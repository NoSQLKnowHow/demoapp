"""
Meta router.

Powers the Learn Mode educational content: concept explanations,
schema information, and the SQL reference for operations. This is
the "teacher" behind Learn Mode.
"""

import time

import oracledb
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import verify_credentials
from app.database import get_connection, get_cursor
from app.middleware import is_learn_mode
from app.models import PrismResponse, ResponseMeta

router = APIRouter(
    prefix="/api/v1/meta",
    tags=["meta"],
    dependencies=[Depends(verify_credentials)],
)


# ============================================================================
# Concept Definitions
# ============================================================================

CONCEPTS = {
    "unified-model-theory": {
        "slug": "unified-model-theory",
        "title": "Unified Model Theory",
        "summary": "Data stored once in canonical relational form can be projected as relational rows, JSON documents, graph relationships, vector embeddings, and time series, without data duplication or ETL.",
        "body": (
            "The Unified Model Theory is the idea that a single canonical dataset, "
            "stored in normalized relational tables, can serve multiple access patterns "
            "simultaneously. Rather than copying data into separate specialized databases "
            "(a document store for JSON, a graph database for relationships, a vector "
            "database for embeddings), Oracle AI Database 26ai projects the same data "
            "into whatever shape consumers need. One write, many reads. No sync jobs, "
            "no eventual consistency, no polyglot persistence overhead."
        ),
        "related_sections": ["relational", "json", "graph", "vector"],
    },
    "json-duality-views": {
        "slug": "json-duality-views",
        "title": "JSON Duality Views",
        "summary": "Live JSON document projections over normalized relational tables. No data duplication, fully updatable.",
        "body": (
            "JSON Duality Views let you define a JSON document shape on top of "
            "existing relational tables. The view is live: when you query it, Oracle "
            "assembles the JSON document from the underlying rows on the fly. When you "
            "update the JSON document, Oracle decomposes the changes back into the "
            "appropriate relational rows. The data is never duplicated. In Prism, the "
            "inspection_report_dv view projects inspection_reports and inspection_findings "
            "as nested JSON documents, complete with insert, update, and delete support."
        ),
        "related_sections": ["json"],
    },
    "json-collection-tables": {
        "slug": "json-collection-tables",
        "title": "JSON Collection Tables",
        "summary": "Native JSON document storage in Oracle, accessible via SQL and MongoDB-compatible drivers.",
        "body": (
            "JSON Collection Tables store documents as native JSON with no predefined "
            "relational schema. They are created with CREATE JSON COLLECTION TABLE and "
            "can be queried via standard SQL (using JSON_VALUE, JSON_QUERY, etc.) or "
            "through the Oracle Database API for MongoDB, which allows pymongo and other "
            "MongoDB-compatible drivers to access the same data. In Prism, the "
            "operational_procedures table is a JSON collection containing SOPs, safety "
            "checklists, and escalation procedures as self-contained documents."
        ),
        "related_sections": ["json"],
    },
    "sql-pgq": {
        "slug": "sql-pgq",
        "title": "SQL/PGQ Property Graphs",
        "summary": "SQL-native graph queries over relational data using the SQL/PGQ standard.",
        "body": (
            "SQL/PGQ (Property Graph Queries) is an ISO SQL standard extension that "
            "lets you define property graphs over existing relational tables and query "
            "them with graph pattern matching syntax. You declare which tables are "
            "vertices and which are edges, then use MATCH clauses to express path "
            "patterns, shortest paths, and reachability queries. In Prism, the "
            "citypulse_graph projects infrastructure_assets as vertices and "
            "asset_connections as edges, enabling connectivity and path queries "
            "without leaving SQL."
        ),
        "related_sections": ["graph"],
    },
    "vector-embeddings": {
        "slug": "vector-embeddings",
        "title": "Vector Embeddings",
        "summary": "Dense numeric representations of text that capture semantic meaning, enabling similarity search.",
        "body": (
            "A vector embedding is a fixed-length array of floating-point numbers that "
            "represents the semantic meaning of a piece of text. Similar meanings produce "
            "similar vectors, even if the exact words are different. Oracle AI Database "
            "26ai stores embeddings in VECTOR columns and generates them in-database "
            "using ONNX models loaded via DBMS_VECTOR.LOAD_ONNX_MODEL. In Prism, the "
            "DEMO_MODEL generates embeddings for maintenance log narratives, inspection "
            "report summaries, and inspection finding descriptions."
        ),
        "related_sections": ["vector"],
    },
    "cosine-similarity": {
        "slug": "cosine-similarity",
        "title": "Cosine Similarity",
        "summary": "A distance metric that measures the angle between two vectors, commonly used for text similarity.",
        "body": (
            "Cosine distance measures the angle between two vectors rather than the "
            "absolute distance between their endpoints. Two vectors pointing in the same "
            "direction have a cosine distance of 0 (identical meaning), while orthogonal "
            "vectors have a distance of 1 (unrelated meaning). This is preferred over "
            "Euclidean distance for text embeddings because it is insensitive to vector "
            "magnitude, focusing purely on directional similarity. In Prism, all vector "
            "searches use VECTOR_DISTANCE with COSINE metric."
        ),
        "related_sections": ["vector"],
    },
    "chunking": {
        "slug": "chunking",
        "title": "Text Chunking",
        "summary": "Splitting text into smaller segments before embedding, to stay within model limits and improve retrieval quality.",
        "body": (
            "Embedding models have input size limits and work best on focused text "
            "segments. Chunking splits longer text into overlapping pieces (chunks) that "
            "each capture a specific idea or detail. Overlap ensures that concepts "
            "spanning chunk boundaries are still captured. In Prism, text is chunked "
            "using DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS with a max size of 1000 characters, "
            "100-character overlap, and sentence-level splitting. Each chunk is embedded "
            "and stored independently in the document_chunks table."
        ),
        "related_sections": ["vector"],
    },
    "hnsw-index": {
        "slug": "hnsw-index",
        "title": "HNSW Vector Index",
        "summary": "Hierarchical Navigable Small World graph index for fast approximate nearest neighbor search.",
        "body": (
            "HNSW is a graph-based index structure that organizes vectors into layers "
            "of navigable small-world graphs. It enables fast approximate nearest "
            "neighbor (ANN) search by traversing the graph from coarse to fine "
            "granularity. In Oracle, HNSW indexes are created with CREATE VECTOR INDEX "
            "using ORGANIZATION INMEMORY NEIGHBOR GRAPH. The TARGET ACCURACY parameter "
            "controls the tradeoff between speed and recall. In Prism, the "
            "idx_chunk_embedding index uses DISTANCE COSINE with TARGET ACCURACY 95."
        ),
        "related_sections": ["vector"],
    },
    "hybrid-search": {
        "slug": "hybrid-search",
        "title": "Hybrid Search",
        "summary": "Combining vector similarity with relational predicates in a single query.",
        "body": (
            "Hybrid search combines semantic vector similarity (finding text with "
            "similar meaning) with traditional relational filters (district, date range, "
            "severity) in a single SQL query. In a polyglot architecture, this requires "
            "searching the vector database first, then post-filtering against a relational "
            "database, discarding potentially most of the results. In Oracle's converged "
            "architecture, the WHERE clause and VECTOR_DISTANCE operate on the same table "
            "in the same query, and hybrid vector indexes can push filters into the index "
            "scan itself."
        ),
        "related_sections": ["vector"],
    },
    "rag": {
        "slug": "rag",
        "title": "Retrieval-Augmented Generation (RAG)",
        "summary": "Improving LLM responses by retrieving relevant context from a database before generating an answer.",
        "body": (
            "RAG is a pattern where a user's question is first used to retrieve relevant "
            "documents or chunks from a vector database, then those chunks are sent as "
            "context alongside the question to an LLM. This grounds the LLM's response "
            "in actual data rather than relying solely on training knowledge. Vector "
            "search is the retrieval step in RAG: better retrieval produces better "
            "answers. In Prism, the vector search endpoints provide the retrieval "
            "foundation that a future 'Ask CityPulse' RAG feature would build on."
        ),
        "related_sections": ["vector"],
    },
}


