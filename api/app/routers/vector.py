"""
Vector projection router.

Provides semantic search, keyword search, and hybrid search across
all vectorized CityPulse content (maintenance logs, inspection report
summaries, inspection finding descriptions).

Uses the pre-joined views (v_chunks_unified, v_chunks_maintenance_logs,
etc.) to simplify queries and return rich context with each result.
"""

import time
from typing import Optional

import oracledb
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_credentials
from app.config import settings
from app.database import get_connection, get_cursor
from app.middleware import is_learn_mode
from app.models import (
    PrismResponse,
    ResponseMeta,
    VectorSearchRequest,
    VectorSearchResult,
)

router = APIRouter(
    prefix="/api/v1/vector",
    tags=["vector"],
    dependencies=[Depends(verify_credentials)],
)

EMBEDDING_MODEL = settings.embedding_model


# ============================================================================
# Semantic Search
# ============================================================================

SEMANTIC_SEARCH_SQL = """
    SELECT chunk_id, source_table, source_id, chunk_text,
           asset_id, asset_name, asset_type, district_name,
           severity, source_date,
           VECTOR_DISTANCE(
               embedding,
               VECTOR_EMBEDDING({model} USING :query AS data),
               COSINE
           ) AS distance
    FROM v_chunks_unified
    WHERE 1 = 1
"""


