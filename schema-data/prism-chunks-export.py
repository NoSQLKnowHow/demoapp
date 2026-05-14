#!/usr/bin/env python3
"""
============================================================================
PRISM: Document Chunks Exporter
============================================================================
Exports the contents of the DOCUMENT_CHUNKS table from a fully-populated
Prism database to a portable file. The export includes the vector
embeddings (so re-vectorization is not needed at import time) and the
natural keys needed to re-associate chunks with their source rows in a
freshly-seeded target database.

Output formats (selected via --format):
    json  - data/document_chunks.json.gz (compressed JSON, inspectable)
    pkl   - data/document_chunks.pkl     (Python pickle, binary)
    both  - both files (default)

Usage:
    python prism-chunks-export.py [--format json|pkl|both]

Run against: a Prism database that has been fully seeded and ingested
            (prism-seed.py + prism-ingest.py both completed)
Pairs with:  prism-chunks-import.py (loads the export into a new database)

Requires:
    - python-oracledb
    - python-dotenv
    - Environment variables (see .env): ORACLE_DSN, ORACLE_USER,
      ORACLE_PASSWORD, ORACLE_WALLET_DIR (optional)
============================================================================
"""

import argparse
import array
import gzip
import json
import os
import pickle
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

import oracledb

# Return LOBs as Python strings/bytes, matching prism-ingest.py behavior.
oracledb.defaults.fetch_lobs = False


# ============================================================================
# Configuration
# ============================================================================

ORACLE_DSN = os.environ.get("ORACLE_DSN")
ORACLE_USER = os.environ.get("ORACLE_USER", "prism")
ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD")
ORACLE_WALLET_DIR = os.environ.get("ORACLE_WALLET_DIR")

EMBEDDING_MODEL = "DEMO_MODEL"

# Output paths (kept next to maintenance_logs.json and inspection_reports.json)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JSON_OUTPUT_FILE = os.path.join(DATA_DIR, "document_chunks.json.gz")
PKL_OUTPUT_FILE = os.path.join(DATA_DIR, "document_chunks.pkl")


# ============================================================================
# Database Connection
# ============================================================================

def get_connection():
    """Create and return an Oracle database connection."""
    wallet_dir = ORACLE_WALLET_DIR.strip() if ORACLE_WALLET_DIR else ""
    if wallet_dir and os.path.isdir(wallet_dir):
        print(f"  Using wallet connection (wallet dir: {wallet_dir})")
        return oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN,
            config_dir=wallet_dir,
            wallet_location=wallet_dir,
            wallet_password=ORACLE_PASSWORD
        )
    else:
        print(f"  Using direct connection (DSN: {ORACLE_DSN})")
        return oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN
        )


# ============================================================================
# Embedding Conversion Helper
# ============================================================================

def embedding_to_list(value):
    """
    Convert an Oracle VECTOR column value to a plain Python list of floats.

    python-oracledb returns VECTOR values as array.array (typecode 'f' or 'd').
    A plain Python list is JSON-serializable and works with pickle too.
    """
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, array.array):
        return list(value)
    # Fallback: assume iterable of numbers
    try:
        return list(value)
    except TypeError:
        raise TypeError(f"Cannot convert embedding of type {type(value).__name__} to list")


# ============================================================================
# Export Logic
# ============================================================================

EXPORT_QUERY = """
    SELECT
        dc.source_table,
        dc.source_id,
        dc.chunk_seq,
        dc.chunk_text,
        dc.embedding,
        -- Natural keys per source table, resolved via LEFT JOIN.
        -- Only one of these branches will be populated per row.
        ml_asset.name      AS ml_asset_name,
        ml.narrative       AS ml_narrative,
        ir_asset.name      AS ir_asset_name,
        ir.inspector       AS ir_inspector,
        ir.summary         AS ir_summary,
        if_asset.name      AS if_asset_name,
        if_report.inspector AS if_inspector,
        if_report.summary  AS if_report_summary,
        ifn.description    AS if_description
    FROM document_chunks dc
    -- Maintenance log join chain
    LEFT JOIN maintenance_logs ml
        ON dc.source_table = 'maintenance_logs' AND dc.source_id = ml.log_id
    LEFT JOIN infrastructure_assets ml_asset
        ON ml.asset_id = ml_asset.asset_id
    -- Inspection report join chain
    LEFT JOIN inspection_reports ir
        ON dc.source_table = 'inspection_reports' AND dc.source_id = ir.report_id
    LEFT JOIN infrastructure_assets ir_asset
        ON ir.asset_id = ir_asset.asset_id
    -- Inspection finding join chain (finding -> report -> asset)
    LEFT JOIN inspection_findings ifn
        ON dc.source_table = 'inspection_findings' AND dc.source_id = ifn.finding_id
    LEFT JOIN inspection_reports if_report
        ON ifn.report_id = if_report.report_id
    LEFT JOIN infrastructure_assets if_asset
        ON if_report.asset_id = if_asset.asset_id
    ORDER BY dc.source_table, dc.source_id, dc.chunk_seq
"""