# ============================================================================
# Concept Endpoints
# ============================================================================

@router.get("/concepts", response_model=PrismResponse)
async def list_concepts():
    """List all available concept definitions (slug, title, summary only)."""
    summaries = [
        {
            "slug": c["slug"],
            "title": c["title"],
            "summary": c["summary"],
        }
        for c in CONCEPTS.values()
    ]
    return PrismResponse(
        data=summaries,
        meta=ResponseMeta(operation_id="meta-concepts-list"),
    )


@router.get("/concepts/{concept_slug}", response_model=PrismResponse)
async def get_concept(concept_slug: str):
    """Get a single concept definition by slug."""
    concept = CONCEPTS.get(concept_slug)
    if not concept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept '{concept_slug}' not found",
        )
    return PrismResponse(
        data=concept,
        meta=ResponseMeta(operation_id="meta-concept-detail"),
    )


# ============================================================================
# Schema Information
# ============================================================================

@router.get("/schema/tables", response_model=PrismResponse)
async def list_tables(
    conn: oracledb.Connection = Depends(get_connection),
):
    """List all Prism tables with row counts."""
    start = time.perf_counter()

    tables = [
        "districts", "infrastructure_assets", "operational_procedures",
        "maintenance_logs", "inspection_reports", "inspection_findings",
        "asset_connections", "document_chunks",
    ]

    result = []
    with get_cursor(conn) as cursor:
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            result.append({"table_name": table, "row_count": count})

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=result,
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="meta-schema-tables",
        ),
    )


