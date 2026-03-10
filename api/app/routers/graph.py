"""
Graph projection router.

Provides SQL/PGQ-based access to the CityPulse infrastructure
connectivity graph. Assets are vertices, connections are edges.

Endpoints:
- Direct connections for an asset
- N-hop neighborhood (subgraph around an asset)
- Shortest path between two assets
"""

import time
from typing import Optional

import oracledb
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import verify_credentials
from app.database import get_connection, get_cursor
from app.middleware import is_learn_mode
from app.models import (
    AssetConnection,
    GraphEdge,
    GraphNeighborhood,
    GraphNode,
    GraphPath,
    PrismResponse,
    ResponseMeta,
)

router = APIRouter(
    prefix="/api/v1/graph",
    tags=["graph"],
    dependencies=[Depends(verify_credentials)],
)


# ============================================================================
# Helper: build a GraphNode from a row dict
# ============================================================================

def _node_from_row(row_dict):
    """Build a GraphNode from a dict with asset columns."""
    return GraphNode(
        asset_id=row_dict["asset_id"],
        name=row_dict["name"],
        asset_type=row_dict["asset_type"],
        status=row_dict.get("status"),
        district_id=row_dict.get("district_id"),
    )


# ============================================================================
# Direct Connections
# ============================================================================

CONNECTIONS_SQL = """
    SELECT ac.connection_id, ac.from_asset_id, ac.to_asset_id,
           ac.connection_type, ac.description,
           a_from.name AS from_asset_name,
           a_to.name AS to_asset_name
    FROM asset_connections ac
    JOIN infrastructure_assets a_from ON ac.from_asset_id = a_from.asset_id
    JOIN infrastructure_assets a_to ON ac.to_asset_id = a_to.asset_id
    WHERE ac.from_asset_id = :asset_id OR ac.to_asset_id = :asset_id
    ORDER BY ac.connection_type, a_from.name
"""

# The equivalent SQL/PGQ query (shown in Learn Mode for comparison)
CONNECTIONS_PGQ_SQL = """
    SELECT src_id, src_name, edge_type, edge_desc, dst_id, dst_name
    FROM GRAPH_TABLE (citypulse_graph
        MATCH (a) -[e]- (b)
        WHERE a.asset_id = :asset_id
        COLUMNS (
            a.asset_id AS src_id,
            a.name AS src_name,
            e.connection_type AS edge_type,
            e.description AS edge_desc,
            b.asset_id AS dst_id,
            b.name AS dst_name
        )
    )
    ORDER BY edge_type, src_name
"""


