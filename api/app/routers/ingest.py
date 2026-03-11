"""
Ingest router.

Handles data entry: new maintenance logs and new inspection reports.
Each submission inserts the record into the canonical table, then
immediately chunks and embeds the narrative text so it becomes
searchable via vector search in the same request.

This is the "one write, many reads" principle in action.
"""

import json
import time

import oracledb
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_credentials
from app.config import settings
from app.database import get_connection, get_cursor
from app.middleware import is_learn_mode
from app.models import (
    IngestResult,
    NewInspectionReport,
    NewMaintenanceLog,
    PipelineStep,
    PrismResponse,
    ResponseMeta,
)

router = APIRouter(
    prefix="/api/v1/ingest",
    tags=["ingest"],
    dependencies=[Depends(verify_credentials)],
)

EMBEDDING_MODEL = settings.embedding_model

# Chunking config (matches prism-ingest.py)
CHUNK_PARAMS = json.dumps({
    "max": 1000,
    "overlap": 100,
    "split": "sentence",
    "normalize": "all",
})


# ============================================================================
# Helpers
# ============================================================================

def _chunk_and_embed(cursor, source_table, source_id, text):
    """
    Chunk text and insert embeddings into document_chunks.
    Returns (chunks_created, pipeline_steps).
    """
    pipeline_steps = []

    if not text or not text.strip():
        return 0, pipeline_steps

    # Step 1: Chunk
    chunk_sql = (
        "SELECT et.column_value FROM TABLE("
        "DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS(:input_text, JSON(:chunk_params))"
        ") et"
    )
    pipeline_steps.append(PipelineStep(
        step="chunk",
        sql=f"SELECT et.column_value FROM TABLE(DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS(:text, JSON('{CHUNK_PARAMS}'))) et",
    ))

    cursor.execute(chunk_sql, {"input_text": text, "chunk_params": CHUNK_PARAMS})
    chunks = cursor.fetchall()

    if not chunks:
        return 0, pipeline_steps

    # Step 2 & 3: Embed and store
    insert_sql = (
        f"INSERT INTO document_chunks (source_table, source_id, chunk_seq, chunk_text, embedding) "
        f"VALUES (:source_table, :source_id, :chunk_seq, :chunk_text, "
        f"VECTOR_EMBEDDING({EMBEDDING_MODEL} USING :chunk_text AS data))"
    )
    pipeline_steps.append(PipelineStep(
        step="embed+store",
        sql=insert_sql,
    ))

    chunk_count = 0
    for idx, (chunk_value,) in enumerate(chunks, start=1):
        # Parse chunk JSON to extract text
        if isinstance(chunk_value, str):
            try:
                chunk_data = json.loads(chunk_value)
                chunk_text = chunk_data.get("chunk_data", chunk_value)
            except json.JSONDecodeError:
                chunk_text = chunk_value
        elif isinstance(chunk_value, dict):
            chunk_text = chunk_value.get("chunk_data", str(chunk_value))
        else:
            chunk_text = str(chunk_value)

        if not chunk_text or not chunk_text.strip():
            continue

        cursor.execute(insert_sql, {
            "source_table": source_table,
            "source_id": source_id,
            "chunk_seq": idx,
            "chunk_text": chunk_text,
        })
        chunk_count += 1

    return chunk_count, pipeline_steps


# ============================================================================
# New Maintenance Log
# ============================================================================

INSERT_LOG_SQL = """
    INSERT INTO maintenance_logs (asset_id, severity, narrative)
    VALUES (:asset_id, :severity, :narrative)
    RETURNING log_id INTO :new_id
"""


