"""
Prism unified view router.

The "aha moment" endpoint: returns all four projections for a single
asset in one response. Shows the same canonical data simultaneously
as relational, JSON, graph, and vector results.
"""

import json
import time
from collections import defaultdict, deque

import oracledb
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_credentials
from app.config import settings
from app.database import get_connection, get_cursor
from app.middleware import is_learn_mode
from app.models import (
    AssetDetail,
    GraphEdge,
    GraphNeighborhood,
    GraphNode,
    PrismResponse,
    PrismUnifiedView,
    ResponseMeta,
    VectorSearchResult,
)

router = APIRouter(
    prefix="/api/v1/prism",
    tags=["prism"],
    dependencies=[Depends(verify_credentials)],
)

EMBEDDING_MODEL = settings.embedding_model


# ============================================================================
# SQL
# ============================================================================

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

LATEST_INSPECTION_DV_SQL = """
    SELECT JSON_SERIALIZE(data RETURNING CLOB) AS doc
    FROM inspection_report_dv
    WHERE JSON_VALUE(data, '$.asset_id' RETURNING NUMBER) = :asset_id
    ORDER BY JSON_VALUE(data, '$.inspectDate') DESC
    FETCH FIRST 1 ROW ONLY
"""

NEIGHBORS_SQL = """
    SELECT from_asset_id, to_asset_id FROM asset_connections
"""

NODES_FOR_IDS_SQL = """
    SELECT asset_id, name, asset_type, status, district_id
    FROM infrastructure_assets
    WHERE asset_id IN ({id_list})
"""

EDGES_FOR_IDS_SQL = """
    SELECT connection_id, from_asset_id, to_asset_id, connection_type, description
    FROM asset_connections
    WHERE from_asset_id IN ({id_list})
      AND to_asset_id IN ({id_list})
"""

VECTOR_SEARCH_SQL = """
    SELECT chunk_id, source_table, source_id, chunk_text,
           asset_id, asset_name, asset_type, district_name,
           severity, source_date,
           VECTOR_DISTANCE(
               embedding,
               (SELECT embedding FROM document_chunks
                WHERE source_table = 'maintenance_logs'
                AND source_id = (
                    SELECT log_id FROM maintenance_logs
                    WHERE asset_id = :asset_id
                    ORDER BY log_date DESC FETCH FIRST 1 ROW ONLY
                )
                AND chunk_seq = 1),
               COSINE
           ) AS distance
    FROM v_chunks_unified
    WHERE asset_id = :asset_id
    ORDER BY distance
    FETCH FIRST :top_k ROWS ONLY
"""

# Simpler fallback: just get the most relevant chunks for this asset
ASSET_CHUNKS_SQL = """
    SELECT chunk_id, source_table, source_id, chunk_text,
           asset_id, asset_name, asset_type, district_name,
           severity, source_date
    FROM v_chunks_unified
    WHERE asset_id = :asset_id
    ORDER BY source_date DESC NULLS LAST
    FETCH FIRST :top_k ROWS ONLY
"""


# ============================================================================
# Helpers
# ============================================================================

def _node_from_row(row_dict):
    return GraphNode(
        asset_id=row_dict["asset_id"],
        name=row_dict["name"],
        asset_type=row_dict["asset_type"],
        status=row_dict.get("status"),
        district_id=row_dict.get("district_id"),
    )


def _build_id_binds(ids):
    id_list = list(ids)
    bind_names = [f":id{i}" for i in range(len(id_list))]
    bind_params = {f"id{i}": aid for i, aid in enumerate(id_list)}
    return ",".join(bind_names), bind_params


def _parse_specs(row_dict):
    if row_dict.get("specifications"):
        try:
            row_dict["specifications"] = json.loads(row_dict["specifications"])
        except (json.JSONDecodeError, TypeError):
            row_dict["specifications"] = None
    return row_dict


# ============================================================================
# Unified View Endpoint
# ============================================================================

