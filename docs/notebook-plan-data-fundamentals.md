# Jupyter Notebook Plan: Data Fundamentals for AI Application Development

**Companion notebook for the Data Fundamentals presentation series**

**Version:** 1.0  
**Author:** Kirk Kirkconnell (Oracle Developer Relations)  
**Created:** April 16, 2026

---

## Overview

This document defines the cell-by-cell plan for a hands-on Jupyter Notebook that accompanies the Data Fundamentals presentation. The notebook runs inside an Oracle LiveLabs sandbox against Oracle AI Database 26ai Free (container). Target completion time is 30 minutes for the core sections, with an optional 15-minute Hybrid Vector Search section.

### Target audience

Application developers (Python, JS, Java, full-stack, AI-app builders) who may already use Oracle but are unfamiliar with newer capabilities. Mixed AI experience levels.

### Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | Oracle AI Database 26ai Free (container) | LiveLabs sandbox environment |
| Python driver | python-oracledb, thin mode | Pure Python, zero Oracle Client install, works out of the box in containers |
| Embedding model | ONNX (DEMO_MODEL), pre-loaded | In-database embeddings, no external API calls, no data egress |
| Dataset | Prism (CityPulse curated subset) | Consistent with presentation series and Prism demo app |
| Vector index | HNSW with cosine distance | Recommended default per presentation guidance |
| Graph syntax | SQL/PGQ GRAPH_TABLE | Native Oracle 26ai syntax |
| Pre-loaded objects | All tables, data, duality views, property graph, unified chunks view, ONNX model | Notebook creates only the vector index and hybrid search objects |

---

## Section 0: Welcome and Setup (~3 minutes)

### Cell 0.1 - Markdown: Title and objectives

Title, objectives, prerequisites. "By the end of this notebook, you will have connected to Oracle AI Database 26ai, explored the Prism smart city dataset, performed vector search, executed a single query combining relational, JSON, graph, and vector data, and optionally built a hybrid vector search index."

### Cell 0.2 - Markdown: Dataset context

Quick context on the Prism dataset. One short paragraph: Prism uses a curated smart city dataset with seven districts, 28 infrastructure assets (bridges, substations, pipelines, sensors, communication towers, and more), maintenance logs, inspection reports, and connectivity relationships between assets. All stored in one Oracle database, projected as relational rows, JSON documents, graph relationships, and vector embeddings.

### Cell 0.3 - Code: Configuration

Clearly labeled placeholder variables at the top of the notebook:

```python
# === CONFIGURATION - UPDATE THESE VALUES ===
DB_USER     = "your_username"
DB_PASSWORD = "your_password"
DB_DSN      = "localhost:1521/FREEPDB1"
ONNX_MODEL  = "DEMO_MODEL"
```

### Cell 0.4 - Code: Install and import dependencies

`oracledb` (thin mode), `IPython.display` for formatting. Short and minimal.

### Cell 0.5 - Code: Connect to the database

`oracledb.connect()` in thin mode using the config variables. Verify with a version check query. Print confirmation with database version.

---

## Section 1: Explore the Prism Data Model (~3 minutes)

### Cell 1.1 - Markdown: Orientation

"The Prism schema is already loaded with sample data. Let's see what's here before we build on top of it."

### Cell 1.2 - Code: List tables with row counts

Query for all Prism tables: DISTRICTS, INFRASTRUCTURE_ASSETS, OPERATIONAL_PROCEDURES, MAINTENANCE_LOGS, INSPECTION_REPORTS, INSPECTION_FINDINGS, ASSET_CONNECTIONS, DOCUMENT_CHUNKS. Display as a clean table.

### Cell 1.3 - Code: Peek at relational data

Query `infrastructure_assets` joined with `districts` to show asset_id, name, asset_type, status, and district name for a handful of rows.

### Cell 1.4 - Code: Peek at JSON data using dot notation

Query `infrastructure_assets` to show the `specifications` JSON column for bridges:

