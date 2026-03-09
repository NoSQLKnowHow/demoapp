"""
JSON projection router.

Demonstrates three JSON capabilities in Oracle AI Database 26ai:

1. JSON Duality Views: Inspection reports projected as nested JSON
   documents from normalized relational tables. Supports read and
   write (round-trip through the Duality View).

2. JSON Collection Table: Operational procedures stored as native
   JSON documents. Queried via standard SQL.

3. MongoDB API: The same operational procedures collection accessed
   via pymongo, demonstrating that MongoDB-compatible drivers can
   query Oracle JSON collections without code changes.
"""

import json
import time
from typing import Optional

import oracledb
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_credentials
from app.config import settings
from app.database import get_connection, get_cursor
from app.middleware import is_learn_mode
from app.models import (
    InspectionFinding,
    InspectionReport,
    InspectionReportDetail,
    OperationalProcedure,
    PrismResponse,
    ResponseMeta,
)

router = APIRouter(
    prefix="/api/v1/json",
    tags=["json"],
    dependencies=[Depends(verify_credentials)],
)


# ============================================================================
# Inspection Reports (JSON Duality View)
# ============================================================================

INSPECTIONS_LIST_SQL = """
    SELECT JSON_SERIALIZE(data RETURNING CLOB) AS doc
    FROM inspection_report_dv
    ORDER BY JSON_VALUE(data, '$._id' RETURNING NUMBER)
"""

INSPECTION_DETAIL_SQL = """
    SELECT JSON_SERIALIZE(data RETURNING CLOB) AS doc
    FROM inspection_report_dv
    WHERE JSON_VALUE(data, '$._id' RETURNING NUMBER) = :report_id
"""

DUALITY_VIEW_DDL = """CREATE JSON RELATIONAL DUALITY VIEW inspection_report_dv AS
    inspection_reports @insert @update @delete {
        _id        : report_id,
        asset_id   : asset_id,
        inspector  : inspector,
        inspectDate: inspect_date,
        grade      : overall_grade,
        summary    : summary,
        findings   : inspection_findings @insert @update @delete {
            findingId      : finding_id,
            category       : category,
            severity       : severity,
            description    : description,
            recommendation : recommendation
        }
    };"""


def _parse_duality_doc(doc_str):
    """Parse a JSON Duality View document string into a dict."""
    if isinstance(doc_str, str):
        return json.loads(doc_str)
    return doc_str


