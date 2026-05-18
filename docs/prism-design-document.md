# Prism: Workshop design

**CityPulse dataset and companion notebooks for the data fundamentals presentation series**

**Version:** 1.4.0
**Author:** Kirk Kirkconnell (Oracle Developer Relations)
**Last Updated:** May 18, 2026

**Changes in 1.4.0** (May 18, 2026): Major restructure to reflect current scope. The deliverables today are the CityPulse dataset, schema, ingestion pipeline, and the two companion Jupyter notebooks. The Prism web application (React + FastAPI) is no longer in active development and has been relocated to §10 Future possibilities, where its original design is preserved in full for when work resumes. The main body of this document now describes what actually ships.

**Changes in 1.3.0** (May 18, 2026): Added LangGraph agent memory architecture backed by `langgraph-oracledb` (`OracleSaver` for thread checkpoints, `OracleStore` for long-term semantic memory). Moved "RAG integration" and "Agent memory architecture" from Future Considerations into the implemented feature set, since both now ship as the rag-to-agents lab. Added a Companion Labs section covering the data-fundamentals and rag-to-agents notebooks.

---

## 1. Purpose and vision

Prism brings the concepts from the Data Fundamentals presentation series to life through a curated dataset and two hands-on Jupyter notebooks. Where the presentations tell, the workshop materials show: developers work directly against a single canonical dataset stored in Oracle AI Database 26ai and see that same data accessed as relational rows, JSON documents, graph relationships, and vector embeddings, all without data duplication or synchronization overhead.

The workshop serves two complementary purposes:

- **As live workshop content** during and after Data Fundamentals presentations, giving attendees executable code they can run and modify.
- **As a self-paced learning resource** that developers can run against their own Autonomous Database (ADB) instance or a local Oracle Database Free container to understand Oracle's converged database capabilities hands-on.

In subsequent labs, developers will build on this foundation to add features and explore deeper topics in the series.

### 1.1 Core thesis

Prism exists to show one idea: **data stored once in canonical form can efficiently be projected into whatever shape your consumers need**. This is the Unified Model Theory in action, the anti-polyglot-persistence argument made tangible. The notebooks are the demonstration surface; the schema is the canonical store; the projections (relational, JSON, graph, vector) are the lenses through which developers see the same data.

---

## 2. Target audience

Application developers, especially those who might already have used the Oracle platform but may be unaware of newer developer capabilities since around Oracle 12c. These developers have mixed AI experience levels, ranging from "I've heard of vector search" to "I've built RAG pipelines and more." The notebooks meet them wherever they are: the data fundamentals lab starts at the SQL level and works up through JSON, graph, and vector; the rag-to-agents lab assumes that foundation and builds toward LangGraph agents with durable memory.

---

## 3. Architecture overview

### 3.1 Technology stack

| Layer             | Technology                                          |
|-------------------|-----------------------------------------------------|
| Database          | Oracle AI Database 26ai / Autonomous Database       |
| DB Driver         | python-oracledb                                     |
| Embeddings        | Oracle ONNX embedding model (DEMO_MODEL)            |
| Notebook runtime  | Jupyter (workshop image or local install)           |
| Agent framework   | LangGraph + Ollama (rag-to-agents lab only)         |
| Agent persistence | `langgraph-oracledb` (OracleSaver + OracleStore)    |
| LLM integration   | langchain + langchain-ollama + langchain-community  |
| Data loading      | Python scripts (`prism-seed.py`, `prism-ingest.py`) |
| Deployment        | Run notebooks locally or in workshop image          |

### 3.2 Architecture at the data layer

```
┌─────────────────────────────────────────────────────────┐
│             Jupyter notebooks (notebooks/)               │
│                                                          │
│   data_fundamentals_lab.ipynb                            │
│   rag_to_agents_lab.ipynb                                │
└────────────────────────┬────────────────────────────────┘
                         │ python-oracledb
┌────────────────────────▼────────────────────────────────┐
│              Oracle AI Database 26ai / ADB               │
│                                                          │
│   Canonical Tables (relational, normalized)              │
│   JSON Collection Table (OPERATIONAL_PROCEDURES)         │
│   JSON Column (INFRASTRUCTURE_ASSETS.specs)              │
│   JSON Duality Views (projected)                         │
│   SQL/PGQ Graph Workspace (projected)                    │
│   VECTOR columns + HNSW indexes (projected)              │
│   LangGraph memory tables (created at notebook runtime)  │
└─────────────────────────────────────────────────────────┘
```

The notebooks connect directly to the database via python-oracledb. There is no application server, no API layer, and no frontend in the current scope. Each notebook is self-contained: it opens its own connection, runs its own queries, and renders its own output (HTML tables, matplotlib charts, networkx graph visualizations).

The rag-to-agents lab additionally creates LangGraph memory tables at runtime via `langgraph-oracledb`'s `OracleSaver` (for thread checkpoints) and `OracleStore` (for long-term semantic memory). Both call `.setup()` on first run to create or migrate their tables idempotently. These tables live in the same Oracle instance as the canonical Prism data.

---

