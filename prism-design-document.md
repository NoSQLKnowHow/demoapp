# Prism: Design Document

**Companion App for the Data Fundamentals Presentation Series**

**Version:** 1.0
**Author:** Kirk (Oracle Developer Relations)
**Last Updated:** March 5, 2026

---

## 1. Purpose and Vision

Prism is a developer-facing web application that brings the concepts from the Data Fundamentals presentation series to life. Where the presentation tells, Prism shows: developers interact with a single canonical dataset stored in Oracle AI Database 26ai and see that same data projected as relational rows, JSON documents, graph relationships, and vector embeddings, all without data duplication or synchronization overhead.

The application serves two complementary purposes:

- **As a live demo** during and after Data Fundamentals presentations, giving attendees a tangible environment to explore the concepts they just heard about.
- **As a self-paced learning tool** that developers can run against their own Autonomous Database (ADB) instance to understand Oracle's converged database capabilities hands-on.

### 1.1 Core Thesis

Prism exists to prove one idea: **data stored once in canonical form can be projected into whatever shape your consumers need**. This is the Unified Model Theory in action. Prism is the anti-polyglot-persistence argument made interactive.

---

## 2. Target Audience

Oracle application developers who are already using the platform but may be unaware of newer capabilities in Oracle AI Database 26ai. These developers have mixed AI experience levels, ranging from "I've heard of embeddings" to "I've built RAG pipelines." Prism meets them wherever they are via its dual-mode interface.

---

## 3. Architecture Overview

### 3.1 Technology Stack

| Layer        | Technology                                    |
|--------------|-----------------------------------------------|
| Frontend     | React (with Tailwind CSS for styling)         |
| Backend API  | FastAPI (Python)                              |
| Database     | Oracle AI Database 26ai / Autonomous Database |
| DB Driver    | python-oracledb                               |
| Embeddings   | Oracle ONNX embedding model (DEMO_MODEL)      |
| Graph Viz    | Cytoscape.js (via react-cytoscapejs)          |
| Auth         | Basic authentication (username/password)       |
| Deployment   | OCI (hosted) or local dev against own ADB      |

