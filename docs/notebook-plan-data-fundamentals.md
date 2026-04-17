# Jupyter Notebook Plan: Data Fundamentals for AI Application Development

**Companion notebook for the Data Fundamentals presentation series**

**Version:** 1.1.2
**Author:** Kirk Kirkconnell (Oracle Developer Relations)
**Created:** April 16, 2026
**Updated:** April 17, 2026

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

### Known constraints (discovered during testing)

| Constraint | Impact | Workaround |
|------------|--------|------------|
| GRAPH_TABLE does not support LATERAL correlation | Cannot reference outer query variables inside a GRAPH_TABLE WHERE clause | Query all graph connections unconditionally in a CTE, then JOIN to filter |
| Property graph KEY columns are not exposed as PROPERTIES | `asset_id` (the KEY) cannot be used in GRAPH_TABLE COLUMNS | Use `name` (which is a PROPERTY and unique) from the graph, then JOIN back to `infrastructure_assets` to resolve IDs |

---

## Section 0: Welcome and Setup (~3 minutes)

### Cell 0.1 - Markdown: Title and objectives

Title, objectives, prerequisites. "By the end of this notebook, you will have connected to Oracle AI Database 26ai, explored the Prism smart city dataset, performed vector search, executed a single query combining relational, JSON, graph, and vector data, and optionally built a hybrid vector search index."

### Cell 0.2 - Markdown: Dataset context

Quick context on the Prism dataset. One short paragraph: Prism uses a curated smart city dataset with seven districts, 28 infrastructure assets (bridges, substations, pipelines, sensors, communication towers, and more), maintenance logs, inspection reports with findings, and connectivity relationships between assets. All stored in one Oracle database, projected as relational rows, JSON documents, graph relationships, and vector embeddings, with no duplication and no synchronization overhead.

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

`oracledb` (thin mode), `json`, `decimal`, `IPython.display` for formatting, `networkx` + `matplotlib` for graph visualization. Also defines five helper functions:

- `show_table()`: Renders query results as clean HTML tables with configurable `max_width` for column wrapping (default 80ch).
- `show_graph()`: Visualizes network graphs from `(from_node, relationship, to_node)` tuples using networkx + matplotlib. Supports node coloring by asset type and optional highlighting of specific nodes (used for critical-incident assets). Renders inline as a static PNG.
- `_json_default()`: Handles Oracle types that `json.dumps` doesn't know about natively. Converts `decimal.Decimal` (from Oracle NUMBER columns) to `float` so scores render as numbers in JSON output.
- `print_json()`: Pretty-prints JSON results from Oracle. If the result arrives as a string (e.g. from `DBMS_HYBRID_VECTOR.SEARCH`), parses it first with `json.loads()`, then prints with `json.dumps(result, indent=2, default=_json_default)`.
- `rename_fused_score()`: Renames the `score` key to `fused_score` in hybrid search result dicts. Used only in the three fused hybrid cells (UNION, INTERSECT, weighted) to make the scoring story self-documenting.

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
       a.specifications.spanLength_m.number() AS span_length_m,
       a.specifications.loadCapacity_t.number() AS load_capacity_t,
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
             c.connection_type AS relationship,
             b.name AS to_asset)
)
FETCH FIRST 10 ROWS ONLY
```

### Cell 1.6 - Code: Visualize the connectivity graph

Queries ALL graph connections (not the first-10 subset from the table above), fetches asset types from `infrastructure_assets` for node coloring, and renders the full Prism infrastructure connectivity graph using the `show_graph` helper. Nodes colored by asset type with a legend.

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

Insert a new maintenance log for Harbor Bridge with a realistic narrative about vibration patterns, fatigue stress, and corrosion. **Before inserting, cleans up any previous runs** by deleting document_chunks and maintenance_logs matching the lab narrative (identified by the phrase "north support cable" + Harbor Bridge asset_id). This prevents duplicate rows from skewing vector search results on re-runs.

Then manually:

1. Chunk the narrative using `DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS` with JSON params
2. Parse the `chunk_data` field from the returned JSON objects
3. Generate embeddings using `VECTOR_EMBEDDING(DEMO_MODEL USING :chunk_text AS data)` inline in the INSERT
4. Insert each chunk + vector into `DOCUMENT_CHUNKS`
5. Commit

This matches the exact pipeline used in `prism-ingest.py`.

### Cell 2.7 - Code: Verify the new chunks

Query `DOCUMENT_CHUNKS` for the new log_id showing chunk_id, chunk_seq, chunk_text preview, and dimension count.

---

## Section 3: Create a Vector Index (~3 minutes)

### Cell 3.1 - Markdown: Why index vectors?

HNSW (Hierarchical Navigable Small Worlds) is the recommended default vector index. It provides high-recall approximate nearest neighbor search using a multi-layered in-memory graph structure. We use cosine distance, which measures the angle between vectors and focuses on meaning rather than magnitude.

### Cell 3.2 - Code: Create the HNSW vector index

**Checks `USER_INDEXES` first and drops the index if it already exists** (safe for re-runs). Then creates:

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

Vector search using the pre-loaded unified view (`v_chunks_unified`), searching for "structural damage and corrosion on Harbor Bridge". Shows source_table, source_date, chunk preview (up to 240 characters, line-wrapped via `show_table` max-width), asset_name, district_name, and cosine distance.

### Cell 4.3 - Markdown: Interpreting results

Cosine distance closer to 0 = more semantically similar. Results are relevant even when exact search words don't appear in the source text. Note which source tables the results came from.

### Cell 4.4 - Code: Vector search (Query 2)

Second vector search with different semantic territory: "equipment failures near water treatment causing environmental risk" to show results from different assets and source types. Same columns as Query 1 including source_date.

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

A CTE-based query targeting: "maintenance issues and structural condition of Harbor Bridge"

Structure:

- CTE 1 (`vector_hits`): `VECTOR_DISTANCE` + `VECTOR_EMBEDDING` for semantic search on `v_chunks_unified`
- CTE 2 (`connected`): `GRAPH_TABLE(citypulse_graph ...)` with a literal `WHERE a.name = 'Harbor Bridge'` to find connected assets
- Final SELECT: joins `vector_hits` to `infrastructure_assets` and `districts`, uses JSON dot notation on `specifications` (span length, load capacity, material), includes connected asset names via LISTAGG from the graph CTE

Display results as a table.

### Cell 5.4 - Code: Unified query (JSON output)

The same unified query but returning native JSON using `JSON_OBJECT(... RETURNING JSON)`. No `JSON_SERIALIZE` wrapper, no CLOBs. Oracle returns the JSON type directly, `python-oracledb` receives it as a Python dict, and `json.dumps(result, indent=2)` handles the pretty-printing. Demonstrates Oracle projecting the same relational + graph + vector results as structured JSON.

### Cell 5.5 - Markdown: Recap

"One database. One query. Four data shapes. Zero synchronization tax."

### Cell 5.6 - Code: Unified query (graph-driven discovery)

Second unified query from a different angle: "Which assets are connected to assets that had recent critical-severity incidents, and what do their latest inspection records show?"

**Important: This query cannot use LATERAL + GRAPH_TABLE correlation.** Oracle's GRAPH_TABLE does not allow references to outer query variables. Additionally, KEY columns (like `asset_id`) are not exposed as PROPERTIES in the graph.

The working approach:

- CTE 1 (`critical_assets`): JOINs `maintenance_logs` to `infrastructure_assets` to get asset **names** (not IDs) for critical-severity logs
- CTE 2 (`all_connections`): Queries the full `GRAPH_TABLE` unconditionally, returning from_asset, to_asset, connection_type, and to_type using **name** properties only
- CTE 3 (`impacted`): JOINs `all_connections` to `critical_assets` on `asset_name = from_asset` to filter
- CTE 4 (`latest_inspections`): ROW_NUMBER window to get each asset's most recent inspection
- Final SELECT: JOINs `impacted` to `infrastructure_assets` on `ia.name = imp.to_asset` to resolve back to relational data, extracts JSON specs, includes latest inspection grade and summary

This shows graph traversal driving discovery rather than supplementing a known-asset lookup.

### Cell 5.7 - Code: Visualize the impact graph

Reuses the `rows` variable from Cell 5.6. Extracts critical asset names for red highlighting, builds the node type map from result columns (`connected_asset` -> `asset_type`), looks up types for critical assets via a follow-up query to `infrastructure_assets`. Renders the subgraph of critical-incident assets and their connected neighbors using `show_graph`, with critical assets highlighted in red. Gracefully handles the no-results case.

---

## Section 6 (Optional): Hybrid Vector Search (+15 minutes)

### Cell 6.1 - Markdown: Section header

Clearly marked: **"OPTIONAL SECTION: Hybrid Vector Search (+15 minutes)"**. "If you have time, this section demonstrates how Oracle's Hybrid Vector Index combines lexical keyword search with semantic vector search in a single index."

### Cell 6.2 - Markdown: The problem hybrid search solves

Vector search excels at semantic similarity but can miss exact matches on asset identifiers, codes, or specific terminology. Lexical search nails exact matches but misses semantically related content that uses different wording.

Example: "What safety incidents involved Substation Gamma and what were the root causes?" needs semantic understanding of "root causes" AND exact matching on "Substation Gamma."

### Cell 6.3 - Code: Create dedicated hybrid search table

**Starts with defensive cleanup** (drops index, table, and vectorizer preference if they exist from prior runs, using try/except to handle the "does not exist" case silently). Then creates a separate table (`hybrid_search_demo`) and populates it from `maintenance_logs` (narrative) and `inspection_findings` (description), joining through to get `asset_name` and `severity`.

### Cell 6.4 - Code: Create vectorizer preference and hybrid index

Create vectorizer preference using `DBMS_VECTOR_CHAIN.CREATE_PREFERENCE` with HNSW, DEMO_MODEL, word-based chunking. Then create the hybrid vector index on the content column. **Prints a warning** about MAINTENANCE AUTO: the hybrid index chunks, embeds, and indexes all rows in the background after creation. The first search query may take 30-60 seconds while this completes.

### Cell 6.5 - Code: Pure vector-only search

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "VECTOR_ONLY"`. Search text: "root cause analysis of electrical failures". Returns JSON natively (no `JSON_SERIALIZE` wrapper needed). `python-oracledb` receives a Python dict; `print_json(result)` handles pretty-printing. Show top 5 results with `vector_score` only (no `score` column, since there is nothing to fuse in a vector-only search).