## 4. The CityPulse dataset (curated subset)

Prism uses a curated subset of the CityPulse smart city dataset. Each subset naturally demonstrates a specific data projection without feeling contrived.

### 4.1 Canonical layer

This is the single source of truth. All projections derive from these tables.

**Core tables:**

- **DISTRICTS**: City districts with boundaries, population, and classification (residential, industrial, commercial, mixed-use).
- **INFRASTRUCTURE_ASSETS**: Physical assets: Harbor Bridge, Substation Gamma, water pipelines, communication towers, etc. Each belongs to a district, has a type, status, commissioning date, and a `specifications` column stored as the JSON data type. This JSON column holds asset-type-specific technical attributes (e.g., load capacity for a bridge, voltage rating for a substation, diameter for a pipeline) that vary by asset type.
- **OPERATIONAL_PROCEDURES**: A JSON collection table storing standard operating procedures and playbooks as native JSON documents (e.g., "High Voltage Substation Inspection Protocol," "Bridge Structural Assessment Procedure," "Emergency Pipeline Leak Response"). Each document contains steps, safety checklists, required equipment, escalation contacts, and estimated durations. This is self-contained reference material with no foreign key relationships to other tables. Accessible via both SQL and the Oracle Database API for MongoDB.
- **MAINTENANCE_LOGS**: Free-text maintenance and incident reports tied to infrastructure assets. Narrative content is chunked and embedded for vector search.
- **INSPECTION_REPORTS**: Structured inspection records tied to assets. The summary field is vectorized for semantic search.
- **INSPECTION_FINDINGS**: Individual findings within inspection reports, with severity, category, and recommendations. The description field is vectorized for semantic search.
- **ASSET_CONNECTIONS**: Junction table recording physical connectivity between infrastructure assets (which pipeline feeds which substation, which sensor monitors which bridge segment). This is the foundation for graph projection.
- **DOCUMENT_CHUNKS**: Stores chunked text and vector embeddings for all vectorized content (maintenance log narratives, inspection report summaries, inspection finding descriptions). A polymorphic reference design allows chunks from any source table. This also allows multiple chunks to be associated with each piece of content.

### 4.2 How each projection maps

| Projection     | Source Tables                                  | Projection Mechanism              | What it demonstrates                                         |
|---------------|------------------------------------------------|-----------------------------------|--------------------------------------------------------------|
| Relational    | All core tables                                | Direct SQL queries                | Normalized storage, JOIN-based access, JSON column in a relational table |
| JSON (Duality)| INSPECTION_REPORTS + INSPECTION_FINDINGS       | JSON Duality Views                | Nested document shape from normalized rows                    |
| JSON (Native) | OPERATIONAL_PROCEDURES                         | JSON Collection Table             | Native JSON document storage, MongoDB API access              |
| Graph         | ASSET_CONNECTIONS + INFRASTRUCTURE_ASSETS       | SQL/PGQ property graph            | Connectivity traversal, path finding                          |
| Vector        | DOCUMENT_CHUNKS (sourced from MAINTENANCE_LOGS, INSPECTION_REPORTS, INSPECTION_FINDINGS) | VECTOR column + HNSW index | Semantic search over narrative content                        |

### 4.3 Unified Model Theory (UMT) in action

All projections read from the same canonical tables. The ingestion pipeline (`prism-ingest.py`) demonstrates the one-write-many-reads pattern at load time: for each maintenance log narrative, inspection report summary, and inspection finding description, a single transaction:

1. Inserts the source row in its canonical table (MAINTENANCE_LOGS, INSPECTION_REPORTS, or INSPECTION_FINDINGS).
2. Chunks the text using VECTOR_CHUNKS.
3. Embeds each chunk using the ONNX DEMO_MODEL.
4. Stores the chunks and embeddings in DOCUMENT_CHUNKS.

After that single write, the new data is simultaneously:

- Queryable as a relational row via SQL.
- Accessible as part of a JSON document if the related inspection report is fetched through its Duality View.
- Traversable in the graph if the associated asset has connections.
- Searchable semantically via vector search.

The rag-to-agents lab extends this pattern at runtime: when the agent's `remember` tool writes a note to long-term memory, `langgraph-oracledb`'s `OracleStore` embeds the note in-database using the same DEMO_MODEL on insert, making it immediately retrievable by `recall` (namespace lookup) or `recall_similar` (semantic search over the HNSW vector index). One Oracle instance, one embedding model, both data and agent memory living in the same converged store.

**No ETL. No sync jobs. No eventual consistency. No separate vector database. One write, many reads.**

---

## 5. Companion labs (Jupyter notebooks)

Two notebooks ship in `notebooks/`. Both run against the canonical Prism dataset described in §4. Both can be run from a workshop image or a local Python environment that meets the dependencies in the top-level `requirements.txt`.

### 5.1 `data_fundamentals_lab.ipynb`

A guided tour of the four data projections in Oracle AI Database 26ai, working through the canonical Prism schema:

- **Relational and JSON**: Tables, joins, JSON columns, JSON Duality Views, JSON_VALUE, dot notation.
- **Graph**: SQL/PGQ `GRAPH_TABLE` queries, multi-hop traversals via Python-side BFS, networkx/matplotlib visualization.
- **Vector**: `VECTOR_DISTANCE`, `VECTOR_CHUNKS`, `DBMS_VECTOR_CHAIN`, ONNX model loading, HNSW index queries.
- **Hybrid search**: Reciprocal Rank Fusion combining vector and keyword results.

Pairs with the Data Fundamentals presentation. Designed as a hands-on lab in a LiveLabs sandbox running Oracle AI Database 26ai Free.

### 5.2 `rag_to_agents_lab.ipynb`

A maturity-ladder walkthrough that progressively builds from grounded RAG up to a LangGraph agent with durable memory. The lab is structured as five sections that each map to a slide in the "From RAG to Agents: Zero to Hero" presentation:

1. **Grounded RAG**: A minimal retriever over `V_CHUNKS_UNIFIED` using in-database `DEMO_MODEL` embeddings. Demonstrates that the failure mode in RAG applications is usually not the model, it's what data gets sent to it.
2. **LLM-driven workflow**: A deterministic classify → retrieve → draft → format pipeline for incident triage. Introduces token cost as a production signal.
3. **Tools and skills**: The `@tool` decorator pattern, type signatures as the LLM's interface, SOPs ("skills") that drive agent behavior.
4. **The marquee unified query**: A single Oracle query that mixes relational lookup, SQL/PGQ graph traversal, vector search, and a JSON specifications column, returning one JSON document. The most pointed UMT demonstration in either notebook.
5. **The agent**: A LangGraph agent powered by Ollama with both short-term (thread checkpointer) and long-term (semantic store) memory, backed by `langgraph-oracledb`. Includes per-step observability traces, prompt-injection defense, and an enforced safety-net pattern for tool-calling SOPs.

Pairs with the "From RAG to Agents" presentation in the Developer Tech Days series.

### 5.3 Memory architecture (langgraph-oracledb)

The rag-to-agents lab's agent uses `langgraph-oracledb` for both LangGraph memory surfaces:

- **`OracleSaver`** is the checkpointer. It writes one row per agent step to a small set of tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`) keyed by `thread_id`. Re-running a thread rehydrates the conversation from these tables; restarting the kernel does not lose state.
- **`OracleStore`** is the long-term memory store. It writes `(namespace, key, value)` records to a configurable pair of tables (`store_bridge` and `store_vectors_bridge` in this lab, named via `table_suffix="bridge"` for readable inspection). The value is a JSON document; the embedding is computed in-database via `OracleEmbeddings(DEMO_MODEL)` on write. Queries support both exact namespace lookup and HNSW vector search.

Both call `.setup()` on first notebook run to create or migrate their tables idempotently. There is no separate DBA step or prep script for these tables; the framework owns its own schema.

Three thin tools wrap the store and become the agent's memory primitives:

- `remember(asset_name, note)` calls `store.put(("bridge_decisions", asset_name), key, {...})`.
- `recall(asset_name, limit)` calls `store.search(("bridge_decisions", asset_name), limit=limit)`.
- `recall_similar(query, asset_name=None, k)` calls `store.search(("bridge_decisions", ...), query=query, limit=k)` to run cosine-distance search over the HNSW index.

This means the agent's long-term memory lives in the same Oracle instance as the canonical Prism data, embedded with the same DEMO_MODEL, queryable by the same SQL. Rather than introducing Pinecone, Weaviate, or Redis to hold agent state, the converged store does the work.

### 5.4 Shared dataset, distinct lenses

The two notebooks read from the same canonical Prism dataset. The data fundamentals lab takes the data developer's view: how do I project this dataset four different ways and query each projection. The rag-to-agents lab takes the AI developer's view: how do I build retrieval and agent behavior on top of this dataset and persist agent state alongside it.

Both views land in the same place. One database, one canonical store, multiple shapes for different consumers. That is the UMT thesis.

---

## 6. Database schema design

### 6.1 Canonical tables

```sql
CREATE TABLE districts (
    district_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           VARCHAR2(100) NOT NULL,
    classification VARCHAR2(50)  NOT NULL,  -- residential, industrial, commercial, mixed-use
    population     NUMBER,
    area_sq_km     NUMBER(10,2),
    description    VARCHAR2(4000)
);

CREATE TABLE infrastructure_assets (
    asset_id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    district_id       NUMBER NOT NULL REFERENCES districts(district_id),
    name              VARCHAR2(200) NOT NULL,
    asset_type        VARCHAR2(100) NOT NULL,  -- bridge, substation, pipeline, sensor, tower
    status            VARCHAR2(50)  DEFAULT 'active',
    commissioned_date DATE,
    description       VARCHAR2(4000),
    specifications    JSON           -- asset-type-specific attributes (JSON data type)
);
```

**Example `specifications` values by asset type:**

```json
-- Bridge
{ "spanLength_m": 485, "loadCapacity_t": 5000, "laneCount": 4, "material": "steel-concrete composite" }

-- Substation
{ "voltageRating_kv": 132, "transformerCount": 3, "peakCapacity_mw": 250 }