@router.post("/search", response_model=PrismResponse)
async def semantic_search(
    body: VectorSearchRequest,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Semantic vector search across all vectorized content.
    Finds chunks whose meaning is closest to the natural language query,
    even if exact keywords don't appear in the text.
    """
    start = time.perf_counter()

    sql = SEMANTIC_SEARCH_SQL.format(model=EMBEDDING_MODEL)
    params = {"query": body.query}

    if body.source_filter:
        sql += " AND source_table = :source_filter"
        params["source_filter"] = body.source_filter
    if body.district_filter:
        sql += " AND district_id = :district_filter"
        params["district_filter"] = body.district_filter
    if body.severity_filter:
        sql += " AND severity = :severity_filter"
        params["severity_filter"] = body.severity_filter

    sql += " ORDER BY distance"
    sql += " FETCH FIRST :top_k ROWS ONLY"
    params["top_k"] = body.top_k

    with get_cursor(conn) as cursor:
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    results = []
    for row in rows:
        results.append(VectorSearchResult(
            chunk_id=row["chunk_id"],
            source_table=row["source_table"],
            source_id=row["source_id"],
            chunk_text=row["chunk_text"],
            similarity_score=round(1 - row["distance"], 4),
            asset_name=row.get("asset_name"),
            asset_id=row.get("asset_id"),
            log_date=row.get("source_date"),
            severity=row.get("severity"),
        ))

    return PrismResponse(
        data=results,
        meta=ResponseMeta(
            sql=sql.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="vector-semantic-search",
        ),
    )


# ============================================================================
# Keyword Search (for comparison)
# ============================================================================

KEYWORD_SEARCH_SQL = """
    SELECT chunk_id, source_table, source_id, chunk_text,
           asset_id, asset_name, asset_type, district_name,
           severity, source_date
    FROM v_chunks_unified
    WHERE LOWER(chunk_text) LIKE '%' || LOWER(:query) || '%'
"""


@router.post("/search/keyword", response_model=PrismResponse)
async def keyword_search(
    body: VectorSearchRequest,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Keyword (LIKE) search across all vectorized content.
    Provided for side-by-side comparison with semantic search to
    demonstrate the difference in result quality.
    """
    start = time.perf_counter()

    sql = KEYWORD_SEARCH_SQL
    params = {"query": body.query}

    if body.source_filter:
        sql += " AND source_table = :source_filter"
        params["source_filter"] = body.source_filter
    if body.district_filter:
        sql += " AND district_id = :district_filter"
        params["district_filter"] = body.district_filter
    if body.severity_filter:
        sql += " AND severity = :severity_filter"
        params["severity_filter"] = body.severity_filter

    sql += " FETCH FIRST :top_k ROWS ONLY"
    params["top_k"] = body.top_k

    with get_cursor(conn) as cursor:
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    results = []
    for row in rows:
        results.append(VectorSearchResult(
            chunk_id=row["chunk_id"],
            source_table=row["source_table"],
            source_id=row["source_id"],
            chunk_text=row["chunk_text"],
            similarity_score=0.0,
            asset_name=row.get("asset_name"),
            asset_id=row.get("asset_id"),
            log_date=row.get("source_date"),
            severity=row.get("severity"),
        ))

    return PrismResponse(
        data=results,
        meta=ResponseMeta(
            sql=sql.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="vector-keyword-search",
        ),
    )


# ============================================================================
# Hybrid Search (semantic + relational filters)
# ============================================================================

HYBRID_SEARCH_SQL = """
    SELECT chunk_id, source_table, source_id, chunk_text,
           asset_id, asset_name, asset_type, district_name,
           severity, source_date,
           VECTOR_DISTANCE(
               embedding,
               VECTOR_EMBEDDING({model} USING :query AS data),
               COSINE
           ) AS distance
    FROM v_chunks_unified
    WHERE 1 = 1
"""


@router.post("/search/hybrid", response_model=PrismResponse)
async def hybrid_search(
    body: VectorSearchRequest,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Hybrid search: semantic vector similarity combined with relational
    filters (source type, district, severity). This demonstrates the
    advantage of converged databases where vector search and relational
    predicates operate on the same data in the same query.
    """
    start = time.perf_counter()

    sql = HYBRID_SEARCH_SQL.format(model=EMBEDDING_MODEL)
    params = {"query": body.query}

    if body.source_filter:
        sql += " AND source_table = :source_filter"
        params["source_filter"] = body.source_filter
    if body.district_filter:
        sql += " AND district_id = :district_filter"
        params["district_filter"] = body.district_filter
    if body.severity_filter:
        sql += " AND severity = :severity_filter"
        params["severity_filter"] = body.severity_filter

    sql += " ORDER BY distance"
    sql += " FETCH FIRST :top_k ROWS ONLY"
    params["top_k"] = body.top_k

    elapsed_note = ""
    if not (body.source_filter or body.district_filter or body.severity_filter):
        elapsed_note = " (no relational filters applied; equivalent to semantic search)"

    with get_cursor(conn) as cursor:
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    results = []
    for row in rows:
        results.append(VectorSearchResult(
            chunk_id=row["chunk_id"],
            source_table=row["source_table"],
            source_id=row["source_id"],
            chunk_text=row["chunk_text"],
            similarity_score=round(1 - row["distance"], 4),
            asset_name=row.get("asset_name"),
            asset_id=row.get("asset_id"),
            log_date=row.get("source_date"),
            severity=row.get("severity"),
        ))

    learn_sql = None
    if learn:
        learn_sql = (
            sql.strip() + "\n\n" +
            "-- Hybrid search combines VECTOR_DISTANCE (semantic similarity)\n" +
            "-- with standard SQL WHERE clauses (relational filters) in a\n" +
            "-- single query. No post-filtering needed." +
            elapsed_note
        )

    return PrismResponse(
        data=results,
        meta=ResponseMeta(
            sql=learn_sql,
            execution_time_ms=round(elapsed, 2),
            operation_id="vector-hybrid-search",
        ),
    )


# ============================================================================
# Pipeline Explain (Learn Mode)
# ============================================================================

@router.get("/pipeline/explain", response_model=PrismResponse)
async def pipeline_explain(
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Returns a description of the vector ingestion pipeline steps,
    along with current chunk counts. Designed for Learn Mode to
    help developers understand how content becomes searchable.
    """
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute("""
            SELECT source_table, COUNT(*) AS chunk_count
            FROM document_chunks
            GROUP BY source_table
            ORDER BY source_table
        """)
        counts = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM document_chunks")
        total = cursor.fetchone()[0]

    elapsed = (time.perf_counter() - start) * 1000

    pipeline = {
        "steps": [
            {
                "step": 1,
                "name": "Source text extraction",
                "description": "Read narrative text from maintenance logs, inspection report summaries, and inspection finding descriptions.",
                "sql": "SELECT narrative FROM maintenance_logs WHERE ..."
            },
            {
                "step": 2,
                "name": "Chunking",
                "description": "Split each text into smaller overlapping chunks using DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS. This ensures each chunk fits within the embedding model's input limit and captures focused semantic meaning.",
                "sql": "SELECT * FROM TABLE(DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS(:text, JSON('{\"max\": 1000, \"overlap\": 100, \"split\": \"sentence\", \"normalize\": \"all\"}')))"
            },
            {
                "step": 3,
                "name": "Embedding",
                "description": f"Generate a vector embedding for each chunk using the {EMBEDDING_MODEL} ONNX model loaded directly in the database. The embedding captures the semantic meaning of the text as a high-dimensional vector.",
                "sql": f"SELECT VECTOR_EMBEDDING({EMBEDDING_MODEL} USING :chunk_text AS data) FROM dual"
            },
            {
                "step": 4,
                "name": "Storage",
                "description": "Store each chunk's text, its vector embedding, and a reference back to the source record in the DOCUMENT_CHUNKS table. The vector lives with the data, not in a separate system.",
                "sql": f"INSERT INTO document_chunks (source_table, source_id, chunk_seq, chunk_text, embedding) VALUES (:src, :id, :seq, :text, VECTOR_EMBEDDING({EMBEDDING_MODEL} USING :text AS data))"
            },
            {
                "step": 5,
                "name": "Indexing",
                "description": "Create an HNSW vector index on the embedding column for fast approximate nearest neighbor search.",
                "sql": "CREATE VECTOR INDEX idx_chunk_embedding ON document_chunks(embedding) ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE WITH TARGET ACCURACY 95"
            },
        ],
        "current_counts": {
            "maintenance_logs": counts.get("maintenance_logs", 0),
            "inspection_reports": counts.get("inspection_reports", 0),
            "inspection_findings": counts.get("inspection_findings", 0),
            "total_chunks": total,
        },
        "embedding_model": EMBEDDING_MODEL,
    }

    return PrismResponse(
        data=pipeline,
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="vector-pipeline-explain",
        ),
    )