@router.post("/maintenance-logs", response_model=PrismResponse)
async def create_maintenance_log(
    body: NewMaintenanceLog,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Submit a new maintenance log. The log is inserted, then the narrative
    text is immediately chunked, embedded, and stored so it becomes
    searchable via vector search.
    """
    if not settings.allow_writes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Writes are disabled in this deployment mode",
        )

    start = time.perf_counter()
    all_steps = []

    with get_cursor(conn) as cursor:
        # Validate asset exists
        cursor.execute("SELECT 1 FROM infrastructure_assets WHERE asset_id = :id", {"id": body.asset_id})
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        # Insert the log and get the new ID via RETURNING INTO
        new_id_var = cursor.var(oracledb.NUMBER)
        all_steps.append(PipelineStep(step="insert", sql=INSERT_LOG_SQL.strip()))
        cursor.execute(INSERT_LOG_SQL, {
            "asset_id": body.asset_id,
            "severity": body.severity,
            "narrative": body.narrative,
            "new_id": new_id_var,
        })
        log_id = int(new_id_var.getvalue()[0])

        # Chunk and embed
        chunks_created, pipeline_steps = _chunk_and_embed(
            cursor, "maintenance_logs", log_id, body.narrative
        )
        all_steps.extend(pipeline_steps)

        conn.commit()

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=IngestResult(
            source_id=log_id,
            chunks_created=chunks_created,
            vectors_stored=chunks_created,
            pipeline_steps=all_steps,
        ),
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="ingest-maintenance-log",
        ),
    )


# ============================================================================
# New Inspection Report (with Findings)
# ============================================================================

INSERT_REPORT_SQL = """
    INSERT INTO inspection_reports (asset_id, inspector, overall_grade, summary)
    VALUES (:asset_id, :inspector, :overall_grade, :summary)
    RETURNING report_id INTO :new_id
"""

INSERT_FINDING_SQL = """
    INSERT INTO inspection_findings (report_id, category, severity, description, recommendation)
    VALUES (:report_id, :category, :severity, :description, :recommendation)
    RETURNING finding_id INTO :new_id
"""


@router.post("/inspection-reports", response_model=PrismResponse)
async def create_inspection_report(
    body: NewInspectionReport,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Submit a new inspection report with findings. The report and findings
    are inserted, then the summary and each finding description are
    chunked, embedded, and stored for vector search.
    """
    if not settings.allow_writes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Writes are disabled in this deployment mode",
        )

    start = time.perf_counter()
    all_steps = []
    total_chunks = 0

    with get_cursor(conn) as cursor:
        # Validate asset exists
        cursor.execute("SELECT 1 FROM infrastructure_assets WHERE asset_id = :id", {"id": body.asset_id})
        if not cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

        # Insert the report and get the new ID via RETURNING INTO
        new_id_var = cursor.var(oracledb.NUMBER)
        all_steps.append(PipelineStep(step="insert_report", sql=INSERT_REPORT_SQL.strip()))
        cursor.execute(INSERT_REPORT_SQL, {
            "asset_id": body.asset_id,
            "inspector": body.inspector,
            "overall_grade": body.overall_grade,
            "summary": body.summary,
            "new_id": new_id_var,
        })
        report_id = int(new_id_var.getvalue()[0])

        # Chunk and embed the summary
        chunks, steps = _chunk_and_embed(cursor, "inspection_reports", report_id, body.summary)
        total_chunks += chunks
        all_steps.extend(steps)

        # Insert findings and vectorize each
        for finding in body.findings:
            new_finding_var = cursor.var(oracledb.NUMBER)
            all_steps.append(PipelineStep(step="insert_finding", sql=INSERT_FINDING_SQL.strip()))
            cursor.execute(INSERT_FINDING_SQL, {
                "report_id": report_id,
                "category": finding.category,
                "severity": finding.severity,
                "description": finding.description,
                "recommendation": finding.recommendation,
                "new_id": new_finding_var,
            })
            finding_id = int(new_finding_var.getvalue()[0])

            # Chunk and embed the finding description
            chunks, steps = _chunk_and_embed(
                cursor, "inspection_findings", finding_id, finding.description
            )
            total_chunks += chunks
            all_steps.extend(steps)

        conn.commit()

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=IngestResult(
            source_id=report_id,
            chunks_created=total_chunks,
            vectors_stored=total_chunks,
            pipeline_steps=all_steps,
        ),
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="ingest-inspection-report",
        ),
    )