@router.get("/assets/{asset_id}/connections", response_model=PrismResponse)
async def get_connections(
    asset_id: int,
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Get all direct connections for an asset (both inbound and outbound).
    Returns the connections with asset names resolved.
    """
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute(CONNECTIONS_SQL, {"asset_id": asset_id})
        columns = [col[0].lower() for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    if not rows:
        # Check if the asset exists at all
        with get_cursor(conn) as cursor:
            cursor.execute("SELECT 1 FROM infrastructure_assets WHERE asset_id = :id", {"id": asset_id})
            if not cursor.fetchone():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    connections = [AssetConnection(**row) for row in rows]

    learn_sql = None
    if learn:
        learn_sql = (
            "-- Relational JOIN query (used):\n" + CONNECTIONS_SQL.strip() +
            "\n\n-- Equivalent SQL/PGQ query:\n" + CONNECTIONS_PGQ_SQL.strip()
        )

    return PrismResponse(
        data=connections,
        meta=ResponseMeta(
            sql=learn_sql,
            execution_time_ms=round(elapsed, 2),
            operation_id="graph-connections",
        ),
    )


# ============================================================================
# N-Hop Neighborhood
# ============================================================================

NEIGHBORHOOD_CENTER_SQL = """
    SELECT asset_id, name, asset_type, status, district_id
    FROM infrastructure_assets
    WHERE asset_id = :asset_id
"""

# For the neighborhood, we use iterative Python-side hop expansion
# rather than recursive CTEs. Recursive CTEs hit cycle detection errors
# on bidirectional graph data (A->B->A). The Python approach uses a
# simple BFS with a visited set, querying one hop at a time.

NEIGHBORS_FOR_IDS_SQL = """
    SELECT DISTINCT
        CASE WHEN ac.from_asset_id IN ({id_list}) THEN ac.to_asset_id
             ELSE ac.from_asset_id END AS neighbor_id
    FROM asset_connections ac
    WHERE ac.from_asset_id IN ({id_list}) OR ac.to_asset_id IN ({id_list})
"""

NODES_FOR_IDS_SQL = """
    SELECT asset_id, name, asset_type, status, district_id
    FROM infrastructure_assets
    WHERE asset_id IN ({id_list})
"""

EDGES_FOR_IDS_SQL = """
    SELECT ac.connection_id, ac.from_asset_id, ac.to_asset_id,
           ac.connection_type, ac.description
    FROM asset_connections ac
    WHERE ac.from_asset_id IN ({id_list})
      AND ac.to_asset_id IN ({id_list})
"""

# The SQL/PGQ equivalent (shown in Learn Mode)
NEIGHBORHOOD_PGQ_SQL = """
    -- SQL/PGQ equivalent for N-hop neighborhood:
    SELECT DISTINCT
        b.asset_id, b.name, b.asset_type, b.status, b.district_id
    FROM GRAPH_TABLE (citypulse_graph
        MATCH (a) -[e]-{1,:hops} (b)
        WHERE a.asset_id = :asset_id
        COLUMNS (
            b.asset_id AS asset_id,
            b.name AS name,
            b.asset_type AS asset_type,
            b.status AS status,
            b.district_id AS district_id
        )
    )
"""


def _build_id_binds(ids):
    """Build bind variable names and params dict for a set of IDs."""
    bind_names = [f":id{i}" for i in range(len(ids))]
    bind_params = {f"id{i}": aid for i, aid in enumerate(ids)}
    return ",".join(bind_names), bind_params


def _expand_neighborhood(cursor, start_id, hops):
    """
    BFS expansion: starting from start_id, find all asset IDs
    reachable within 'hops' steps. Returns the set of all reachable IDs.
    """
    visited = {start_id}
    frontier = {start_id}

    for _ in range(hops):
        if not frontier:
            break
        bind_str, bind_params = _build_id_binds(frontier)
        sql = NEIGHBORS_FOR_IDS_SQL.format(id_list=bind_str)
        cursor.execute(sql, bind_params)
        neighbors = {row[0] for row in cursor.fetchall()}
        frontier = neighbors - visited
        visited |= frontier

    return visited


@router.get("/assets/{asset_id}/neighborhood", response_model=PrismResponse)
async def get_neighborhood(
    asset_id: int,
    hops: int = Query(1, ge=1, le=4, description="Number of hops from the center asset (1-4)"),
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Get the N-hop neighborhood subgraph around an asset.
    Returns all nodes and edges reachable within the specified number of hops.
    Useful for Cytoscape.js visualization on the frontend.
    """
    start = time.perf_counter()

    # Get center node
    with get_cursor(conn) as cursor:
        cursor.execute(NEIGHBORHOOD_CENTER_SQL, {"asset_id": asset_id})
        columns = [col[0].lower() for col in cursor.description]
        center_row = cursor.fetchone()

    if not center_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    center = _node_from_row(dict(zip(columns, center_row)))

    # BFS hop expansion to find all reachable node IDs
    with get_cursor(conn) as cursor:
        reachable_ids = _expand_neighborhood(cursor, asset_id, hops)

    # Fetch node details for all reachable IDs
    with get_cursor(conn) as cursor:
        bind_str, bind_params = _build_id_binds(reachable_ids)
        cursor.execute(NODES_FOR_IDS_SQL.format(id_list=bind_str), bind_params)
        columns = [col[0].lower() for col in cursor.description]
        node_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    nodes = [_node_from_row(row) for row in node_rows]

    # Fetch all edges between reachable nodes
    with get_cursor(conn) as cursor:
        bind_str, bind_params = _build_id_binds(reachable_ids)
        cursor.execute(EDGES_FOR_IDS_SQL.format(id_list=bind_str), bind_params)
        columns = [col[0].lower() for col in cursor.description]
        edge_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    edges = [GraphEdge(**row) for row in edge_rows]

    elapsed = (time.perf_counter() - start) * 1000

    learn_sql = None
    if learn:
        learn_sql = (
            "-- Iterative BFS expansion (used):\n" +
            "-- For each hop, query neighbors of the current frontier,\n" +
            "-- add new nodes to the visited set, repeat.\n\n" +
            NEIGHBORHOOD_PGQ_SQL.strip()
        )

    return PrismResponse(
        data=GraphNeighborhood(center=center, nodes=nodes, edges=edges),
        meta=ResponseMeta(
            sql=learn_sql,
            execution_time_ms=round(elapsed, 2),
            operation_id="graph-neighborhood",
        ),
    )


# ============================================================================
# Shortest Path
# ============================================================================

SHORTEST_PATH_SQL = """
    WITH path_search(asset_id, path_ids, path_length) AS (
        SELECT :from_id AS asset_id,
               CAST(TO_CHAR(:from_id) AS VARCHAR2(4000)) AS path_ids,
               0 AS path_length
        FROM dual
        UNION ALL
        SELECT CASE
            WHEN ac.from_asset_id = ps.asset_id THEN ac.to_asset_id
            ELSE ac.from_asset_id
        END,
        ps.path_ids || ',' || TO_CHAR(
            CASE
                WHEN ac.from_asset_id = ps.asset_id THEN ac.to_asset_id
                ELSE ac.from_asset_id
            END
        ),
        ps.path_length + 1
        FROM path_search ps
        JOIN asset_connections ac
            ON ac.from_asset_id = ps.asset_id OR ac.to_asset_id = ps.asset_id
        WHERE ps.path_length < 10
          AND INSTR(ps.path_ids, TO_CHAR(
              CASE
                  WHEN ac.from_asset_id = ps.asset_id THEN ac.to_asset_id
                  ELSE ac.from_asset_id
              END
          )) = 0
    )
    CYCLE asset_id SET is_cycle TO 1 DEFAULT 0
    SELECT path_ids, path_length
    FROM path_search
    WHERE asset_id = :to_id AND is_cycle = 0
    ORDER BY path_length
    FETCH FIRST 1 ROW ONLY
"""

SHORTEST_PATH_PGQ_SQL = """
    -- SQL/PGQ equivalent for shortest path:
    SELECT *
    FROM GRAPH_TABLE (citypulse_graph
        MATCH SHORTEST (a) -[e]-+ (b)
        WHERE a.asset_id = :from_id AND b.asset_id = :to_id
        COLUMNS (
            VERTICES ON PATH AS path_vertices,
            EDGES ON PATH AS path_edges
        )
    )
"""


@router.get("/paths", response_model=PrismResponse)
async def get_shortest_path(
    from_id: int = Query(..., description="Starting asset ID"),
    to_id: int = Query(..., description="Destination asset ID"),
    conn: oracledb.Connection = Depends(get_connection),
    learn: bool = Depends(is_learn_mode),
):
    """
    Find the shortest path between two assets in the infrastructure graph.
    Returns the ordered list of nodes and edges along the path.
    """
    start = time.perf_counter()

    # Validate both assets exist
    with get_cursor(conn) as cursor:
        cursor.execute(
            "SELECT asset_id, name, asset_type, status, district_id FROM infrastructure_assets WHERE asset_id IN (:id1, :id2)",
            {"id1": from_id, "id2": to_id}
        )
        columns = [col[0].lower() for col in cursor.description]
        asset_rows = {row[0]: dict(zip(columns, row)) for row in cursor.fetchall()}

    if from_id not in asset_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source asset {from_id} not found")
    if to_id not in asset_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Destination asset {to_id} not found")

    if from_id == to_id:
        elapsed = (time.perf_counter() - start) * 1000
        return PrismResponse(
            data=GraphPath(
                path_length=0,
                nodes=[_node_from_row(asset_rows[from_id])],
                edges=[]
            ),
            meta=ResponseMeta(
                execution_time_ms=round(elapsed, 2),
                operation_id="graph-shortest-path",
            ),
        )

    # Find shortest path using recursive CTE with cycle detection
    with get_cursor(conn) as cursor:
        cursor.execute(SHORTEST_PATH_SQL, {"from_id": from_id, "to_id": to_id})
        path_row = cursor.fetchone()

    if not path_row:
        elapsed = (time.perf_counter() - start) * 1000
        return PrismResponse(
            data={"message": "No path found between the specified assets", "from_id": from_id, "to_id": to_id},
            meta=ResponseMeta(
                sql=SHORTEST_PATH_SQL.strip() if learn else None,
                execution_time_ms=round(elapsed, 2),
                operation_id="graph-shortest-path",
            ),
        )

    path_ids_str, path_length = path_row
    path_ids = [int(x) for x in path_ids_str.split(",")]

    # Fetch all nodes along the path
    with get_cursor(conn) as cursor:
        bind_names = [f":id{i}" for i in range(len(path_ids))]
        bind_params = {f"id{i}": pid for i, pid in enumerate(path_ids)}
        cursor.execute(
            f"SELECT asset_id, name, asset_type, status, district_id FROM infrastructure_assets WHERE asset_id IN ({','.join(bind_names)})",
            bind_params
        )
        columns = [col[0].lower() for col in cursor.description]
        all_nodes = {row[0]: dict(zip(columns, row)) for row in cursor.fetchall()}

    # Build ordered node list
    nodes = [_node_from_row(all_nodes[pid]) for pid in path_ids if pid in all_nodes]

    # Fetch edges along the path (between consecutive nodes)
    edges = []
    with get_cursor(conn) as cursor:
        for i in range(len(path_ids) - 1):
            a, b = path_ids[i], path_ids[i + 1]
            cursor.execute("""
                SELECT connection_id, from_asset_id, to_asset_id, connection_type, description
                FROM asset_connections
                WHERE (from_asset_id = :a AND to_asset_id = :b)
                   OR (from_asset_id = :b AND to_asset_id = :a)
                FETCH FIRST 1 ROW ONLY
            """, {"a": a, "b": b})
            columns = [col[0].lower() for col in cursor.description]
            edge_row = cursor.fetchone()
            if edge_row:
                edges.append(GraphEdge(**dict(zip(columns, edge_row))))

    elapsed = (time.perf_counter() - start) * 1000

    learn_sql = None
    if learn:
        learn_sql = (
            "-- Recursive CTE with cycle detection (used):\n" +
            SHORTEST_PATH_SQL.strip() +
            "\n\n" + SHORTEST_PATH_PGQ_SQL.strip()
        )

    return PrismResponse(
        data=GraphPath(path_length=path_length, nodes=nodes, edges=edges),
        meta=ResponseMeta(
            sql=learn_sql,
            execution_time_ms=round(elapsed, 2),
            operation_id="graph-shortest-path",
        ),
    )