### 3.2 High-Level Architecture

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
│   /api/json/*         JSON Duality Views +        │
│                       MongoDB API examples        │
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
│                                                   │
│   MongoDB API access to JSON collection tables    │
└──────────────────────────────────────────────────┘
```

### 3.3 Authentication

Prism uses HTTP Basic Authentication on all API endpoints. Credentials are configured via environment variables. This is intentionally simple: the goal is to prevent unauthorized access to the hosted demo, not to build a user management system.

The React frontend stores the credentials in session state after a login prompt on first access. All subsequent API calls include the `Authorization` header.

### 3.4 The `/api/meta/*` Endpoints

These endpoints exist specifically to power Learn Mode. They return:

- The exact SQL or PL/SQL being executed for any given operation.
- Explain plans and execution statistics.
- Conceptual annotations (e.g., what cosine similarity means in the context of a specific query).

By separating this into its own API surface, the frontend can cleanly toggle between Demo Mode (calls `/api/relational/*`, `/api/json/*`, etc.) and Learn Mode (calls the same endpoints but also fetches from `/api/meta/*` to display educational context).

---

## 4. The CityPulse Dataset (Curated Subset)

Prism uses a curated subset of the CityPulse smart city dataset. Each subset naturally demonstrates a specific data projection without feeling contrived.

### 4.1 Canonical Layer

This is the single source of truth. All projections derive from these tables.

**Core Tables:**

- **DISTRICTS** — City districts with boundaries, population, and classification (residential, industrial, commercial, mixed-use).
- **INFRASTRUCTURE_ASSETS** — Physical assets: Harbor Bridge, Substation Gamma, water pipelines, communication towers, etc. Each belongs to a district, has a type, status, commissioning date, and a `specifications` column stored as the JSON data type. This JSON column holds asset-type-specific technical attributes (e.g., load capacity for a bridge, voltage rating for a substation, diameter for a pipeline) that vary by asset type.
- **OPERATIONAL_PROCEDURES** — A JSON collection table storing standard operating procedures as pure JSON documents. Each document contains a procedure ID, title, category, version, safety checklists, required equipment, step-by-step instructions, and escalation contacts. Demonstrates Oracle's native JSON document storage as a pure document store, accessible via both SQL and the MongoDB API.
- **MAINTENANCE_LOGS** — Free-text maintenance and incident reports tied to infrastructure assets. Narrative content is chunked and embedded for vector search.
- **INSPECTION_REPORTS** — Structured inspection records tied to assets. The summary field is vectorized for semantic search.
- **INSPECTION_FINDINGS** — Individual findings within inspection reports, with severity, category, and recommendations. The description field is vectorized for semantic search.
- **ASSET_CONNECTIONS** — Junction table recording physical connectivity between infrastructure assets (which pipeline feeds which substation, which sensor monitors which bridge segment). This is the foundation for graph projection.
- **DOCUMENT_CHUNKS** — Stores chunked text and vector embeddings for all vectorized content (maintenance log narratives, inspection report summaries, inspection finding descriptions). A polymorphic reference design allows chunks from any source table.

### 4.2 How Each Projection Maps

| Projection     | Source Tables                                  | Projection Mechanism              | What It Demonstrates                                         |
|---------------|------------------------------------------------|-----------------------------------|--------------------------------------------------------------|
| Relational    | All core tables                                | Direct SQL queries                | Normalized storage, JOIN-based access, JSON column in a relational table |
| JSON (Duality)| INSPECTION_REPORTS + INSPECTION_FINDINGS       | JSON Duality Views                | Nested document shape from normalized rows                    |
| JSON (Native) | OPERATIONAL_PROCEDURES                         | JSON Collection Table + MongoDB API | Native JSON document storage in Oracle, with MongoDB-compatible access |
| Graph         | ASSET_CONNECTIONS + INFRASTRUCTURE_ASSETS       | SQL/PGQ property graph            | Connectivity traversal, path finding                          |
| Vector        | DOCUMENT_CHUNKS (sourced from MAINTENANCE_LOGS, INSPECTION_REPORTS, INSPECTION_FINDINGS) | VECTOR column + HNSW index | Semantic search over narrative content                        |

### 4.3 The Unified Model Theory in Action

All projections read from the same canonical tables. When a new maintenance log is submitted through the data entry form, the following happens in a single transaction:

1. The log is inserted as a relational row in MAINTENANCE_LOGS.
2. The narrative text is chunked using VECTOR_CHUNKS.
3. Each chunk is embedded using the ONNX DEMO_MODEL.
4. The chunks and embeddings are stored in DOCUMENT_CHUNKS.

After that single write, the new data is simultaneously:

- Queryable as a relational row via SQL.
- Accessible as part of a JSON document if the related inspection report is fetched through its Duality View.
- Traversable in the graph if the associated asset has connections.
- Searchable semantically via vector search.

**No ETL. No sync jobs. No eventual consistency. One write, many reads.**

---

## 5. Feature Sections

The UI is organized into four primary sections (one per projection type), a data entry section, and a unified "Prism View" that ties them together.

### 5.1 Section: Relational Explorer

**Demo Mode:**
- Browse districts and infrastructure assets in familiar table/grid views.
- Filter, sort, and drill into asset details.
- View the JSON `specifications` column rendered inline for each asset, demonstrating JSON data living naturally inside a relational table.
- View maintenance history for a selected asset.

**Learn Mode (additions):**
- Displays the SQL query being executed for each view.
- Shows the normalized schema diagram and explains why this structure matters (data integrity, no duplication).
- Annotates the canonical layer concept: "This is the single source of truth. Every other section you see in Prism is a projection of this data."
- Explains the JSON data type column: why `specifications` is JSON (polymorphic attributes across asset types) rather than a wide table with nullable columns, and how it is queried using JSON_VALUE and dot notation in SQL.

### 5.2 Section: JSON Projection

**Demo Mode:**
- View inspection reports as nested JSON documents (inspector, findings, severity, recommendations, all in one document) rendered in a formatted code view.
- Browse OPERATIONAL_PROCEDURES as native JSON documents from the JSON collection table. These are rich, nested documents containing safety checklists, equipment lists, step-by-step instructions, and escalation contacts.
- Query procedures by category, applicable asset type, or keyword within the JSON structure.
- Edit a finding's severity in the JSON view and see it reflected in the relational view (round-trip through Duality Views).

**Learn Mode (additions):**
- Displays the JSON Duality View definition (DDL).
- Side-by-side comparison: the normalized relational rows on the left, the projected JSON document on the right.
- Explains that no data was duplicated or transformed: the Duality View is a live projection.
- Contrasts the Duality View approach with the JSON collection table (OPERATIONAL_PROCEDURES): two valid patterns for different use cases, both native to Oracle.
- **MongoDB API demonstration:** Shows the same OPERATIONAL_PROCEDURES data accessed via Oracle's MongoDB-compatible API, demonstrating that developers familiar with MongoDB's query syntax can use it directly against Oracle's JSON collection tables without changing their database. Includes example queries using MongoDB wire protocol syntax alongside the equivalent SQL, reinforcing that the data is the same regardless of access method.

### 5.3 Section: Graph Projection

**Demo Mode:**
- Interactive network visualization of CityPulse infrastructure connectivity using Cytoscape.js.
- Click an asset node to see what it's connected to (e.g., "Substation Gamma is fed by Pipeline North-7 and monitored by Sensor Array B-12").
- Path queries: "What is the shortest path between Harbor Bridge Sensor Array A and Substation Gamma?"

**Learn Mode (additions):**
- Displays the SQL/PGQ query behind each visualization.
- Contrasts the graph query with the equivalent multi-JOIN SQL that would be required without SQL/PGQ.
- Explains property graph concepts (vertices, edges, path patterns) in the context of the CityPulse data.

### 5.4 Section: Vector Search

**Demo Mode:**
- **Search interface:** Natural language search across all vectorized content (maintenance logs, inspection report summaries, inspection finding descriptions). Type "corrosion near water main" and get semantically relevant results, even if those exact words don't appear in the source text.
- **Results display:** Ranked results with similarity scores. Each result indicates its source type (maintenance log, report summary, or finding).
- **Comparison toggle:** Run the same query as a keyword/LIKE search alongside the vector search to demonstrate the difference in result quality.

**Learn Mode (additions):**

#### 5.4.1 Data Ingestion Pipeline (Learn Mode)

Walk through the pipeline that prepared content for vector search:

1. **Chunking** — How source text was broken into chunks using `VECTOR_CHUNKS`. Displays chunk boundaries, explains chunking strategies (fixed-size, semantic), and shows why chunk size matters for retrieval quality.
2. **Embedding** — How each chunk was passed through the Oracle ONNX embedding model (`DEMO_MODEL`) to produce a vector. Visualizes a single chunk becoming a high-dimensional vector. Explains that the embedding model captures semantic meaning, not just keywords.
3. **Storage** — How the resulting vectors are stored in a VECTOR data type column in the DOCUMENT_CHUNKS table, alongside the original chunk text and a reference back to the source record. Emphasizes: the vector lives with the data, not in a separate system.

#### 5.4.2 Hybrid Vector Indexes (Learn Mode)

An introductory overview:

- What hybrid indexes are: combining vector similarity search with traditional relational predicates in a single index structure.
- Why this matters: "Find maintenance logs semantically similar to 'corrosion near water' but only for assets in the Industrial District and from the last 6 months."
- How Oracle's hybrid indexes avoid the post-filtering problem (where you vector-search first, then discard most results because they don't match your filters).
- **Note:** This is positioned as a preview/introduction, not a full deep-dive.

### 5.5 Section: Data Entry

**Demo Mode:**
- **New Maintenance Log form:** Select an asset, enter severity, and write the narrative text. On submit, the log is inserted, chunked, embedded, and stored in a single operation. A confirmation displays the new log and confirms it is now searchable via vector search.
- **New Inspection Report form:** Select an asset, enter inspector name, overall grade, summary, and one or more findings (each with category, severity, description, recommendation). On submit, the report and findings are inserted, and the summary and finding descriptions are chunked, embedded, and stored. Confirmation shows the new report and confirms vector searchability.

**Learn Mode (additions):**
- Displays the complete sequence of operations that happen on submit: INSERT into the source table, VECTOR_CHUNKS call, DEMO_MODEL embedding, INSERT into DOCUMENT_CHUNKS.
- Shows the SQL and PL/SQL executed at each step.
- Highlights that this is the "one write, many reads" principle happening in real time: the data just entered is immediately available across all four projection sections.

### 5.6 Section: Prism View (Unified)

This is the "aha moment" section that ties everything together.

**Demo Mode:**
- Select any single infrastructure asset (e.g., Harbor Bridge).
- See a unified dashboard showing that one asset's data across all four projections simultaneously:
  - Relational: its row data (including the JSON specifications), district, status, dates.
  - JSON: the most recent inspection report as a document via the Duality View, plus any applicable operational procedures from the JSON collection.
  - Graph: its connectivity neighborhood.
  - Vector: the most semantically relevant maintenance logs and inspection findings.

**Learn Mode (additions):**
- Highlights that all four views hit the same canonical data.
- Shows a visual "data lineage" diagram: one INSERT into the canonical layer, four different query paths reading from it.
- Reinforces the polyglot persistence contrast: "In a polyglot architecture, this single asset's data would live in four different databases, with sync jobs between them. Here, it is one database, one write, four projections."

---

## 6. UI/UX Design

### 6.1 Global Layout

- **Top navigation bar:** App logo ("Prism"), section navigation tabs (Relational, JSON, Graph, Vector, Data Entry, Prism View), and the Demo/Learn mode toggle in the top-right corner.
- **Mode toggle:** A clear, accessible switch. When in Learn Mode, the entire UI gains a subtle visual indicator (e.g., a thin accent bar or background tint shift) so developers always know which mode they're in.
- **Content area:** Single-column primary content with contextual sidebars in Learn Mode.

### 6.2 Learn Mode Behavior

When the toggle is switched to Learn Mode:

- **SQL/Code panels** slide in below or beside each data display, showing the exact query or operation.
- **Concept cards** appear inline with concise explanations of the relevant concept.
- **Visual aids** (diagrams, animations) render where appropriate, particularly in the Vector section.
- Transitions between modes should be smooth (animated slide/fade), not jarring page reloads.

### 6.3 Design Principles

- **Clean, professional aesthetic.** This represents Oracle DevRel. No toy-app energy.
- **Data-forward.** The data is the star. UI chrome stays minimal.
- **Progressive disclosure.** Demo Mode is uncluttered. Learn Mode adds depth without overwhelming.
- **Developer-familiar patterns.** Code blocks with syntax highlighting, tab-based navigation, table views with sorting and filtering.

---

## 7. API Design (FastAPI)

### 7.1 Endpoint Structure

```
/api/v1/
├── relational/
│   ├── districts/                    GET — List districts
│   ├── districts/{id}                GET — District detail
│   ├── assets/                       GET — List assets (filterable by district, type, status)
│   ├── assets/{id}                   GET — Asset detail with specifications and maintenance history
│   └── maintenance-logs/             GET — List/search maintenance logs (keyword)
│
├── json/
│   ├── inspections/                  GET — List inspection reports as JSON documents (Duality View)
│   ├── inspections/{id}              GET — Single inspection document
│   ├── inspections/{id}              PUT — Update inspection (demonstrates Duality View round-trip)
│   ├── procedures/                   GET — List operational procedures (JSON collection)
│   ├── procedures/{id}               GET — Single procedure document
│   └── procedures/mongodb-example    GET — Returns equivalent MongoDB API query syntax (Learn Mode)
│
├── graph/
│   ├── assets/{id}/connections       GET — Direct connections for an asset
│   ├── assets/{id}/neighborhood      GET — N-hop neighborhood
│   └── paths/                        GET — Shortest path between two assets
│
├── vector/
│   ├── search/                       POST — Semantic search (query text, top-K, optional filters)
│   ├── search/keyword                POST — Keyword search (same query, for comparison)
│   ├── search/hybrid                 POST — Hybrid search (semantic + relational filters)
│   └── pipeline/explain              GET — Returns the ingestion pipeline steps (for Learn Mode)
│
├── ingest/
│   ├── maintenance-logs/             POST — Submit new maintenance log (insert + vectorize)
│   └── inspection-reports/           POST — Submit new inspection report with findings (insert + vectorize)
│
├── prism/
│   └── assets/{id}/unified           GET — All four projections for a single asset
│
└── meta/
    ├── sql/{operation_id}            GET — The SQL text for a given operation
    ├── explain/{operation_id}        GET — Explain plan for a given operation
    └── concepts/{concept_slug}       GET — Educational content for a concept
```

### 7.2 Response Envelope

All API responses follow a consistent envelope:

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

The frontend sends a custom header (e.g., `X-Prism-Mode: learn`) to signal that the backend should include SQL text and execution metadata in the `meta` block. This avoids separate round-trips for Learn Mode content on every primary request.

### 7.3 Ingest Response

The POST endpoints under `/api/ingest/` return the inserted record plus a confirmation of the vectorization pipeline:

```json
{
  "data": {
    "log_id": 412,
    "asset_id": 7,
    "narrative": "...",
    "chunks_created": 3,
    "vectors_stored": 3
  },
  "meta": {
    "pipeline_steps": [
      { "step": "insert", "sql": "INSERT INTO maintenance_logs ..." },
      { "step": "chunk", "sql": "SELECT VECTOR_CHUNKS(...) ..." },
      { "step": "embed", "sql": "SELECT VECTOR_EMBEDDING(DEMO_MODEL ...) ..." },
      { "step": "store", "sql": "INSERT INTO document_chunks ..." }
    ],
    "execution_time_ms": 87
  }
}
```

The `pipeline_steps` array is always returned for ingest operations (regardless of mode) since the vectorization process is a key part of the demo.

### 7.4 MongoDB API Access

The OPERATIONAL_PROCEDURES JSON collection table is also accessible via Oracle's MongoDB-compatible API. This provides a secondary access path that demonstrates Oracle's polyglot access capabilities without polyglot persistence.

Developers connecting via the MongoDB wire protocol can query procedures using familiar MongoDB syntax:

```javascript
// MongoDB shell / driver syntax (connecting via Oracle's MongoDB API)
db.operational_procedures.find({ "data.category": "electrical" })
db.operational_procedures.find({ "data.applicableAssetTypes": "bridge" })
db.operational_procedures.findOne({ "data.procedureId": "SOP-BR-001" })
```

The Learn Mode UI shows these MongoDB queries alongside the equivalent SQL:

```sql
-- Equivalent SQL against the same JSON collection table
SELECT json_serialize(data PRETTY) FROM operational_procedures
WHERE json_value(data, '$.category') = 'electrical';
```

This reinforces the core message: same data, same table, multiple access methods.

---

## 8. Database Schema Design

### 8.1 Canonical Tables

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
    asset_type        VARCHAR2(100) NOT NULL,  -- bridge, substation, pipeline, sensor, tower, etc.
    status            VARCHAR2(50)  DEFAULT 'active',
    commissioned_date DATE,
    description       VARCHAR2(4000),
    specifications    JSON           -- asset-type-specific attributes (JSON data type)
);
```

**Example `specifications` values by asset type:**

```json
-- Bridge
{ "spanLength_m": 485, "loadCapacity_t": 5000, "laneCount": 4, "material": "steel-concrete composite", "deckWidth_m": 22 }

-- Substation
{ "voltageRating_kv": 132, "transformerCount": 3, "peakCapacity_mw": 250, "coolingType": "ONAN/ONAF" }

-- Pipeline
{ "diameter_mm": 600, "material": "ductile iron", "pressureRating_kpa": 1200, "length_km": 12.4 }
```

### 8.2 JSON Collection Table

```sql
CREATE JSON COLLECTION TABLE operational_procedures;
```

This uses Oracle's native JSON collection table syntax, creating a table with a single `DATA` column of type JSON. The collection table is the pure document store pattern: no relational schema imposed on the documents. Each document is a self-contained operational procedure.

**Example OPERATIONAL_PROCEDURES document:**

```json
{
  "procedureId": "SOP-BR-001",
  "title": "Bridge Structural Assessment Procedure",
  "category": "structural",
  "version": "2.1",
  "lastRevised": "2025-08-20",
  "estimatedDuration_min": 240,
  "requiredPersonnel": 4,
  "applicableAssetTypes": ["bridge"],
  "safetyChecklist": [
    "Traffic management plan approved and signage deployed",
    "Fall protection harnesses inspected and worn by all personnel",
    "Under-bridge inspection platform pre-positioned and load-tested",
    "Marine traffic notified if working over navigable water",
    "Weather check: postpone if wind exceeds 40 km/h or lightning within 10 km"
  ],
  "equipment": [
    "Schmidt rebound hammer",
    "ultrasonic thickness gauge",
    "crack width comparator cards",
    "half-cell potential meter",
    "drone with high-resolution camera",
    "GPS-enabled measurement tools"
  ],
  "steps": [
    { "order": 1, "action": "Conduct drone survey of entire bridge deck and superstructure", "notes": "Capture ortho-mosaic imagery at minimum 2 cm/pixel resolution" },
    { "order": 2, "action": "Inspect all expansion joints for debris, damage, and alignment", "notes": "Measure joint gap at 3 points per joint and compare to design values" }
  ],
  "escalation": {
    "contact": "Structural Engineering Division",
    "phone": "555-0187",
    "conditions": ["Any crack exceeding 1.0 mm width", "Section loss exceeding 25%"]
  }
}
```

**MongoDB API access:** This table is simultaneously accessible via Oracle's MongoDB-compatible API, allowing developers who are familiar with MongoDB drivers and query syntax to connect via the MongoDB wire protocol and query procedures without changing their existing tooling. See Section 7.4 for query examples.

### 8.3 Remaining Canonical Tables

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
    connection_type VARCHAR2(100),  -- feeds, monitors, supports, connects-to, powers
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

### 8.4 Vector Index

Created after seed data and vector ingestion are complete (see `prism-indexes.sql`):

```sql
CREATE VECTOR INDEX idx_chunk_embedding
    ON document_chunks(embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95;
```

### 8.5 JSON Duality View

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

### 8.6 SQL/PGQ Property Graph

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

---

## 9. Deployment Design

Prism is designed to run in two configurations without code changes.

### 9.1 Local Development

1. Developer clones the repo.
2. Copies `.env.example` to `.env` and configures ADB connection details (DSN, user, password, wallet directory).
3. Runs `docker compose up` (or runs FastAPI and React dev servers directly).
4. Runs the setup script: `prism-setup.sql` creates the PRISM user, all schema objects, JSON Duality View, and SQL/PGQ property graph.
5. Runs the seed script: `python prism-seed.py` loads CityPulse structural data (districts, assets, connections, procedures) and generates narrative content (maintenance logs, inspection reports) via LLM.
6. Runs the ingestion script: `python prism-ingest.py` executes the vector ingestion pipeline (chunking, embedding, storing) so developers can see the process in action, not just the result.
7. Runs the index script: `prism-indexes.sql` creates the HNSW vector index on the populated data.

### 9.2 Hosted Demo (OCI)

A scripted, repeatable deployment process for the public-facing hosted instance.

**Step 1: Provision the Autonomous Database**

- Create an ADB instance in OCI (or use an existing one).
- Download the wallet and store credentials securely (OCI Vault recommended).

**Step 2: Create the Schema**

Run `prism-setup.sql` against the ADB instance. This script:

1. Creates the PRISM application user and grants required privileges.
2. Creates all canonical tables (DISTRICTS, INFRASTRUCTURE_ASSETS, MAINTENANCE_LOGS, INSPECTION_REPORTS, INSPECTION_FINDINGS, ASSET_CONNECTIONS, DOCUMENT_CHUNKS).
3. Creates the OPERATIONAL_PROCEDURES JSON collection table.
4. Creates standard B-tree indexes on frequently queried columns.
5. Loads the ONNX embedding model (DEMO_MODEL) into the database.
6. Creates the JSON Duality View (INSPECTION_REPORT_DV).
7. Creates the SQL/PGQ property graph (CITYPULSE_GRAPH).

**Step 3: Load Seed Data**

Run `python prism-seed.py` to populate all tables with CityPulse sample data. This script:

1. Inserts structural data inline: districts, infrastructure assets (with JSON specifications), asset connections, and operational procedures (as JSON documents).
2. Generates narrative content via OCI Generative AI: maintenance logs and inspection reports with findings, producing realistic, semantically rich text for vector search.

**Step 4: Run Vector Ingestion**

Run `python prism-ingest.py` to:

1. Read all maintenance log narratives, inspection report summaries, and inspection finding descriptions.
2. Chunk each text source using VECTOR_CHUNKS.
3. Generate embeddings using DEMO_MODEL.
4. Insert all chunks and vectors into DOCUMENT_CHUNKS.

**Step 5: Create Vector Index**

Run `prism-indexes.sql` to create the HNSW vector index on DOCUMENT_CHUNKS.embedding.

**Step 6: Deploy the Application**

- Build the React frontend (`npm run build`).
- Package the FastAPI backend and built frontend into a container image.
- Deploy to OCI Container Instances (or OKE).
- Configure environment variables (see Section 9.3) including basic auth credentials.
- Set `PRISM_MODE=hosted` and `PRISM_ALLOW_WRITES=true` (to enable data entry forms).
- Configure an OCI Load Balancer or API Gateway with HTTPS termination.

**Step 7: Validate**

- Verify authentication is enforced on all endpoints.
- Test each projection section and confirm data renders correctly.
- Submit a new maintenance log via the data entry form and confirm it appears in vector search results.
- Confirm Learn Mode displays SQL and pipeline details.
- Verify MongoDB API access to OPERATIONAL_PROCEDURES returns expected documents.

### 9.3 Environment Configuration

```
# Database
ORACLE_DSN=...
ORACLE_USER=...
ORACLE_PASSWORD=...
ORACLE_WALLET_DIR=...

# LLM (for seed data generation)
OCI_COMPARTMENT_ID=...
OCI_GENAI_ENDPOINT=https://inference.generativeai.us-chicago-1.oci.oraclecloud.com
OCI_GENAI_MODEL=meta.llama-3.2-90b-vision-instruct

# Authentication
PRISM_AUTH_USERNAME=...
PRISM_AUTH_PASSWORD=...

# Application
PRISM_MODE=local|hosted
PRISM_ALLOW_WRITES=true|false
```

---

## 10. Seed Data Requirements

The CityPulse subset needs enough volume to make demos meaningful but not so much that setup is slow. Structural data (districts, assets, connections, procedures) is defined inline in the seed script. Narrative content (maintenance logs, inspection reports and findings) is generated via OCI Generative AI for realistic, semantically rich text.

| Table                   | Approximate Row Count | Notes                                          |
|-------------------------|-----------------------|------------------------------------------------|
| DISTRICTS               | 7                     | Mix of classification types                     |
| INFRASTRUCTURE_ASSETS   | 28                    | Spread across districts, multiple types, each with JSON specifications |
| OPERATIONAL_PROCEDURES  | 9                     | JSON documents covering electrical, structural, pipeline, emergency, communications, water treatment, flood response, solar |
| ASSET_CONNECTIONS       | 25                    | Dense enough for interesting graph traversals    |
| MAINTENANCE_LOGS        | ~300 (LLM-generated)  | Rich narrative text, varying severity and dates, weighted by asset importance |
| INSPECTION_REPORTS      | ~60 (LLM-generated)   | Spread across inspectable assets, meaningful summaries |
| INSPECTION_FINDINGS     | ~120-250 (LLM-generated) | 2-5 findings per report, detailed descriptions   |
| DOCUMENT_CHUNKS         | ~800-1500             | Generated by ingestion pipeline from logs, reports, and findings |

Maintenance log narratives, inspection report summaries, and finding descriptions are the most important seed data to get right. They need to be realistic, varied, and semantically rich so that vector search produces compelling results. The LLM generation approach ensures this variety while keeping the seed data reproducible.

---

## 11. Project Structure

```
demoapp/
├── schema-data/
│   ├── .env                  # Environment configuration (not committed)
│   ├── prism-setup.sql       # Schema creation: user, tables, indexes, duality view, graph
│   ├── prism-seed.py         # Structural data + LLM-generated narrative content
│   ├── prism-ingest.py       # Vector ingestion pipeline (chunk, embed, store)
│   └── prism-indexes.sql     # HNSW vector index (run after ingestion)
├── backend/                  # FastAPI application (planned)
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   └── services/
├── frontend/                 # React application (planned)
│   ├── src/
│   └── package.json
├── .env.example
└── README.md
```

---

## 12. Future Considerations

These are explicitly out of scope for the initial version but worth noting for future iterations:

- **RAG integration:** Add an "Ask CityPulse" feature that retrieves relevant chunks via vector search, sends them as context to an LLM, and displays a generated answer. This aligns with the RAG content in the Data Fundamentals presentation and is a natural extension of the vector search section.
- **Agent memory architecture:** Demonstrate episodic, semantic, and procedural memory as projections within the canonical data layer.
- **Time series projection:** Add sensor readings from Harbor Bridge and Substation Gamma to demonstrate temporal data as a fifth projection.

---

## 13. Success Criteria

Prism succeeds if a developer who has just watched the Data Fundamentals presentation can:

1. **See the Unified Model Theory in action** by observing the same CityPulse data served as relational rows, JSON documents (both Duality Views and a native JSON collection table with MongoDB API access), graph relationships, and vector search results, all from one database.
2. **Understand the vector search pipeline** from raw text to chunks to embeddings to indexed, searchable vectors, reinforced by submitting new data and seeing it become immediately searchable.
3. **Feel the difference** between keyword search and semantic search on the same dataset.
4. **Recognize multiple access patterns** by seeing the same OPERATIONAL_PROCEDURES data queried via SQL and via MongoDB API syntax, reinforcing that Oracle supports polyglot access without polyglot persistence.
5. **Walk away knowing** that Oracle AI Database 26ai eliminates the need for polyglot persistence for these use cases, without feeling like they just watched a product commercial.

---

*This is a living document. It will evolve as we refine scope, validate technical assumptions, and begin implementation.*