@router.get("/inspections", response_model=PrismResponse)
async def list_inspections(
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    List inspection reports as JSON documents via the Duality View.
    Each document contains the report with nested findings.
    """
    start = time.perf_counter()

    sql = INSPECTIONS_LIST_SQL + " OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"

    with get_cursor(conn) as cursor:
        cursor.execute(sql, {"offset": offset, "limit": limit})
        rows = cursor.fetchall()

    elapsed = (time.perf_counter() - start) * 1000

    documents = [_parse_duality_doc(row[0]) for row in rows]

    return PrismResponse(
        data=documents,
        meta=ResponseMeta(
            sql=sql.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="json-inspections-list",
        ),
    )


@router.get("/inspections/{report_id}", response_model=PrismResponse)
async def get_inspection(
    report_id: int,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Get a single inspection report as a JSON document via the Duality View.
    """
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute(INSPECTION_DETAIL_SQL, {"report_id": report_id})
        row = cursor.fetchone()

    elapsed = (time.perf_counter() - start) * 1000

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection report not found")

    document = _parse_duality_doc(row[0])

    learn_sql = INSPECTION_DETAIL_SQL.strip()
    if learn:
        learn_sql += "\n\n-- Duality View DDL:\n" + DUALITY_VIEW_DDL

    return PrismResponse(
        data=document,
        meta=ResponseMeta(
            sql=learn_sql if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="json-inspection-detail",
        ),
    )


@router.put("/inspections/{report_id}", response_model=PrismResponse)
async def update_inspection(
    report_id: int,
    body: dict,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Update an inspection report through the Duality View.
    Demonstrates round-trip: edit the JSON document, and the underlying
    relational tables are updated automatically.

    Expects the full JSON document (or a partial update) as the request body.
    """
    if not settings.allow_writes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Writes are disabled in this deployment mode"
        )

    start = time.perf_counter()

    # Ensure the _id in the document matches the URL
    body["_id"] = report_id
    doc_json = json.dumps(body)

    update_sql = """
        UPDATE inspection_report_dv
        SET data = JSON(:doc)
        WHERE JSON_VALUE(data, '$._id' RETURNING NUMBER) = :report_id
    """

    with get_cursor(conn) as cursor:
        cursor.execute(update_sql, {"doc": doc_json, "report_id": report_id})
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection report not found")
        conn.commit()

    # Re-fetch the updated document to return
    with get_cursor(conn) as cursor:
        cursor.execute(INSPECTION_DETAIL_SQL, {"report_id": report_id})
        row = cursor.fetchone()

    elapsed = (time.perf_counter() - start) * 1000

    document = _parse_duality_doc(row[0]) if row else body

    return PrismResponse(
        data=document,
        meta=ResponseMeta(
            sql=update_sql.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="json-inspection-update",
        ),
    )


# ============================================================================
# Operational Procedures (JSON Collection Table)
# ============================================================================

PROCEDURES_LIST_SQL = """
    SELECT JSON_SERIALIZE(data RETURNING CLOB) AS doc
    FROM operational_procedures
"""

PROCEDURE_DETAIL_SQL = """
    SELECT JSON_SERIALIZE(data RETURNING CLOB) AS doc
    FROM operational_procedures
    WHERE JSON_VALUE(data, '$.procedureId') = :procedure_id
"""

PROCEDURES_FILTER_SQL = """
    SELECT JSON_SERIALIZE(data RETURNING CLOB) AS doc
    FROM operational_procedures
    WHERE 1 = 1
"""


@router.get("/procedures", response_model=PrismResponse)
async def list_procedures(
    category: Optional[str] = Query(None, description="Filter by category (e.g., electrical, structural, emergency)"),
    keyword: Optional[str] = Query(None, description="Keyword search in procedure title"),
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    List operational procedures from the JSON collection table.
    These are native JSON documents stored without a relational schema.
    """
    start = time.perf_counter()

    sql = PROCEDURES_FILTER_SQL
    params = {}

    if category is not None:
        sql += " AND JSON_VALUE(data, '$.category') = :category"
        params["category"] = category
    if keyword is not None:
        sql += " AND LOWER(JSON_VALUE(data, '$.title')) LIKE '%' || LOWER(:keyword) || '%'"
        params["keyword"] = keyword

    sql += " ORDER BY JSON_VALUE(data, '$.procedureId')"

    with get_cursor(conn) as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    elapsed = (time.perf_counter() - start) * 1000

    documents = [_parse_duality_doc(row[0]) for row in rows]

    return PrismResponse(
        data=documents,
        meta=ResponseMeta(
            sql=sql.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="json-procedures-list",
        ),
    )


# ============================================================================
# MongoDB API Comparison
# ============================================================================
# NOTE: This endpoint MUST be defined before /procedures/{procedure_id}
# so FastAPI doesn't try to match "mongodb" as a procedure_id.
# ============================================================================

@router.get("/procedures/mongodb", response_model=PrismResponse)
async def list_procedures_mongodb(
    category: Optional[str] = Query(None, description="Filter by category"),
    keyword: Optional[str] = Query(None, description="Keyword search in title"),
    learn: bool = Depends(is_learn_mode),
):
    """
    Query the same operational procedures collection via the Oracle
    Database API for MongoDB (using pymongo). Returns identical results
    to the SQL-based /procedures endpoint, demonstrating that the same
    data is accessible through both SQL and MongoDB-compatible drivers.

    Requires MONGODB_URI to be configured in the environment.
    """
    if not settings.mongodb_uri:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="MongoDB API not configured. Set MONGODB_URI in .env to enable this endpoint."
        )

    start = time.perf_counter()

    try:
        from pymongo import MongoClient

        client = MongoClient(settings.mongodb_uri)
        # The database name is typically the Oracle schema/user name
        db = client[settings.oracle_user.upper()]
        collection = db["OPERATIONAL_PROCEDURES"]

        # Build the MongoDB query filter
        mongo_filter = {}
        if category is not None:
            mongo_filter["category"] = category
        if keyword is not None:
            mongo_filter["title"] = {"$regex": keyword, "$options": "i"}

        # Execute the query
        cursor = collection.find(mongo_filter)
        documents = []
        for doc in cursor:
            # Convert MongoDB ObjectId to string for JSON serialization
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])
            documents.append(doc)

        client.close()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"MongoDB API query failed: {str(e)}"
        )

    elapsed = (time.perf_counter() - start) * 1000

    # Build the pymongo code that was executed (for Learn Mode)
    pymongo_code = f"""from pymongo import MongoClient

client = MongoClient("{settings.mongodb_uri[:30]}...")
db = client["{settings.oracle_user.upper()}"]
collection = db["OPERATIONAL_PROCEDURES"]

filter = {json.dumps(mongo_filter, indent=2)}
results = collection.find(filter)

# Returns the same documents as the SQL endpoint"""

    # Also show the equivalent SQL for comparison
    equivalent_sql = PROCEDURES_FILTER_SQL
    if category:
        equivalent_sql += f"\n    AND JSON_VALUE(data, '$.category') = '{category}'"
    if keyword:
        equivalent_sql += f"\n    AND LOWER(JSON_VALUE(data, '$.title')) LIKE '%{keyword.lower()}%'"
    equivalent_sql += "\n    ORDER BY JSON_VALUE(data, '$.procedureId')"

    learn_content = None
    if learn:
        learn_content = (
            "-- pymongo code:\n" + pymongo_code +
            "\n\n-- Equivalent SQL:\n" + equivalent_sql
        )

    return PrismResponse(
        data=documents,
        meta=ResponseMeta(
            sql=learn_content,
            execution_time_ms=round(elapsed, 2),
            operation_id="json-procedures-mongodb",
        ),
    )


# ============================================================================
# Procedure Detail (after /mongodb to avoid route collision)
# ============================================================================

@router.get("/procedures/{procedure_id}", response_model=PrismResponse)
async def get_procedure(
    procedure_id: str,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Get a single operational procedure document by its procedureId.
    """
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute(PROCEDURE_DETAIL_SQL, {"procedure_id": procedure_id})
        row = cursor.fetchone()

    elapsed = (time.perf_counter() - start) * 1000

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")

    document = _parse_duality_doc(row[0])

    return PrismResponse(
        data=document,
        meta=ResponseMeta(
            sql=PROCEDURE_DETAIL_SQL.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="json-procedure-detail",
        ),
    )