```sql
SELECT a.name, a.asset_type,
       a.specifications.spanLength_m.number() AS span_length,
       a.specifications.loadCapacity_t.number() AS load_capacity,
       a.specifications.material.string() AS material
FROM infrastructure_assets a
WHERE a.asset_type = 'bridge'
```

This shows JSON dot notation extracting typed fields alongside relational columns.

### Cell 1.5 - Code: Peek at the property graph

A `GRAPH_TABLE` query showing asset connections:

```sql
SELECT *
FROM GRAPH_TABLE (citypulse_graph
    MATCH (a IS asset) -[c IS connected_to]-> (b IS asset)
    COLUMNS (a.name AS from_asset,
             c.connection_type,
             b.name AS to_asset)
)
FETCH FIRST 10 ROWS ONLY
```

---

## Section 2: Vector Embeddings with an ONNX Model (~8 minutes)

### Cell 2.1 - Markdown: What are vector embeddings?

Embedding models derive semantic meaning from text and output arrays of numbers called vectors. Semantically similar content produces vectors that are closer together in vector space.

### Cell 2.2 - Markdown: In-database embeddings

Oracle 26ai can load ONNX embedding models directly into the database. This means vector search runs entirely inside Oracle and your data never leaves the database. No external API calls, no data egress, no network latency for embedding generation. The model sits next to your data.

### Cell 2.3 - Code: Verify the ONNX model

Verify the ONNX model is loaded and the user has access to it. Query `ALL_MINING_MODELS` filtering for `DEMO_MODEL`. Display model name, mining function, algorithm, and creation date.

### Cell 2.4 - Code: Generate a single embedding

```sql
SELECT VECTOR_EMBEDDING(DEMO_MODEL USING
    'safety incident at pump station' AS data) AS embedding
FROM DUAL
```

Print the first 10 dimensions and total dimension count using `VECTOR_DIMS()`.

### Cell 2.5 - Markdown: Insert and vectorize

"The Prism dataset already has vector embeddings pre-loaded in the DOCUMENT_CHUNKS table. Rather than re-vectorize everything (which would take a while), let's see the full pipeline in action by inserting a single new maintenance log and watching the vectors get created."

### Cell 2.6 - Code: Insert a new maintenance log and vectorize it

Insert a new maintenance log for Harbor Bridge with a realistic narrative:

> "Detected unusual vibration patterns on the north support cable during routine sensor sweep. Frequency analysis suggests possible fatigue stress at the cable anchor point near the western abutment. Corrosion visible on three secondary cable clamps. Recommending detailed structural inspection within 48 hours and temporary load restriction to single-lane traffic."

Then manually:

1. Chunk the narrative using `VECTOR_CHUNKS`
2. Generate embeddings using `VECTOR_EMBEDDING(DEMO_MODEL ...)`
3. Insert each chunk + vector into `DOCUMENT_CHUNKS`
4. Commit

This is the explicit step-by-step pipeline.

### Cell 2.7 - Code: Verify the new chunks

Query `DOCUMENT_CHUNKS` joined back for the new log_id:

```sql
SELECT dc.chunk_id, dc.chunk_seq,
       SUBSTR(dc.chunk_text, 1, 100) AS chunk_preview,
       VECTOR_DIMS(dc.embedding) AS dimensions
FROM document_chunks dc
WHERE dc.source_table = 'maintenance_logs'
  AND dc.source_id = :new_log_id
ORDER BY dc.chunk_seq
```

---

## Section 3: Create a Vector Index (~3 minutes)

### Cell 3.1 - Markdown: Why index vectors?

HNSW (Hierarchical Navigable Small Worlds) is the recommended default vector index. It provides high-recall approximate nearest neighbor search using a multi-layered in-memory graph structure. We use cosine distance, which measures the angle between vectors and focuses on meaning rather than magnitude.

### Cell 3.2 - Code: Create the HNSW vector index

```sql
CREATE VECTOR INDEX idx_chunk_embedding
    ON document_chunks(embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95
```