-- Pipeline
{ "diameter_mm": 600, "material": "ductile iron", "pressureRating_kpa": 1200, "length_km": 12.4 }
```

### 6.2 JSON collection table

```sql
CREATE JSON COLLECTION TABLE operational_procedures;
```

**Example OPERATIONAL_PROCEDURES document:**

```json
{
  "procedureId": "SOP-HV-001",
  "title": "High Voltage Substation Inspection Protocol",
  "category": "electrical",
  "version": "3.2",
  "lastRevised": "2025-11-15",
  "estimatedDuration_min": 180,
  "requiredPersonnel": 3,
  "safetyChecklist": [
    "Verify all circuits de-energized and locked out",
    "Confirm grounding cables attached",
    "PPE inspection: arc-flash suit, insulated gloves, face shield"
  ],
  "equipment": ["thermal imaging camera", "insulation resistance tester", "partial discharge detector"],
  "steps": [
    {
      "order": 1,
      "action": "Perform visual inspection of all transformer bushings and insulators",
      "notes": "Document any discoloration, cracks, or oil leaks with photos"
    },
    {
      "order": 2,
      "action": "Conduct thermal scan of all bus connections and switchgear",
      "notes": "Flag any connection with temperature differential exceeding 10°C"
    }
  ],
  "escalation": {
    "contact": "Grid Operations Center",
    "phone": "555-0142",
    "conditions": ["Evidence of active arcing", "Transformer oil level below minimum", "Ground fault detected"]
  }
}
```

### 6.3 Remaining canonical tables

```sql
CREATE TABLE maintenance_logs (
    log_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id     NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    log_date     DATE DEFAULT SYSDATE,
    severity     VARCHAR2(20),   -- routine, warning, critical
    narrative    CLOB NOT NULL   -- free-text maintenance/incident report
);

CREATE TABLE inspection_reports (
    report_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id      NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    inspector     VARCHAR2(200),
    inspect_date  DATE DEFAULT SYSDATE,
    overall_grade VARCHAR2(10),
    summary       VARCHAR2(4000)
);

CREATE TABLE inspection_findings (
    finding_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_id      NUMBER NOT NULL REFERENCES inspection_reports(report_id),
    category       VARCHAR2(100),
    severity       VARCHAR2(20),
    description    VARCHAR2(4000),
    recommendation VARCHAR2(4000)
);

CREATE TABLE asset_connections (
    connection_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_asset_id   NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    to_asset_id     NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    connection_type VARCHAR2(100),  -- feeds, monitors, supports, connects-to
    description     VARCHAR2(4000)
);

CREATE TABLE document_chunks (
    chunk_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_table   VARCHAR2(50)  NOT NULL,  -- 'maintenance_logs', 'inspection_reports', 'inspection_findings'
    source_id      NUMBER        NOT NULL,  -- PK of the source record
    chunk_seq      NUMBER        NOT NULL,  -- ordering of chunks within a source record
    chunk_text     VARCHAR2(4000) NOT NULL, -- the chunked text
    embedding      VECTOR        NOT NULL   -- vector embedding of chunk_text
);
```

### 6.4 Vector index

```sql
CREATE VECTOR INDEX idx_chunk_embedding
    ON document_chunks(embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95;
```

### 6.5 JSON Duality View

```sql
CREATE JSON RELATIONAL DUALITY VIEW inspection_report_dv AS
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
    };
```

### 6.6 SQL/PGQ Property Graph

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

### 6.7 Vector chunk views

Four views pre-join the DOCUMENT_CHUNKS table with its source tables, eliminating complex JOINs from the notebooks.

**Individual source views** provide source-specific columns for targeted queries:

- `V_CHUNKS_MAINTENANCE_LOGS` joins chunks to maintenance logs, assets, and districts. Exposes `severity`, `log_date`, `asset_name`, `asset_type`, `district_name`.
- `V_CHUNKS_INSPECTION_REPORTS` joins chunks to inspection reports, assets, and districts. Exposes `overall_grade`, `inspect_date`, `inspector`, `asset_name`, `asset_type`, `district_name`.
- `V_CHUNKS_INSPECTION_FINDINGS` joins chunks to findings, reports, assets, and districts. Exposes `category`, `severity`, `inspect_date`, `asset_name`, `asset_type`, `district_name`.

**Unified view** (`V_CHUNKS_UNIFIED`) is a UNION ALL of all three source views with a common column set: `chunk_id`, `source_table`, `source_id`, `chunk_seq`, `chunk_text`, `embedding`, `severity`, `source_date`, `asset_id`, `asset_name`, `asset_type`, `district_id`, `district_name`. This is the primary view used by the rag-to-agents lab for cross-source vector search and hybrid search with relational filters.

Example query using the unified view:

```sql
SELECT chunk_id, source_table, chunk_text,
       asset_name, district_name, severity,
       VECTOR_DISTANCE(embedding,
           VECTOR_EMBEDDING(DEMO_MODEL USING :query AS data),
           COSINE) AS distance