@router.get("/schema/views", response_model=PrismResponse)
async def list_views(
    conn: oracledb.Connection = Depends(get_connection),
):
    """List all Prism views."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute("SELECT view_name FROM user_views ORDER BY view_name")
        views = [row[0] for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=views,
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="meta-schema-views",
        ),
    )


@router.get("/schema/indexes", response_model=PrismResponse)
async def list_indexes(
    conn: oracledb.Connection = Depends(get_connection),
):
    """List all Prism indexes."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute("""
            SELECT index_name, table_name, index_type
            FROM user_indexes
            ORDER BY table_name, index_name
        """)
        columns = [col[0].lower() for col in cursor.description]
        indexes = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=indexes,
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="meta-schema-indexes",
        ),
    )


@router.get("/schema/graph", response_model=PrismResponse)
async def get_graph_info(
    conn: oracledb.Connection = Depends(get_connection),
):
    """Get property graph metadata."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute("""
            SELECT graph_name FROM user_property_graphs
            ORDER BY graph_name
        """)
        graphs = [row[0] for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=graphs,
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="meta-schema-graph",
        ),
    )


@router.get("/schema/models", response_model=PrismResponse)
async def list_models(
    conn: oracledb.Connection = Depends(get_connection),
):
    """List all mining models (including ONNX embedding models)."""
    start = time.perf_counter()

    with get_cursor(conn) as cursor:
        cursor.execute("""
            SELECT model_name, algorithm, mining_function
            FROM user_mining_models
            ORDER BY model_name
        """)
        columns = [col[0].lower() for col in cursor.description]
        models = [dict(zip(columns, row)) for row in cursor.fetchall()]

    elapsed = (time.perf_counter() - start) * 1000

    return PrismResponse(
        data=models,
        meta=ResponseMeta(
            execution_time_ms=round(elapsed, 2),
            operation_id="meta-schema-models",
        ),
    )