### Cell 3.3 - Code: Verify the index

Query `USER_INDEXES` for the new vector index, showing name, index_type, and status.

---

## Section 4: Vector Search (~5 minutes)

### Cell 4.1 - Markdown: Let's search

"Now let's search. We'll embed a natural language question and find semantically similar content across all maintenance logs, inspection reports, and inspection findings."

### Cell 4.2 - Code: Vector search (Query 1)

Vector search using the pre-loaded unified view (`v_chunks_unified`):

```sql
SELECT chunk_id, source_table,
       SUBSTR(chunk_text, 1, 120) AS chunk_preview,
       asset_name, district_name,
       VECTOR_DISTANCE(embedding,
           VECTOR_EMBEDDING(DEMO_MODEL USING
               'structural damage and corrosion on Harbor Bridge' AS data),
           COSINE) AS distance
FROM v_chunks_unified
ORDER BY distance
FETCH FIRST 5 ROWS ONLY
```

### Cell 4.3 - Markdown: Interpreting results

Cosine distance closer to 0 = more semantically similar. Results are relevant even when exact search words don't appear in the source text. Note which source tables the results came from.

### Cell 4.4 - Code: Vector search (Query 2)

Second vector search with different semantic territory: "equipment failures near water treatment causing environmental risk" to show results from different assets and source types.

---

## Section 5: The Unified Query (~8 minutes)

### Cell 5.1 - Markdown: Setting the scene

"In a polyglot persistence world, the query you're about to run would require four separate databases, four network hops, and a synchronization strategy. In Oracle 26ai, it's one query, one transaction, zero syncing."

### Cell 5.2 - Markdown: What the query will do

Walk through the four projections, step by step:

1. **Vector search** finds semantically similar maintenance and inspection content
2. **Relational JOINs** pull in asset details, district info, and inspection history
3. **JSON dot notation** extracts technical specifications from the JSON column
4. **Graph traversal** finds physically connected assets

### Cell 5.3 - Code: Unified query (table output)

A CTE-based query targeting: "What maintenance issues have affected Harbor Bridge and what is its structural condition?"

Structure:

- CTE 1 (`vector_hits`): `VECTOR_DISTANCE` + `VECTOR_EMBEDDING` for semantic search on `v_chunks_unified`
- CTE 2 (`connected_assets`): `GRAPH_TABLE(citypulse_graph ...)` to find assets connected to Harbor Bridge (sensors monitoring it, substations powering it, seawall supporting it)
- Final SELECT: joins `vector_hits` to `infrastructure_assets` and `districts`, uses JSON dot notation on `specifications` (span length, load capacity, material), includes connected asset names from the graph CTE

Display results as a table.

### Cell 5.4 - Code: Unified query (JSON output)

The same unified query wrapped with `JSON_OBJECT` / `JSON_ARRAYAGG` and formatted with `JSON_SERIALIZE(... PRETTY)` to output results as a structured JSON document. Demonstrates Oracle projecting the same relational + graph + vector results as JSON.

### Cell 5.5 - Markdown: Recap

"One database. One query. Four data shapes. Zero synchronization tax."

### Cell 5.6 - Code: Unified query (graph-driven discovery)

Second unified query from a different angle: "Which assets are connected to assets that had recent critical-severity incidents, and what do their latest inspection records show?"

This query:

- Starts from `maintenance_logs` filtered to `severity = 'critical'` in the last year
- Uses `GRAPH_TABLE` to traverse outward from those assets to find connected/dependent assets
- Joins to `inspection_reports` and `inspection_findings` for the connected assets' latest inspections
- Extracts JSON specs from the connected assets
- Runs a vector search for semantically related content across the connected assets

This shows graph traversal driving discovery (rather than just supplementing a known-asset lookup like Cell 5.3).

---

## Section 6 (Optional): Hybrid Vector Search (+15 minutes)

### Cell 6.1 - Markdown: Section header