@router.get("/assets/{asset_id}/unified", response_model=PrismResponse)
async def get_unified_view(
    asset_id: int,
    hops: int = Query(2, ge=1, le=4, description="Graph neighborhood depth (1-4)"),
    top_k: int = Query(10, ge=1, le=25, description="Number of vector results"),
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    The Prism unified view: all four projections for a single asset
    in one response.

    - Relational: asset detail with counts and specifications
    - JSON: most recent inspection report via the Duality View
    - Graph: N-hop neighborhood (default 2 hops)
    - Vector: most relevant chunks for this asset
    """
    start = time.perf_counter()
    learn_sqls = []

    # ---- 1. Relational projection ----
    with get_cursor(conn) as cursor:
        cursor.execute(ASSET_DETAIL_SQL, {"asset_id": asset_id})
        columns = [col[0].lower() for col in cursor.description]
        asset_row = cursor.fetchone()

    if not asset_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    asset_dict = _parse_specs(dict(zip(columns, asset_row)))
    relational = AssetDetail(**asset_dict)

    if learn:
        learn_sqls.append("-- Relational projection:\n" + ASSET_DETAIL_SQL.strip())

    # ---- 2. JSON projection (latest inspection via Duality View) ----
    json_document = None
    with get_cursor(conn) as cursor:
        cursor.execute(LATEST_INSPECTION_DV_SQL, {"asset_id": asset_id})
        row = cursor.fetchone()
        if row and row[0]:
            try:
                json_document = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except (json.JSONDecodeError, TypeError):
                json_document = None

    if learn:
        learn_sqls.append("-- JSON projection (Duality View):\n" + LATEST_INSPECTION_DV_SQL.strip())

    # ---- 3. Graph projection (N-hop neighborhood via BFS) ----
    with get_cursor(conn) as cursor:
        cursor.execute(NEIGHBORS_SQL)
        adj = defaultdict(set)
        for from_id, to_id in cursor.fetchall():
            adj[from_id].add(to_id)
            adj[to_id].add(from_id)

    # BFS expansion from the center asset
    visited = {asset_id}
    frontier = {asset_id}
    for _ in range(hops):
        if not frontier:
            break
        next_frontier = set()
        for node in frontier:
            next_frontier |= adj.get(node, set())
        frontier = next_frontier - visited
        visited |= frontier
    neighbor_ids = visited

    graph_data = None
    if neighbor_ids:
        with get_cursor(conn) as cursor:
            bind_str, bind_params = _build_id_binds(neighbor_ids)
            cursor.execute(NODES_FOR_IDS_SQL.format(id_list=bind_str), bind_params)
            columns = [col[0].lower() for col in cursor.description]
            node_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        nodes = [_node_from_row(r) for r in node_rows]
        center = next((n for n in nodes if n.asset_id == asset_id), nodes[0] if nodes else None)

        with get_cursor(conn) as cursor:
            bind_str, bind_params = _build_id_binds(neighbor_ids)
            cursor.execute(EDGES_FOR_IDS_SQL.format(id_list=bind_str), bind_params)
            columns = [col[0].lower() for col in cursor.description]
            edge_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        edges = [GraphEdge(**r) for r in edge_rows]

        if center:
            graph_data = GraphNeighborhood(center=center, nodes=nodes, edges=edges)

    if learn:
        learn_sqls.append(f"-- Graph projection ({hops}-hop neighborhood):\n" +
                          "-- BFS from asset_id, then fetch nodes and edges")

    # ---- 4. Vector projection (relevant chunks for this asset) ----
    vector_results = []
    with get_cursor(conn) as cursor:
        cursor.execute(ASSET_CHUNKS_SQL, {"asset_id": asset_id, "top_k": top_k})
        columns = [col[0].lower() for col in cursor.description]
        chunk_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    for row in chunk_rows:
        vector_results.append(VectorSearchResult(
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

    if learn:
        learn_sqls.append("-- Vector projection (asset chunks):\n" + ASSET_CHUNKS_SQL.strip())

    elapsed = (time.perf_counter() - start) * 1000

    unified = PrismUnifiedView(
        relational=relational,
        json_document=json_document,
        graph=graph_data,
        vector_results=vector_results,
    )

    return PrismResponse(
        data=unified,
        meta=ResponseMeta(
            sql="\n\n".join(learn_sqls) if learn else None,
            execution_time_ms=round(elapsed, 2),
            operation_id="prism-unified-view",
        ),
    )