> **Markdown note before this cell:** Blockquote callout warning that the first query after index creation may take 30-60 seconds.

### Cell 6.6 - Code: Pure text-only search

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "TEXT_ONLY"`. CONTAINS clause targeting "Substation AND Gamma". Same native JSON return pattern. Show results with `text_score` only (no `score` column).

### Cell 6.7 - Code: Full hybrid search (UNION)

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "UNION"` and `"search_scorer": "rsf"`. Same native JSON return pattern. Results include `fused_score`, `vector_score`, and `text_score` (Oracle returns `score`, which is renamed to `fused_score` via `rename_fused_score()` for clarity). Display results showing all three scores side by side.

### Cell 6.8 - Markdown: Why is text_score always 0?

Teachable moment explaining UNION fusion behavior:

- With UNION, the result set includes rows from *either* search. The top 5 by combined score come purely from the vector side because the semantic query scores high. Those rows don't contain "Substation" and "Gamma", so their text_score is 0.
- The difference between `fused_score` and `vector_score` is due to RSF normalization. `vector_score` is raw semantic similarity; `fused_score` is the normalized, fused result.
- The fix: use `INTERSECT` fusion, which only returns rows appearing in **both** searches.

### Cell 6.9 - Code: Hybrid search with INTERSECT fusion

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "INTERSECT"` and `"search_scorer": "rsf"`. Same native JSON return pattern with `fused_score` rename. Now every result has non-zero values for both `text_score` and `vector_score`.

### Cell 6.10 - Markdown: Tuning the balance

Transition explaining that every row now has both scores, then introducing `score_weight` as a tuning knob. RSF lets you control how much influence each search type has on the final score. Increasing the text weight tells Oracle to favor results where the keyword match is strong.

### Cell 6.11 - Code: Hybrid search with heavier text weighting

`DBMS_HYBRID_VECTOR.SEARCH` with `"search_fusion": "UNION"`, text `score_weight: 5` (vs vector `score_weight: 1`), and `"contains": "Substation OR Gamma"` (OR instead of AND to cast a wider net). Same native JSON return pattern with `fused_score` rename. Results containing "Substation" or "Gamma" get a significant scoring boost, shifting which results rise to the top.

### Cell 6.12 - Markdown: Weighting explanation

With `score_weight` set to 5 on the text side, keyword-matching results get a significant boost. Compare `text_score` and `vector_score` columns to see how weighting shifts the ranking. This is a tunable parameter, not a code change.

### Cell 6.13 - Markdown: Interpreting the comparison

- **Vector-only** found semantically relevant electrical failure content, but may have included results from other assets entirely.
- **Text-only** found documents mentioning "Substation Gamma" by name, but missed semantically related content that used different wording.
- **Hybrid (UNION)** showed that with equal weights, vector results dominate the top-K and text_score is 0.
- **Hybrid (INTERSECT)** returned only results matching both searches, with non-zero scores on both sides.
- **Hybrid (weighted text)** demonstrated that score_weight is a tunable dial that shifts which results rise to the top.

### Cell 6.14 - Markdown: Cleanup header

### Cell 6.15 - Code: Cleanup

Drop the `hybrid_search_demo` table, index, and vectorizer preference.

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
| MAINTENANCE_LOGS | Free-text incident reports | log_id, asset_id, severity, narrative (VARCHAR2) |
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

### Property graph definition

```sql
CREATE PROPERTY GRAPH citypulse_graph
    VERTEX TABLES (
        infrastructure_assets
            KEY (asset_id)
            LABEL asset
            PROPERTIES (name, asset_type, status, district_id)
    )
    EDGE TABLES (
        asset_connections
            KEY (connection_id)
            SOURCE KEY (from_asset_id) REFERENCES infrastructure_assets (asset_id)
            DESTINATION KEY (to_asset_id) REFERENCES infrastructure_assets (asset_id)
            LABEL connected_to
            PROPERTIES (connection_type, description)
    );