FROM v_chunks_unified
WHERE district_name = :district  -- relational filter
ORDER BY distance
FETCH FIRST :top_k ROWS ONLY;
```

### 6.8 Framework-managed tables (rag-to-agents lab)

The rag-to-agents lab additionally uses tables created and managed by `langgraph-oracledb` at notebook runtime. These are not created by `prism-setup.sql`; they are created by `OracleSaver.setup()` and `OracleStore.setup()` calls in the notebook itself.

- **`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`**: Created by `OracleSaver.setup()`. Partitioned by `thread_id`. Each row represents one step of one agent thread.
- **`store_bridge`, `store_vectors_bridge`**: Created by `OracleStore.setup()` with `table_suffix="bridge"`. KV store with a JSON value column and a separate vectors table joined by FK. Built with HNSW + COSINE for `OracleEmbeddings(DEMO_MODEL)`.

All framework-managed tables live in the same PRISM schema as the canonical tables. They are cleared between runs by `notebooks/rag_to_agents_reset.sql`.

---

## 7. Deployment design

The notebooks run in two configurations: a local Python environment or a workshop image. Either way, the database setup steps are the same.

### 7.1 Setup steps

1. Clone the repo.
2. Copy `.env.example` to `.env` and configure database connection details (DSN, user, password, wallet directory if using ADB).
3. Run the setup script: `prism-setup.sql` creates all schema objects (canonical tables, JSON collection, JSON Duality View, property graph). Loads the `DEMO_MODEL` ONNX embedding model.
4. Run the seed script: `python prism-seed.py` loads CityPulse sample data from pre-generated JSON files in the `data/` directory.
5. Run the ingestion script: `python prism-ingest.py` executes the vector ingestion pipeline (chunking, embedding, storing in DOCUMENT_CHUNKS).
6. Run the indexes script: `prism-indexes.sql` creates the HNSW vector index.
7. Optional: run `notebooks/rag_to_agents_prep.sql` to create the hybrid vector index used by the rag-to-agents lab.
8. Open the notebook(s) in Jupyter and run.

**Note on seed data generation:** The `data/` directory ships with pre-generated JSON files for maintenance logs and inspection reports, so developers do not need LLM access to set up the database. If you need to regenerate this content (e.g., to change the volume or style), configure an LLM provider in `.env` and run `python prism-generate.py`. This is a one-time, optional step.

### 7.2 Environment configuration

```
# Database
ORACLE_DSN=...
ORACLE_USER=...
ORACLE_PASSWORD=...
ORACLE_WALLET_DIR=...            # leave empty for Oracle Database Free Docker

# LLM Provider (only needed for prism-generate.py, not for normal setup)
# Options: oci, claude, openai
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=...            # when LLM_PROVIDER=claude
OCI_COMPARTMENT_ID=...           # when LLM_PROVIDER=oci
OPENAI_API_KEY=...               # when LLM_PROVIDER=openai