Clearly marked: **"OPTIONAL SECTION: Hybrid Vector Search (+15 minutes)"**. "If you have time, this section demonstrates how Oracle's Hybrid Vector Index combines lexical keyword search with semantic vector search in a single index."

### Cell 6.2 - Markdown: The problem hybrid search solves

Vector search excels at semantic similarity but can miss exact matches on asset identifiers, codes, or specific terminology. Lexical search nails exact matches but misses semantically related content. Hybrid search combines both and fuses the scores.

Example: "What safety incidents involved Substation Gamma and what were the root causes?" needs semantic understanding of "root causes" AND exact matching on "Substation Gamma."

### Cell 6.3 - Code: Create dedicated hybrid search table

Create a separate table to keep the hybrid demo clean and avoid duplication with the existing `document_chunks` table:

```sql
CREATE TABLE hybrid_search_demo (
    doc_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_name  VARCHAR2(200),
    severity    VARCHAR2(20),
    source_type VARCHAR2(50),
    content     CLOB NOT NULL
)
```

Then populate it by selecting combined content from `maintenance_logs` (narrative) and `inspection_findings` (description), joining through to get `asset_name` and `severity`, inserting into the `content` column.

### Cell 6.4 - Code: Create vectorizer preference

```sql
BEGIN
    DBMS_VECTOR_CHAIN.CREATE_PREFERENCE(
        'prism_hybrid_pref',
        DBMS_VECTOR_CHAIN.VECTORIZER,
        JSON('{
            "vector_idxtype": "hnsw",
            "model": "DEMO_MODEL",
            "by": "words",
            "max": 100,
            "overlap": 10,
            "split": "recursively"
        }')
    );
END;
```

### Cell 6.5 - Code: Create the Hybrid Vector Index

```sql
CREATE HYBRID VECTOR INDEX idx_hybrid_demo
    ON hybrid_search_demo(content)
    PARAMETERS('VECTORIZER prism_hybrid_pref')
    PARALLEL 2
```

### Cell 6.6 - Code: Pure vector-only search

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "VECTOR_ONLY"`. Search text: "root cause analysis of electrical failures". Show top 5 results with vector_score.

### Cell 6.7 - Code: Pure text-only search

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "TEXT_ONLY"`. CONTAINS clause targeting "Substation Gamma". Show results with text_score.