def build_natural_key(row_dict):
    """
    Build the natural_key dict for a chunk based on its source_table.

    For each source table, we capture the fields needed by the import
    script to look up the new source_id in the target database after
    re-seeding. Uses full text fields (not excerpts) to guarantee
    uniqueness; gzip handles the redundancy.
    """
    source_table = row_dict["source_table"]

    if source_table == "maintenance_logs":
        return {
            "asset_name": row_dict["ml_asset_name"],
            "narrative": row_dict["ml_narrative"],
        }
    elif source_table == "inspection_reports":
        return {
            "asset_name": row_dict["ir_asset_name"],
            "inspector": row_dict["ir_inspector"],
            "summary": row_dict["ir_summary"],
        }
    elif source_table == "inspection_findings":
        return {
            "asset_name": row_dict["if_asset_name"],
            "inspector": row_dict["if_inspector"],
            "report_summary": row_dict["if_report_summary"],
            "finding_description": row_dict["if_description"],
        }
    else:
        raise ValueError(f"Unknown source_table: {source_table}")


def fetch_chunks(cursor):
    """Run the export query and yield normalized chunk dicts."""
    cursor.execute(EXPORT_QUERY)
    columns = [col[0].lower() for col in cursor.description]

    chunks = []
    for row in cursor:
        row_dict = dict(zip(columns, row))

        chunk = {
            "source_table": row_dict["source_table"],
            "chunk_seq": row_dict["chunk_seq"],
            "chunk_text": row_dict["chunk_text"],
            "embedding": embedding_to_list(row_dict["embedding"]),
            "natural_key": build_natural_key(row_dict),
        }
        chunks.append(chunk)

    return chunks


def get_vector_dimensions(cursor):
    """Determine the vector dimension count from a sample row."""
    cursor.execute("""
        SELECT VECTOR_DIMENSION_COUNT(embedding)
        FROM document_chunks
        WHERE ROWNUM = 1
    """)
    result = cursor.fetchone()
    return int(result[0]) if result else None


def get_database_identity(cursor):
    """Capture identifying info about the source database for the manifest."""
    cursor.execute("SELECT SYS_CONTEXT('USERENV', 'DB_NAME'), SYS_CONTEXT('USERENV', 'SERVICE_NAME') FROM dual")
    db_name, service_name = cursor.fetchone()
    return f"{db_name}/{service_name}" if service_name else db_name


def build_manifest(chunks, cursor):
    """Build the export manifest header."""
    counts_by_source = {}
    for chunk in chunks:
        st = chunk["source_table"]
        counts_by_source[st] = counts_by_source.get(st, 0) + 1

    return {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_database": get_database_identity(cursor),
        "embedding_model_name": EMBEDDING_MODEL,
        "vector_dimensions": get_vector_dimensions(cursor),
        "total_chunks": len(chunks),
        "chunks_by_source_table": counts_by_source,
    }


# ============================================================================
# File Writers
# ============================================================================

def write_json(payload, path):
    """Write the export to a gzip-compressed JSON file."""
    print(f"Writing JSON export to {path}...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  Wrote {size_mb:.2f} MB.")


def write_pkl(payload, path):
    """Write the export to a pickle file."""
    print(f"Writing pickle export to {path}...")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  Wrote {size_mb:.2f} MB.")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Export the Prism DOCUMENT_CHUNKS table to a portable file."
    )
    parser.add_argument(
        "--format",
        choices=["json", "pkl", "both"],
        default="both",
        help="Output format(s) to write. Default: both",
    )
    args = parser.parse_args()

    print("=" * 72)
    print("  PRISM: Document Chunks Exporter")
    print("=" * 72)
    print()

    # Validate configuration
    missing = []
    if not ORACLE_DSN:
        missing.append("ORACLE_DSN")
    if not ORACLE_PASSWORD:
        missing.append("ORACLE_PASSWORD")
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    # Connect
    print("Connecting to source database...")
    conn = get_connection()
    cursor = conn.cursor()
    print("  Connected.")

    # Sanity check: confirm document_chunks has data
    cursor.execute("SELECT COUNT(*) FROM document_chunks")
    total = cursor.fetchone()[0]
    if total == 0:
        print("ERROR: document_chunks is empty. Run prism-ingest.py first.")
        cursor.close()
        conn.close()
        sys.exit(1)
    print(f"  Found {total} chunks in document_chunks.")

    # Fetch all chunks with natural keys
    print("\nFetching chunks with natural keys...")
    chunks = fetch_chunks(cursor)
    print(f"  Retrieved {len(chunks)} chunks.")

    # Detect any chunks that failed to resolve a natural key (orphans)
    orphans = [c for c in chunks if not c["natural_key"] or all(v is None for v in c["natural_key"].values())]
    if orphans:
        print(f"  WARNING: {len(orphans)} chunks could not resolve a natural key. These will be excluded.")
        chunks = [c for c in chunks if c not in orphans]

    # Build the manifest
    manifest = build_manifest(chunks, cursor)
    print("\nManifest:")
    for key, value in manifest.items():
        print(f"  {key}: {value}")

    # Build the final payload
    payload = {
        "manifest": manifest,
        "chunks": chunks,
    }

    # Close DB resources before writing files
    cursor.close()
    conn.close()

    # Write requested formats
    print()
    if args.format in ("json", "both"):
        write_json(payload, JSON_OUTPUT_FILE)
    if args.format in ("pkl", "both"):
        write_pkl(payload, PKL_OUTPUT_FILE)

    print()
    print("=" * 72)
    print("  Export complete.")
    print("  Use prism-chunks-import.py to load this export into a target database.")
    print("=" * 72)


if __name__ == "__main__":
    main()