# Ollama (rag-to-agents lab only)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
```

### 7.3 Python dependencies

The top-level `requirements.txt` is the union of all Python dependencies used anywhere in this repository (data-loader pipeline + notebooks). Use it to build a workshop image or a local virtualenv. The smaller-scoped `schema-data/requirements.txt` is the data-loader runtime only, useful when running just the database setup scripts.

---

## 8. Seed data strategy

Seed data is split into two categories with different generation strategies:

**Structural data** (defined inline in `prism-seed.py`): Districts, infrastructure assets, asset connections, and operational procedures. These are hand-authored and deterministic, producing identical results on every run.

**Narrative content** (pre-generated in `data/` directory): Maintenance logs and inspection reports with findings. These are generated once by `prism-generate.py` using an LLM (OCI Generative AI, Anthropic Claude, or OpenAI), saved as JSON files, and checked into the repository. `prism-seed.py` loads from these files on every run, making database setup fast, free, and repeatable.

The JSON files use `asset_name` as the reference key (not database IDs), so they remain valid regardless of what identity values the database generates. `prism-seed.py` resolves names to IDs after inserting the structural data.

### 8.1 Target row counts

| Table                   | Approximate Row Count | Notes                                          |
|-------------------------|-----------------------|------------------------------------------------|
| DISTRICTS               | 7                     | Mix of classification types                     |
| INFRASTRUCTURE_ASSETS   | 28                    | Spread across districts, multiple types, each with JSON specifications |
| OPERATIONAL_PROCEDURES  | 9                     | JSON documents covering electrical, structural, pipeline, emergency, and routine categories |
| MAINTENANCE_LOGS        | 200 to 400            | Rich narrative text, varying severity and dates  |
| INSPECTION_REPORTS      | 40 to 80              | Spread across assets, meaningful summaries       |
| INSPECTION_FINDINGS     | 120 to 250            | 2 to 5 findings per report, detailed descriptions   |
| ASSET_CONNECTIONS       | 25                    | Dense enough for interesting graph traversals    |
| DOCUMENT_CHUNKS         | ~800 to 1500          | Generated by ingestion pipeline from logs, reports, and findings |

### 8.2 Regenerating narrative content

If you need to regenerate the maintenance logs and inspection reports (e.g., to change volume, style, or quality):

1. Configure `LLM_PROVIDER` and the corresponding API key in `.env`.
2. Run `python prism-generate.py`.
3. Review the output files in `data/maintenance_logs.json` and `data/inspection_reports.json`.
4. Commit the updated files to the repository.

Supported providers: OCI Generative AI (`oci`), Anthropic Claude (`claude`), OpenAI (`openai`).

### 8.3 Export and re-import of document chunks

For workshop image builds where re-running the embedding pipeline against a fresh database is slow, the `prism-chunks-export.py` and `prism-chunks-import.py` scripts in `schema-data/` capture the DOCUMENT_CHUNKS table (text + embeddings + natural keys back to source rows) to a portable file and reload it into a freshly-seeded target database. This bypasses the re-embedding step entirely and is useful for distributing identical data across multiple workshop deployments.

---

## 9. Success criteria

Prism succeeds if a developer who has just watched the Data Fundamentals or "From RAG to Agents" presentation can:

1. **See the Unified Model Theory in action** by working through code that queries the same CityPulse data as relational rows, JSON documents (Duality Views, native JSON collections), graph relationships, and vector search results, all from one database.
2. **Understand the vector search pipeline** from raw text to chunks to embeddings to indexed, searchable vectors, by running `prism-ingest.py` and seeing the data become immediately searchable in the notebook.
3. **Feel the difference** between keyword search, semantic search, and hybrid search on the same dataset.
4. **Build a working agent** (rag-to-agents lab) with durable memory in Oracle, and understand why the memory architecture lives in the same database as the source data instead of a separate vector store.
5. **Walk away knowing** that Oracle AI Database 26ai eliminates the need for polyglot persistence for these use cases, without feeling like they just watched a product commercial.

---

## 10. Future possibilities

These are explicitly out of scope for the current version but worth preserving for future iterations.

### 10.1 The Prism web application

The original vision for Prism was a developer-facing web application that wrapped the dataset in an interactive UI. That work is paused, not cancelled. The full design from the prior version of this document is preserved below so that work can resume from a known specification.

#### 10.1.1 Vision

A React+FastAPI web application that brings the data fundamentals concepts to life through a clickable interface. Where the notebooks show developers the code, the web app would show non-developers and developers alike the *experience* of one canonical dataset projected through four lenses. Two complementary purposes:

- **As a live demo** during presentations, giving attendees a tangible UI to explore the concepts they just heard about.
- **As a self-paced learning tool** that developers can run against their own ADB instance.

#### 10.1.2 Technology stack

| Layer        | Technology                                    |
|--------------|-----------------------------------------------|
| Frontend     | React (with Tailwind CSS for styling)         |
| Backend API  | FastAPI (Python)                              |
| Database     | Oracle AI Database 26ai / Autonomous Database |
| DB Driver    | python-oracledb                               |
| MongoDB API  | Oracle Database API for MongoDB (pymongo)     |
| Embeddings   | Oracle ONNX embedding model (DEMO_MODEL)      |
| Graph Viz    | Cytoscape.js (via react-cytoscapejs)          |
| Auth         | Basic authentication (username/password)       |
| Deployment   | OCI (hosted) or local dev against own ADB      |

#### 10.1.3 Architecture

```
┌──────────────────────────────────────────────────┐
│                  React Frontend                   │
│                                                   │
│   ┌────────────┐  Global Toggle: Demo / Learn     │
│   │ Navigation │  ─────────────────────────────── │
│   ├────────────┤                                  │
│   │ Relational │  Each section presents a single  │
│   │ JSON       │  canonical dataset projected     │
│   │ Graph      │  through a different lens.       │
│   │ Vector     │                                  │
│   │ Data Entry │                                  │
│   └────────────┘                                  │
└────────────────────┬─────────────────────────────┘
                     │ REST API (Basic Auth)