### Cell 6.8 - Code: Full hybrid search

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "UNION"` and `"search_scorer": "rsf"`. Combines the semantic query "root cause analysis of electrical failures" with the keyword query `$Substation AND $Gamma`. Display results showing score, vector_score, and text_score side by side.

### Cell 6.9 - Markdown: Interpreting the comparison

Vector-only found semantically relevant electrical failure content but may have included results from the wrong assets. Text-only found documents mentioning "Substation Gamma" by name but missed semantically related content that used different wording. Hybrid found the union of both, scored and ranked appropriately.

### Cell 6.10 - Code: Cleanup

Drop the `hybrid_search_demo` table, index, and vectorizer preference so the environment is clean for the next attendee (or note that the LiveLabs environment resets).

---

## Section 7: Cleanup and Next Steps (~1 minute)

### Cell 7.1 - Markdown: Summary

What was accomplished:

- Connected to Oracle AI Database 26ai and explored the Prism smart city dataset across relational tables, JSON columns, a property graph, and vector embeddings
- Inserted a new maintenance log and watched the vectorization pipeline create chunks and embeddings using an in-database ONNX model
- Created an HNSW vector index and performed semantic search across all content types
- Combined relational JOINs, JSON dot notation, graph traversal, and vector search in a single SQL query

### Cell 7.2 - Markdown: Further reading

Links to additional resources:

- bit.ly/oracle-chunking
- bit.ly/oracle-hnsw
- Oracle AI Vector Search documentation

### Cell 7.3 - Code: Close connection

Close the database connection cleanly.

---

## Technical references

### Prism schema tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| DISTRICTS | City districts | district_id, name, classification, population |
| INFRASTRUCTURE_ASSETS | Physical assets | asset_id, district_id, name, asset_type, status, specifications (JSON) |
| OPERATIONAL_PROCEDURES | JSON collection table | Native JSON documents (SOPs, playbooks) |
| MAINTENANCE_LOGS | Free-text incident reports | log_id, asset_id, severity, narrative (CLOB) |
| INSPECTION_REPORTS | Structured inspections | report_id, asset_id, inspector, overall_grade, summary |
| INSPECTION_FINDINGS | Individual findings | finding_id, report_id, category, severity, description |
| ASSET_CONNECTIONS | Physical connectivity | connection_id, from_asset_id, to_asset_id, connection_type |
| DOCUMENT_CHUNKS | Chunked text + vectors | chunk_id, source_table, source_id, chunk_text, embedding (VECTOR) |

### Pre-loaded objects

| Object | Type |
|--------|------|
| CITYPULSE_GRAPH | SQL/PGQ Property Graph |
| INSPECTION_REPORT_DV | JSON Relational Duality View |
| V_CHUNKS_UNIFIED | Unified chunks view (UNION ALL of three source-specific chunk views) |
| DEMO_MODEL | ONNX embedding model (all-MiniLM-L12-v2) |

### Sample asset names (from seed data)

Bridges: Harbor Bridge, Meridian Overpass, Riverside Pedestrian Bridge

Substations: Substation Gamma, Substation Delta, Substation Epsilon

Pipelines: Pipeline North-7, Pipeline South-3, Harbor Outfall Main, Central Gas Distribution

Sensors: Harbor Bridge Sensor Array A, Harbor Bridge Sensor Array B, Flood Gauge Station R1, Air Quality Monitor NI-01, Seismic Station CC-01

Communication towers: Comms Tower Alpha, Comms Tower Beta, Harbor Relay Station

Other: Ironworks Water Treatment Plant, Riverside Pump Station, Greenfield Booster Station, Harbor Seawall Section A, Meridian Cut Retaining Wall, Northern Reservoir, Greenfield Solar Array, Northgate Freight Terminal

### Oracle 26ai features used in the notebook

- `VECTOR` data type
- `VECTOR_EMBEDDING()` for in-database embedding generation
- `VECTOR_DISTANCE()` with COSINE distance
- `VECTOR_DIMS()` for dimension inspection
- `VECTOR_CHUNKS()` for text chunking
- `CREATE VECTOR INDEX ... ORGANIZATION INMEMORY NEIGHBOR GRAPH` (HNSW)
- JSON dot notation on JSON data type columns
- `JSON_OBJECT`, `JSON_ARRAYAGG`, `JSON_SERIALIZE(... PRETTY)` for JSON output
- `GRAPH_TABLE()` with SQL/PGQ pattern matching
- `CREATE HYBRID VECTOR INDEX` with vectorizer preference
- `DBMS_VECTOR_CHAIN.CREATE_PREFERENCE` for vectorizer configuration
- `DBMS_HYBRID_VECTOR.SEARCH` for hybrid keyword + semantic search
- `FETCH FIRST N ROWS ONLY` for top-K limiting

### Hybrid search scoring methods available

| Method | Description |
|--------|-------------|
| RSF (Relative Score Fusion) | Weighted sum of normalized keyword and semantic scores |
| RRF (Reciprocal Rank Fusion) | Blends by reciprocal of rank positions |
| WRRF (Weighted Reciprocal Rank Fusion) | RRF with configurable weights |

### Hybrid search fusion modes available

| Mode | Description |
|------|-------------|
| UNION | All unique rows from both searches |
| INTERSECT | Only rows satisfying both searches |
| TEXT_ONLY | Keyword search only (via hybrid index) |
| VECTOR_ONLY | Semantic search only (via hybrid index) |
| MINUS_TEXT | Vector results minus text results |
| MINUS_VECTOR | Text results minus vector results |