```

**Note:** The KEY column (`asset_id`) is not included in PROPERTIES, so it cannot be referenced in GRAPH_TABLE COLUMNS clauses. Use `name` (which is unique) for correlation, then JOIN back to `infrastructure_assets` to resolve IDs.

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
- `DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS` for text chunking
- `CREATE VECTOR INDEX ... ORGANIZATION INMEMORY NEIGHBOR GRAPH` (HNSW)
- JSON dot notation on JSON data type columns
- `JSON_OBJECT(... RETURNING JSON)` for native JSON output (no `JSON_SERIALIZE`, no CLOBs)
- `JSON_ARRAYAGG` for building JSON arrays from query results
- `GRAPH_TABLE()` with SQL/PGQ pattern matching
- `CREATE HYBRID VECTOR INDEX` with vectorizer preference
- `DBMS_VECTOR_CHAIN.CREATE_PREFERENCE` for vectorizer configuration
- `DBMS_HYBRID_VECTOR.SEARCH` for hybrid keyword + semantic search (returns JSON natively)
- `FETCH FIRST N ROWS ONLY` for top-K limiting

### Python dependencies

| Package | Purpose |
|---------|--------|
| `python-oracledb` (thin mode) | Database connectivity; no Oracle Client required |
| `networkx` | Graph data structure construction for visualization |
| `matplotlib` | Static inline graph rendering (PNG) |
| `json` (stdlib) | Pretty-printing native JSON values from Oracle via `print_json()` helper |
| `decimal` (stdlib) | Type checking for Oracle NUMBER values returned as `Decimal` |
| `IPython.display` | HTML table rendering in notebook cells |

### JSON approach: no CLOBs, no JSON_SERIALIZE

The notebook uses Oracle's native JSON type throughout, avoiding CLOBs entirely:

- **Unified query JSON output (Cell 5.4):** `JSON_OBJECT(... RETURNING JSON)` produces native JSON. `python-oracledb` returns a Python dict. `json.dumps()` handles pretty-printing.
- **Hybrid search cells (Cells 6.5-6.11):** `DBMS_HYBRID_VECTOR.SEARCH` returns JSON natively. No wrapper needed.
- **Why not `JSON_SERIALIZE`?** `JSON_SERIALIZE` converts JSON *to text* (VARCHAR2 or CLOB). Asking it to `RETURNING JSON` is circular and Oracle rejects it with ORA-40449. The correct approach is to let JSON-producing functions return their native type and handle formatting in Python.

### Hybrid search scoring: `fused_score` rename

Oracle's `DBMS_HYBRID_VECTOR.SEARCH` returns a field called `score` alongside `vector_score` and `text_score`. In baseline cells (VECTOR_ONLY, TEXT_ONLY), the `score` field is omitted from the return values because it's redundant (identical to the single active score). In the three fused hybrid cells (UNION, INTERSECT, weighted), the `score` field is renamed to `fused_score` via `rename_fused_score()` to make the scoring story self-documenting. This way attendees immediately understand that `fused_score` is the RSF-normalized combination of `vector_score` and `text_score`.

### Hybrid search scoring methods available

| Method | Description |
|--------|-------------|
| RSF (Relative Score Fusion) | Weighted sum of normalized keyword and semantic scores |
| RRF (Reciprocal Rank Fusion) | Blends by reciprocal of rank positions |
| WRRF (Weighted Reciprocal Rank Fusion) | RRF with configurable weights |

### Hybrid search fusion modes available

| Mode | Description | When to use |
|------|-------------|-------------|
| UNION | All unique rows from both searches | When you want broad coverage; beware that one side may dominate the top-K |
| INTERSECT | Only rows satisfying both searches | When both keyword AND semantic relevance are required |
| TEXT_ONLY | Keyword search only (via hybrid index) | Baseline comparison |
| VECTOR_ONLY | Semantic search only (via hybrid index) | Baseline comparison |
| MINUS_TEXT | Vector results minus text results | Advanced: find semantic matches that lack keyword presence |
| MINUS_VECTOR | Text results minus vector results | Advanced: find keyword matches that lack semantic relevance |

### Hybrid search tuning parameters

| Parameter | Location | Effect |
|-----------|----------|--------|
| `score_weight` (vector) | `"vector": {"score_weight": N}` | Controls vector influence on fused score (default: 1) |
| `score_weight` (text) | `"text": {"score_weight": N}` | Controls text influence on fused score (default: 1) |
| `search_fusion` | Top-level | Controls how results from both searches are combined |
| `search_scorer` | Top-level | Controls the scoring algorithm (RSF, RRF, WRRF) |
| `contains` operator | `"text": {"contains": "..."}` | Supports AND, OR, NOT for keyword logic |

### Key lesson: UNION text_score = 0

When using `UNION` fusion with equal weights, the top-K results may come entirely from one search type. If the semantic query is rich, vector results dominate and all returned rows have `text_score = 0`. This is not a bug. Solutions:

1. Switch to `INTERSECT` to require both searches to match
2. Increase `score_weight` on the text side to boost keyword-matching results
3. Use `OR` instead of `AND` in the CONTAINS clause to cast a wider keyword net