┌────────────────────▼─────────────────────────────┐
│                 FastAPI Backend                    │
│                                                   │
│   /api/relational/*   SQL queries                 │
│   /api/json/*         JSON Duality Views + JSON    │
│                       Collection (SQL + MongoDB API)│
│   /api/graph/*        SQL/PGQ queries             │
│   /api/vector/*       Vector search operations    │
│   /api/ingest/*       Data entry + vectorization  │
│   /api/meta/*         Schema, explain plans, SQL  │
│                       text (for Learn Mode)       │
└────────────────────┬─────────────────────────────┘
                     │ python-oracledb
┌────────────────────▼─────────────────────────────┐
│          Oracle AI Database 26ai / ADB            │
│                                                   │
│   Canonical Tables (relational, normalized)       │
│   JSON Collection Table (OPERATIONAL_PROCEDURES)  │
│   JSON Column (INFRASTRUCTURE_ASSETS.specs)       │
│   JSON Duality Views (projected)                  │
│   SQL/PGQ Graph Workspace (projected)             │
│   VECTOR columns + HNSW indexes (projected)       │
└──────────────────────────────────────────────────┘
```

#### 10.1.4 Authentication

HTTP Basic Authentication on all API endpoints, configured via environment variables. Intentionally simple: the goal would have been to prevent unauthorized access to the hosted demo, not to build a user management system. Data would have been refreshed nightly and the password rotated regularly, so any data inserted would be gone in short order and any access would cease as well.

The React frontend would store the credentials in session state after a login prompt on first access. All subsequent API calls would include the `Authorization` header.

#### 10.1.5 The `/api/meta/*` endpoints

These would exist specifically to power Learn Mode. They would return:

- The exact SQL or PL/SQL being executed for any given operation.
- Explain plans and execution statistics.
- Conceptual annotations (e.g., what cosine similarity means in the context of a specific query).

By separating this into its own API surface, the frontend could cleanly toggle between Demo Mode (calls `/api/relational/*`, `/api/json/*`, etc.) and Learn Mode (calls the same endpoints but also fetches from `/api/meta/*` to display educational context).

#### 10.1.6 Feature sections (UI)

The UI would be organized into four primary sections (one per projection type), a data entry section, and a unified "Prism View" that ties them together.

**Section: Relational explorer**

*Demo Mode:* Browse districts and infrastructure assets in familiar table/grid views. Filter, sort, and drill into asset details. View the JSON `specifications` column rendered inline for each asset, demonstrating JSON data living naturally inside a relational table. View maintenance history for a selected asset.

*Learn Mode (additions):* Displays the SQL query being executed for each view. Shows the normalized schema diagram and explains why this structure matters (data integrity, no duplication). Annotates the canonical layer concept. Explains the JSON data type column: why `specifications` is JSON (polymorphic attributes across asset types) rather than a wide table with nullable columns, and how it is queried using JSON_VALUE and dot notation in SQL.

**Section: JSON projection**

Three JSON capabilities in Oracle: Duality Views (relational data projected as JSON), a JSON collection table (native document storage), and the Oracle Database API for MongoDB (accessing JSON collections through MongoDB-compatible drivers).

*Demo mode:* View inspection reports as nested JSON documents rendered in a formatted code view. Browse OPERATIONAL_PROCEDURES documents from the JSON collection table. Edit a finding's severity in the JSON view and see it reflected in the relational view (round-trip through Duality Views).

*Learn mode (additions):* Displays the JSON Duality View definition (DDL). Side-by-side comparison: the normalized relational rows on the left, the projected JSON document on the right. Explains that no data was duplicated or transformed: the Duality View is a live projection. Contrasts the Duality View approach with the JSON collection table: two valid patterns for different use cases.

*MongoDB API access (sub-section):* A split-pane view showing the same OPERATIONAL_PROCEDURES query executed two ways: a SQL query on the left, and the equivalent pymongo query on the right. Both return the same documents. A simple query builder lets users filter procedures and see the results from both access paths side by side.

**Section: Graph projection**

*Demo Mode:* Interactive network visualization of CityPulse infrastructure connectivity using Cytoscape.js. Click an asset node to see what it's connected to. Path queries: "What is the shortest path between Harbor Bridge Sensor 3 and Substation Gamma?"

*Learn mode (additions):* Displays the SQL/PGQ query behind each visualization. Contrasts the graph query with the equivalent multi-JOIN SQL that would be required without SQL/PGQ. Explains property graph concepts (vertices, edges, path patterns) in the context of the CityPulse data.

**Section: Vector Search**

*Demo mode:* Natural language search across all vectorized content. Type "corrosion near water main" and get semantically relevant results, even if those exact words don't appear in the source text. Ranked results with similarity scores. Comparison toggle: run the same query as a keyword/LIKE search alongside the vector search.

*Learn Mode (additions):*

- *Data ingestion pipeline:* Walk through chunking via `VECTOR_CHUNKS`, embedding via the ONNX DEMO_MODEL, and storage in VECTOR columns.
- *Hybrid Vector Indexes:* An introductory overview of combining vector similarity search with relational predicates in a single index structure.

**Section: Data entry**

*Demo mode:* New Maintenance Log and New Inspection Report forms. On submit, the record is inserted, chunked, embedded, and stored in a single operation. A confirmation displays the new record and confirms it is now searchable via vector search.

*Learn mode (additions):* Displays the complete sequence of operations that happen on submit: INSERT, VECTOR_CHUNKS, DEMO_MODEL embedding, INSERT into DOCUMENT_CHUNKS. Highlights that this is the "one write, many reads" principle happening in real time.

**Section: Prism View (Unified)**

The "aha moment" section. Select any single infrastructure asset (e.g., Harbor Bridge). See a unified dashboard showing that one asset's data across all four projections simultaneously: relational row data, JSON document via Duality View, graph connectivity neighborhood, semantically relevant maintenance logs and findings.

*Learn mode (additions):* Highlights that all four views hit the same canonical data. Shows a visual "data lineage" diagram: one INSERT into the canonical layer, four different query paths reading from it. Reinforces the polyglot persistence contrast.

#### 10.1.7 UI/UX design

- **Top navigation bar:** App logo ("Prism"), section navigation tabs, and the Demo/Learn mode toggle in the top-right corner.
- **Mode toggle:** A clear, accessible switch. When in Learn Mode, the entire UI gains a subtle visual indicator so developers always know which mode they're in.
- **Content area:** Single-column primary content with contextual sidebars in Learn Mode.

**Learn mode behavior:** SQL/Code panels slide in below or beside each data display. Concept cards appear inline with concise explanations. Visual aids (diagrams, animations) render where appropriate. Transitions are smooth (animated slide/fade), not jarring page reloads.

**Design principles:** Clean, professional aesthetic (no toy-app energy). Data-forward (UI chrome minimal). Progressive disclosure (Demo Mode uncluttered, Learn Mode adds depth). Developer-familiar patterns (code blocks, tabs, sortable tables).

#### 10.1.8 API design (FastAPI)

```
/api/v1/
├── relational/
│   ├── districts/                    GET. List districts
│   ├── districts/{id}                GET. District detail
│   ├── assets/                       GET. List assets (filterable by district, type, status)
│   ├── assets/{id}                   GET. Asset detail with specifications and maintenance history
│   └── maintenance-logs/             GET. List/search maintenance logs (keyword)
│
├── json/
│   ├── inspections/                  GET. List inspection reports as JSON documents (Duality View)
│   ├── inspections/{id}              GET. Single inspection document
│   ├── inspections/{id}              PUT. Update inspection (demonstrates Duality View round-trip)
│   ├── procedures/                   GET. List operational procedures (JSON collection, via SQL)
│   ├── procedures/{id}               GET. Single procedure document
│   └── procedures/mongodb            GET. Same query via MongoDB API (for side-by-side comparison)
│
├── graph/
│   ├── assets/{id}/connections       GET. Direct connections for an asset
│   ├── assets/{id}/neighborhood      GET. N-hop neighborhood
│   └── paths/                        GET. Shortest path between two assets
│
├── vector/
│   ├── search/                       POST. Semantic search (query text, top-K, optional filters)
│   ├── search/keyword                POST. Keyword search (same query, for comparison)
│   ├── search/hybrid                 POST. Hybrid search (semantic + relational filters)
│   └── pipeline/explain              GET. Returns the ingestion pipeline steps (for Learn Mode)
│
├── ingest/
│   ├── maintenance-logs/             POST. Submit new maintenance log (insert + vectorize)
│   └── inspection-reports/           POST. Submit new inspection report with findings (insert + vectorize)
│
├── prism/
│   └── assets/{id}/unified           GET. All four projections for a single asset
│
└── meta/
    ├── sql/{operation_id}            GET. The SQL text for a given operation
    ├── explain/{operation_id}        GET. Explain plan for a given operation
    └── concepts/{concept_slug}       GET. Educational content for a concept
```

Response envelope:

```json
{
  "data": { },
  "meta": {
    "sql": "SELECT ... (only populated when Learn Mode header is sent)",
    "execution_time_ms": 12,
    "operation_id": "vector-search-cosine"
  }
}
```

The frontend would send a custom header (e.g., `X-Prism-Mode: learn`) to signal that the backend should include SQL text and execution metadata in the `meta` block.

#### 10.1.9 Hosted demo deployment (OCI)

The scripted deployment process for a public-facing hosted instance would have been:

1. **Provision the Autonomous Database.** Create an ADB instance in OCI. Download the wallet and store credentials securely (OCI Vault).
2. **Create the schema.** Run `prism-setup.sql` against the ADB instance.
3. **Load seed data.** Run `python prism-seed.py` to populate all tables.
4. **Run vector ingestion.** Run `python prism-ingest.py`.
5. **Create indexes.** Run `prism-indexes.sql`.
6. **Deploy the application.** Build the React frontend (`npm run build`). Package the FastAPI backend and built frontend into a container image. Deploy to OCI Container Instances (or OKE). Configure environment variables. Set `PRISM_MODE=hosted` and `PRISM_ALLOW_WRITES=true`. Configure an OCI Load Balancer or API Gateway with HTTPS termination.
7. **Validate.** Verify authentication is enforced on all endpoints. Test each projection section. Submit a new maintenance log and confirm it appears in vector search.

### 10.2 Additional roadmap items

- **Time series projection:** Add sensor readings from Harbor Bridge and Substation Gamma to demonstrate temporal data as a fifth projection.
- **Memory architecture depth:** The current rag-to-agents lab gives developers the raw retrieval primitives (`recall` / `recall_similar` over `OracleStore`). Future work covers hierarchical memory, episodic vs. semantic vs. procedural, summarization on write, eviction policies, and per-user/per-team scoping via namespaces. This is the topic of the follow-up presentation in the agents series.
- **Hybrid search expansion:** The rag-to-agents notebook uses `DBMS_HYBRID_VECTOR.SEARCH`. Future work could expose this through a more structured API for use across more notebooks and (eventually) the web app.
- **Workshop image builds:** A reproducible container image with all dependencies (the top-level `requirements.txt`), Ollama models, and the notebooks pre-installed. Cuts setup time at workshops from "follow these eight steps" to "open the notebook."

---

*This is a living document. It will evolve as scope shifts and new lab content is added.*
