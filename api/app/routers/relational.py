"""
Relational projection router.

Provides standard SQL-based access to the canonical CityPulse data:
districts, infrastructure assets (with JSON specifications), and
maintenance logs.
"""

import json
import time
from typing import Optional

import oracledb
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_credentials
from app.database import get_connection, get_cursor
from app.middleware import is_learn_mode
from app.models import (
    Asset,
    AssetDetail,
    District,
    MaintenanceLog,
    MaintenanceLogSummary,
    PrismResponse,
    ResponseMeta,
)

router = APIRouter(
    prefix="/api/v1/relational",
    tags=["relational"],
    dependencies=[Depends(verify_credentials)],
)


# ============================================================================
# Districts
# ============================================================================

DISTRICTS_LIST_SQL = """
    SELECT district_id, name, classification, population, area_sq_km, description
    FROM districts
    ORDER BY name
"""

DISTRICT_DETAIL_SQL = """
    SELECT district_id, name, classification, population, area_sq_km, description
    FROM districts
    WHERE district_id = :district_id
"""


@router.get("/districts", response_model=PrismResponse)
async def list_districts(
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """List all districts."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute(DISTRICTS_LIST_SQL)
        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=[District(**row) for row in rows],
        meta=ResponseMeta(
            sql=DISTRICTS_LIST_SQL.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="relational-districts-list",
        ),
    )


@router.get("/districts/{district_id}", response_model=PrismResponse)
async def get_district(
    district_id: int,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """Get a single district by ID."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute(DISTRICT_DETAIL_SQL, {"district_id": district_id})
        columns = [col[0].lower() for col in cursor.description]
        row = cursor.fetchone()

    elapsed = (time.perf_counter() - start) * 1000

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="District not found")

    return PrismResponse(
        data=District(**dict(zip(columns, row))),
        meta=ResponseMeta(
            sql=DISTRICT_DETAIL_SQL.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="relational-district-detail",
        ),
    )


# ============================================================================
# Infrastructure Assets
# ============================================================================

ASSETS_LIST_SQL = """
    SELECT a.asset_id, a.district_id, a.name, a.asset_type, a.status,
           a.commissioned_date, a.description,
           JSON_SERIALIZE(a.specifications RETURNING VARCHAR2(4000)) AS specifications
    FROM infrastructure_assets a
    WHERE 1 = 1
"""

ASSET_DETAIL_SQL = """
    SELECT a.asset_id, a.district_id, a.name, a.asset_type, a.status,
           a.commissioned_date, a.description,
           JSON_SERIALIZE(a.specifications RETURNING VARCHAR2(4000)) AS specifications,
           d.name AS district_name,
           (SELECT COUNT(*) FROM maintenance_logs ml WHERE ml.asset_id = a.asset_id) AS maintenance_log_count,
           (SELECT COUNT(*) FROM inspection_reports ir WHERE ir.asset_id = a.asset_id) AS inspection_report_count,
           (SELECT COUNT(*) FROM asset_connections ac
            WHERE ac.from_asset_id = a.asset_id OR ac.to_asset_id = a.asset_id) AS connection_count
    FROM infrastructure_assets a
    JOIN districts d ON a.district_id = d.district_id
    WHERE a.asset_id = :asset_id
"""


def _parse_specs(row_dict):
    """Parse the JSON specifications string into a dict."""
    if row_dict.get("specifications"):
        try:
            row_dict["specifications"] = json.loads(row_dict["specifications"])
        except (json.JSONDecodeError, TypeError):
            row_dict["specifications"] = None
    return row_dict


@router.get("/assets", response_model=PrismResponse)
async def list_assets(
    district_id: Optional[int] = Query(None, description="Filter by district"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    asset_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """List infrastructure assets with optional filters."""
    start = time.perf_counter()

    sql = ASSETS_LIST_SQL
    params = {}

    if district_id is not None:
        sql += " AND a.district_id = :district_id"
        params["district_id"] = district_id
    if asset_type is not None:
        sql += " AND a.asset_type = :asset_type"
        params["asset_type"] = asset_type
    if asset_status is not None:
        sql += " AND a.status = :status"
        params["status"] = asset_status

    sql += " ORDER BY a.name"

    with get_cursor(conn) as cursor:
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = [_parse_specs(dict(zip(columns, row))) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=[Asset(**row) for row in rows],
        meta=ResponseMeta(
            sql=sql.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="relational-assets-list",
        ),
    )


@router.get("/assets/{asset_id}", response_model=PrismResponse)
async def get_asset(
    asset_id: int,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """Get a single asset with related counts and district name."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute(ASSET_DETAIL_SQL, {"asset_id": asset_id})
        columns = [col[0].lower() for col in cursor.description]
        row = cursor.fetchone()

    elapsed = (time.perf_counter() - start) * 1000

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    row_dict = _parse_specs(dict(zip(columns, row)))

    return PrismResponse(
        data=AssetDetail(**row_dict),
        meta=ResponseMeta(
            sql=ASSET_DETAIL_SQL.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="relational-asset-detail",
        ),
    )


# ============================================================================
# Maintenance Logs
# ============================================================================

MAINT_LOGS_LIST_SQL = """
    SELECT ml.log_id, ml.asset_id, a.name AS asset_name,
           ml.log_date, ml.severity,
           SUBSTR(ml.narrative, 1, 200) AS narrative_preview
    FROM maintenance_logs ml
    JOIN infrastructure_assets a ON ml.asset_id = a.asset_id
    WHERE 1 = 1
"""

MAINT_LOG_DETAIL_SQL = """
    SELECT log_id, asset_id, log_date, severity, narrative
    FROM maintenance_logs
    WHERE log_id = :log_id
"""


@router.get("/maintenance-logs", response_model=PrismResponse)
async def list_maintenance_logs(
    asset_id: Optional[int] = Query(None, description="Filter by asset"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    keyword: Optional[str] = Query(None, description="Keyword search in narrative text"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """List maintenance logs with optional filters and keyword search."""
    start = time.perf_counter()

    sql = MAINT_LOGS_LIST_SQL
    params = {}

    if asset_id is not None:
        sql += " AND ml.asset_id = :asset_id"
        params["asset_id"] = asset_id
    if severity is not None:
        sql += " AND ml.severity = :severity"
        params["severity"] = severity
    if keyword is not None:
        sql += " AND LOWER(ml.narrative) LIKE '%' || LOWER(:keyword) || '%'"
        params["keyword"] = keyword

    sql += " ORDER BY ml.log_date DESC"
    sql += " OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"
    params["offset"] = offset
    params["limit"] = limit

    with get_cursor(conn) as cursor:
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=[MaintenanceLogSummary(**row) for row in rows],
        meta=ResponseMeta(
            sql=sql.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="relational-maintenance-logs-list",
        ),
    )


@router.get("/maintenance-logs/{log_id}", response_model=PrismResponse)
async def get_maintenance_log(
    log_id: int,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """Get a single maintenance log by ID."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute(MAINT_LOG_DETAIL_SQL, {"log_id": log_id})
        columns = [col[0].lower() for col in cursor.description]
        row = cursor.fetchone()

    elapsed = (time.perf_counter() - start) * 1000

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance log not found")

    return PrismResponse(
        data=MaintenanceLog(**dict(zip(columns, row))),
        meta=ResponseMeta(
            sql=MAINT_LOG_DETAIL_SQL.strip() if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="relational-maintenance-log-detail",
        ),
    )
