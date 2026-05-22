# Loading an ONNX Embedding Model and Prism data set into Oracle Autonomous Database (ADB)

> **Running Oracle Database Free in a Docker/Podman container instead?** This guide does not apply to you. On Free you have direct filesystem access to the database server, so you copy the model in with `docker cp` and load it from a local directory. See [../free/load-prism-database-free.md](../free/load-prism-database-free.md) for that approach.

On Oracle Autonomous Database you have no filesystem access to the database server, so you cannot copy an ONNX model onto the host. Instead you stage the model in OCI Object Storage, pull it into the built-in `DATA_PUMP_DIR` directory with `DBMS_CLOUD.GET_OBJECT`, and load it with `DBMS_VECTOR.LOAD_ONNX_MODEL`. The model is loaded into the `ADMIN` schema and exposed to the `PRISM` user through a grant and a public synonym, so application code can reference it by the bare name `DEMO_MODEL`.

The model-loading steps (Steps 1 through 4) are run as `ADMIN`. The schema creation (Step 5) is run as `PRISM`.

## Prerequisites

- An Oracle Autonomous Database instance (running 23ai or 26ai) with `ADMIN` access
- An OCI Object Storage bucket you can upload to and create a Pre-Authenticated Request (PAR) on
- A SQL client connected through the ADB wallet (SQL Developer, SQLcl, or sqlplus with the wallet configured)
- python 3.10+ for the seed and ingest scripts

---

## Step 1: Download the Pre-Built ONNX Model

Oracle offers a pre-built, augmented version of the all-MiniLM-L12-v2 model that works directly with AI Vector Search. No conversion or augmentation needed.

Download it from Oracle's public bucket:

```bash
wget https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/VBRD9P8ZFWkKvnfhrWxkpPe8K03-JIoM5h_8EJyJcpE80c108fuUjg7R5L5O7mMZ/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2_augmented.zip
```

Unzip the file:

```bash
unzip all_MiniLM_L12_v2_augmented.zip
```

You'll get `all_MiniLM_L12_v2.onnx` (about 133 MB).

---

## Step 2: Upload the Model to OCI Object Storage and Create a PAR

Because ADB cannot read your local filesystem, the model has to live somewhere ADB can reach over HTTPS. Object Storage is that place.

1. In the OCI Console, open **Storage > Buckets** and pick (or create) a bucket in the same tenancy as your ADB.
2. Upload `all_MiniLM_L12_v2.onnx` into the bucket.
3. On the uploaded object, create a **Pre-Authenticated Request (PAR)**:
   - Scope: **Object** (this single object), not the whole bucket.
   - Access type: **Permit object reads** only.
   - Set a reasonable expiry. You only need it long enough to run Step 3 once.
4. Copy the generated PAR URL. It looks like:

   ```
   https://objectstorage.<region>.oraclecloud.com/p/<long-token>/n/<namespace>/b/<bucket>/o/all_MiniLM_L12_v2.onnx
   ```

A PAR is the lightest auth path: the URL itself carries the authorization, so no `DBMS_CLOUD` credential is required for the pull in Step 3. Treat the PAR URL as a secret while it is live, and let it expire once the model is loaded.

---

## Step 3: Pull the Model into DATA_PUMP_DIR (as ADMIN)

Connect to the database as `ADMIN` through your wallet:

```bash
sqlplus admin/<password>@<adb_tns_alias>
```

Pull the object from the PAR URL into the built-in `DATA_PUMP_DIR`. `DATA_PUMP_DIR` exists on every ADB by default and `ADMIN` can already write to it, so there is no `CREATE DIRECTORY` step.

```sql
BEGIN
    DBMS_CLOUD.GET_OBJECT(
        object_uri      => 'https://objectstorage.<region>.oraclecloud.com/p/<long-token>/n/<namespace>/b/<bucket>/o/all_MiniLM_L12_v2.onnx',
        directory_name  => 'DATA_PUMP_DIR'
    );
END;
/
```

Because we are using a PAR, no `credential_name` argument is passed. (If you were using a private bucket without a PAR, you would first call `DBMS_CLOUD.CREATE_CREDENTIAL` and pass its name here.)

Confirm the file landed:

```sql
SELECT object_name, bytes
FROM DBMS_CLOUD.LIST_FILES('DATA_PUMP_DIR')
WHERE object_name = 'all_MiniLM_L12_v2.onnx';
```

You should see the file at roughly 133 MB.

---

## Step 4: Load the ONNX Model (as ADMIN)

Still connected as `ADMIN`, load the staged file into the database as a mining model named `DEMO_MODEL`, then grant the `PRISM` user access to it.

```sql
SET SERVEROUTPUT ON

DECLARE
    v_model_name VARCHAR2(100) := 'DEMO_MODEL';
    v_onnx_file  VARCHAR2(100) := 'all_MiniLM_L12_v2.onnx';
BEGIN
    -- Drop existing model if re-running
    BEGIN
        DBMS_VECTOR.DROP_ONNX_MODEL(model_name => v_model_name, force => TRUE);
        DBMS_OUTPUT.PUT_LINE('Dropped existing model: ' || v_model_name);
    EXCEPTION
        WHEN OTHERS THEN NULL;
    END;

    -- Load the ONNX model from DATA_PUMP_DIR into the ADMIN schema
    DBMS_OUTPUT.PUT_LINE('Loading ONNX model into database...');
    DBMS_VECTOR.LOAD_ONNX_MODEL(
        directory  => 'DATA_PUMP_DIR',
        file_name  => v_onnx_file,
        model_name => v_model_name
    );
    DBMS_OUTPUT.PUT_LINE('Model loaded successfully: ' || v_model_name);
END;
/
```

The model is now owned by `ADMIN`. Expose it to `PRISM` so application code can call it by its bare name. The `PRISM` user is created in Step 5; if you have not created it yet, run these two grants after Step 5 instead.

```sql
-- Let PRISM use the model
GRANT MINING MODEL SELECT ON ADMIN.DEMO_MODEL TO prism;

-- Public synonym so PRISM (and any other user) references it as DEMO_MODEL,
-- not ADMIN.DEMO_MODEL, in VECTOR_EMBEDDING() calls.
CREATE OR REPLACE PUBLIC SYNONYM demo_model FOR admin.demo_model;
```

Verify the model loaded and produces vectors:

```sql
-- Check the model exists
SELECT model_name, algorithm, mining_function, model_size
FROM all_mining_models
WHERE model_name = 'DEMO_MODEL';

-- Generate a test embedding
SELECT VECTOR_EMBEDDING(DEMO_MODEL USING 'The quick brown fox' AS data) AS embedding
FROM dual;
```

You should see one row in the first query and a long vector of floating point numbers in the second.

---

## Step 5: Create the PRISM user, schema, tables, and views

The PRISM user is created by `ADMIN`. On ADB the user gets the `DATA` tablespace (the default application tablespace), which differs from the Free pipeline's `USERS` tablespace.

Connect as `ADMIN` and create the user and grants:

```sql
DEFINE tablespace = DATA
DEFINE dbpassword = "WelcometoOracle26ai"

SET VERIFY OFF

PROMPT
PROMPT ============================================================================
PROMPT  PRISM: Database setup (ADB)
PROMPT ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Create application user
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [1/12] Creating PRISM user...

-- Drop existing user if re-running (comment out for first-time setup)
DROP USER IF EXISTS prism CASCADE;

CREATE USER prism IDENTIFIED BY &dbpassword;

ALTER USER prism QUOTA UNLIMITED ON &tablespace;

PROMPT         User PRISM created.

-- ----------------------------------------------------------------------------
-- 2. Grant privileges
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [2/12] Granting privileges...

-- Session and object creation
GRANT CREATE SESSION TO prism;
GRANT CREATE TABLE TO prism;
GRANT CREATE VIEW TO prism;
GRANT CREATE SEQUENCE TO prism;
GRANT CREATE PROCEDURE TO prism;
GRANT CREATE TYPE TO prism;

-- JSON and graph
GRANT CREATE PROPERTY GRAPH TO prism;

-- Vector and AI
GRANT CREATE MINING MODEL TO prism;
GRANT DB_DEVELOPER_ROLE TO prism;

-- PL/SQL packages for vector operations
GRANT EXECUTE ON DBMS_VECTOR TO prism;
GRANT EXECUTE ON DBMS_VECTOR_CHAIN TO prism;

-- Model access (also shown in Step 4). Safe to run again here.
GRANT MINING MODEL SELECT ON ADMIN.DEMO_MODEL TO prism;
CREATE OR REPLACE PUBLIC SYNONYM demo_model FOR admin.demo_model;

PROMPT         Privileges granted.
```

Now connect as the `PRISM` user to create the schema objects:

```bash
sqlplus prism/<password>@<adb_tns_alias>
```

```sql
-- ----------------------------------------------------------------------------
-- 4. Create canonical tables
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [4/12] Creating canonical tables (DISTRICTS, INFRASTRUCTURE_ASSETS)...

CREATE TABLE districts (
    district_id    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           VARCHAR2(100) NOT NULL,
    classification VARCHAR2(50)  NOT NULL,
    population     NUMBER,
    area_sq_km     NUMBER(10,2),
    description    VARCHAR2(4000)
);

PROMPT         Table DISTRICTS created.

CREATE TABLE infrastructure_assets (
    asset_id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    district_id       NUMBER NOT NULL REFERENCES districts(district_id),
    name              VARCHAR2(200) NOT NULL,
    asset_type        VARCHAR2(100) NOT NULL,
    status            VARCHAR2(50)  DEFAULT 'active',
    commissioned_date DATE,
    description       VARCHAR2(4000),
    specifications    JSON
);

PROMPT         Table INFRASTRUCTURE_ASSETS created.

-- ----------------------------------------------------------------------------
-- 5. Create JSON collection table
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [5/12] Creating JSON collection table (OPERATIONAL_PROCEDURES)...

CREATE JSON COLLECTION TABLE operational_procedures;

PROMPT         Table OPERATIONAL_PROCEDURES created.

-- ----------------------------------------------------------------------------
-- 6. Create remaining canonical tables
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [6/12] Creating remaining tables...

CREATE TABLE maintenance_logs (
    log_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id     NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    log_date     DATE DEFAULT SYSDATE,
    severity     VARCHAR2(20),
    narrative    VARCHAR2(4000) NOT NULL
);

PROMPT         Table MAINTENANCE_LOGS created.

CREATE TABLE inspection_reports (
    report_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id      NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    inspector     VARCHAR2(200),
    inspect_date  DATE DEFAULT SYSDATE,
    overall_grade VARCHAR2(10),
    summary       VARCHAR2(4000)
);

PROMPT         Table INSPECTION_REPORTS created.

CREATE TABLE inspection_findings (
    finding_id     NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_id      NUMBER NOT NULL REFERENCES inspection_reports(report_id),
    category       VARCHAR2(100),
    severity       VARCHAR2(20),
    description    VARCHAR2(4000),
    recommendation VARCHAR2(4000)
);

PROMPT         Table INSPECTION_FINDINGS created.

CREATE TABLE asset_connections (
    connection_id   NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_asset_id   NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    to_asset_id     NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    connection_type VARCHAR2(100),
    description     VARCHAR2(4000)
);

PROMPT         Table ASSET_CONNECTIONS created.

CREATE TABLE document_chunks (
    chunk_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_table   VARCHAR2(50)  NOT NULL,
    source_id      NUMBER        NOT NULL,
    chunk_seq      NUMBER        NOT NULL,
    chunk_text     VARCHAR2(4000) NOT NULL,
    embedding      VECTOR        NOT NULL
);

PROMPT         Table DOCUMENT_CHUNKS created.

-- ----------------------------------------------------------------------------
-- 7. Create standard indexes
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [7/12] Creating standard indexes...

-- Infrastructure assets
CREATE INDEX idx_assets_district ON infrastructure_assets(district_id);
CREATE INDEX idx_assets_type ON infrastructure_assets(asset_type);
CREATE INDEX idx_assets_status ON infrastructure_assets(status);

PROMPT         Indexes on INFRASTRUCTURE_ASSETS created.

-- Maintenance logs
CREATE INDEX idx_maint_logs_asset ON maintenance_logs(asset_id);
CREATE INDEX idx_maint_logs_date ON maintenance_logs(log_date);
CREATE INDEX idx_maint_logs_severity ON maintenance_logs(severity);

PROMPT         Indexes on MAINTENANCE_LOGS created.

-- Inspection reports
CREATE INDEX idx_insp_reports_asset ON inspection_reports(asset_id);
CREATE INDEX idx_insp_reports_date ON inspection_reports(inspect_date);

PROMPT         Indexes on INSPECTION_REPORTS created.

-- Inspection findings
CREATE INDEX idx_insp_findings_report ON inspection_findings(report_id);
CREATE INDEX idx_insp_findings_severity ON inspection_findings(severity);

PROMPT         Indexes on INSPECTION_FINDINGS created.

-- Asset connections
CREATE INDEX idx_asset_conn_from ON asset_connections(from_asset_id);
CREATE INDEX idx_asset_conn_to ON asset_connections(to_asset_id);
CREATE INDEX idx_asset_conn_type ON asset_connections(connection_type);

PROMPT         Indexes on ASSET_CONNECTIONS created.

-- Document chunks (for lookups by source)
CREATE INDEX idx_doc_chunks_source ON document_chunks(source_table, source_id);

PROMPT         Indexes on DOCUMENT_CHUNKS created.

-- ----------------------------------------------------------------------------
-- 8. ONNX embedding model
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [8/12] ONNX embedding model already loaded by ADMIN (Steps 1-4).
PROMPT         PRISM reaches it via the DEMO_MODEL public synonym.

-- Confirm PRISM can see the model through the synonym
SELECT model_name, mining_function, algorithm
FROM all_mining_models
WHERE model_name = 'DEMO_MODEL';

-- ----------------------------------------------------------------------------
-- 9. Create JSON Duality View
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [9/12] Creating JSON Duality View (INSPECTION_REPORT_DV)...

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

PROMPT         Duality View INSPECTION_REPORT_DV created.

-- ----------------------------------------------------------------------------
-- 10. Create SQL/PGQ property graph
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [10/12] Creating SQL/PGQ property graph (CITYPULSE_GRAPH)...

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

PROMPT         Property graph CITYPULSE_GRAPH created.

-- ----------------------------------------------------------------------------
-- 11. Create vector chunk views
-- ----------------------------------------------------------------------------
-- These views pre-join DOCUMENT_CHUNKS with their source tables, making
-- vector search queries simpler in the API layer. Individual views are
-- provided for source-specific queries, and a unified view spans all
-- content types for cross-source vector search.
-- Note: These views are created now (with the schema) but will return
-- no rows until prism-seed.py and prism-ingest.py have been run.
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [11/12] Creating vector chunk views...

-- Individual source view: maintenance log chunks
CREATE OR REPLACE VIEW v_chunks_maintenance_logs AS
    SELECT dc.chunk_id, dc.source_id, dc.chunk_seq,
           dc.chunk_text, dc.embedding,
           ml.asset_id, ml.severity, ml.log_date,
           a.name AS asset_name, a.asset_type,
           d.district_id, d.name AS district_name
    FROM document_chunks dc
    JOIN maintenance_logs ml ON dc.source_id = ml.log_id
    JOIN infrastructure_assets a ON ml.asset_id = a.asset_id
    JOIN districts d ON a.district_id = d.district_id
    WHERE dc.source_table = 'maintenance_logs';

PROMPT         View V_CHUNKS_MAINTENANCE_LOGS created.

-- Individual source view: inspection report summary chunks
CREATE OR REPLACE VIEW v_chunks_inspection_reports AS
    SELECT dc.chunk_id, dc.source_id, dc.chunk_seq,
           dc.chunk_text, dc.embedding,
           ir.asset_id, ir.overall_grade, ir.inspect_date, ir.inspector,
           a.name AS asset_name, a.asset_type,
           d.district_id, d.name AS district_name
    FROM document_chunks dc
    JOIN inspection_reports ir ON dc.source_id = ir.report_id
    JOIN infrastructure_assets a ON ir.asset_id = a.asset_id
    JOIN districts d ON a.district_id = d.district_id
    WHERE dc.source_table = 'inspection_reports';

PROMPT         View V_CHUNKS_INSPECTION_REPORTS created.

-- Individual source view: inspection finding chunks
CREATE OR REPLACE VIEW v_chunks_inspection_findings AS
    SELECT dc.chunk_id, dc.source_id, dc.chunk_seq,
           dc.chunk_text, dc.embedding,
           inf.report_id, inf.category, inf.severity,
           ir.asset_id, ir.inspect_date,
           a.name AS asset_name, a.asset_type,
           d.district_id, d.name AS district_name
    FROM document_chunks dc
    JOIN inspection_findings inf ON dc.source_id = inf.finding_id
    JOIN inspection_reports ir ON inf.report_id = ir.report_id
    JOIN infrastructure_assets a ON ir.asset_id = a.asset_id
    JOIN districts d ON a.district_id = d.district_id
    WHERE dc.source_table = 'inspection_findings';

PROMPT         View V_CHUNKS_INSPECTION_FINDINGS created.

-- Unified view: all chunks joined to source data with common columns.
-- This is the primary view for cross-source vector search in the API.
CREATE OR REPLACE VIEW v_chunks_unified AS
    SELECT dc.chunk_id, dc.source_table, dc.source_id, dc.chunk_seq,
           dc.chunk_text, dc.embedding,
           ml.severity, ml.log_date AS source_date,
           a.asset_id, a.name AS asset_name, a.asset_type,
           d.district_id, d.name AS district_name
    FROM document_chunks dc
    JOIN maintenance_logs ml ON dc.source_id = ml.log_id
    JOIN infrastructure_assets a ON ml.asset_id = a.asset_id
    JOIN districts d ON a.district_id = d.district_id
    WHERE dc.source_table = 'maintenance_logs'
    UNION ALL
    SELECT dc.chunk_id, dc.source_table, dc.source_id, dc.chunk_seq,
           dc.chunk_text, dc.embedding,
           ir.overall_grade AS severity, ir.inspect_date AS source_date,
           a.asset_id, a.name AS asset_name, a.asset_type,
           d.district_id, d.name AS district_name
    FROM document_chunks dc
    JOIN inspection_reports ir ON dc.source_id = ir.report_id
    JOIN infrastructure_assets a ON ir.asset_id = a.asset_id
    JOIN districts d ON a.district_id = d.district_id
    WHERE dc.source_table = 'inspection_reports'
    UNION ALL
    SELECT dc.chunk_id, dc.source_table, dc.source_id, dc.chunk_seq,
           dc.chunk_text, dc.embedding,
           inf.severity, ir.inspect_date AS source_date,
           a.asset_id, a.name AS asset_name, a.asset_type,
           d.district_id, d.name AS district_name
    FROM document_chunks dc
    JOIN inspection_findings inf ON dc.source_id = inf.finding_id
    JOIN inspection_reports ir ON inf.report_id = ir.report_id
    JOIN infrastructure_assets a ON ir.asset_id = a.asset_id
    JOIN districts d ON a.district_id = d.district_id
    WHERE dc.source_table = 'inspection_findings';

PROMPT         View V_CHUNKS_UNIFIED created.

PROMPT
PROMPT --- Verification ---
PROMPT
PROMPT Tables created:

SELECT table_name FROM user_tables ORDER BY table_name;

PROMPT
PROMPT Views created:

SELECT view_name FROM user_views ORDER BY view_name;

PROMPT
PROMPT Property graphs created:

SELECT graph_name FROM user_property_graphs WHERE graph_name = 'CITYPULSE_GRAPH';

PROMPT
PROMPT Indexes created:

SELECT index_name, table_name FROM user_indexes ORDER BY table_name, index_name;
```

---

## Step 6: Importing data into the database and create vector embeddings

Run the Python scripts to populate the database with workshop data. These connect through the ADB wallet using the connection details in `.env`.

``` bash
# Populate tables with data.
python3 prism-seed.py

# Create vector embeddings in document_chunks table
python3 prism-ingest.py
```

`prism-ingest.py` embeds every chunk live using `DEMO_MODEL`. This is the slow step: it takes several minutes for the full dataset because each chunk requires a forward pass through the ONNX model. (A faster pre-built path exists, `prism-chunks-import.py`, which loads embeddings from `../data/document_chunks.pkl` in about a second. See `../README.md` for when to use it.)

---

## Step 7: Create vector index

Connect as the `PRISM` user and create the HNSW index after the data is loaded and embedded.

```sql
------------------------------------------------------------------------------
-- 1. Log into database as prism user
------------------------------------------------------------------------------
-- sqlplus prism/<password>@<adb_tns_alias>

------------------------------------------------------------------------------
-- 2. Create vector index
------------------------------------------------------------------------------

PROMPT
PROMPT ============================================================================
PROMPT  PRISM: Post-ingestion index creation
PROMPT ============================================================================

PROMPT
PROMPT [2/3] Creating HNSW vector index on DOCUMENT_CHUNKS...

CREATE VECTOR INDEX idx_chunk_embedding
    ON document_chunks(embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95;

PROMPT  Vector index IDX_CHUNK_EMBEDDING created.

------------------------------------------------------------------------------
-- 3. Verification
------------------------------------------------------------------------------

PROMPT
PROMPT [3/3] Verifying...

PROMPT
PROMPT Vector index:

SELECT index_name, index_type FROM user_indexes WHERE index_name = 'IDX_CHUNK_EMBEDDING';

PROMPT
PROMPT Chunk counts by source:

SELECT source_table, COUNT(*) AS chunk_count FROM document_chunks GROUP BY source_table;

PROMPT
PROMPT ============================================================================
PROMPT  Vector index created successfully.
PROMPT  Prism database is ready to use.
PROMPT ============================================================================
PROMPT
```

---

## Troubleshooting

**ORA-20404: Object not found** (from `DBMS_CLOUD.GET_OBJECT`) -- The PAR URL is wrong, expired, or scoped to the bucket instead of the object. Regenerate the PAR on the specific object with "Permit object reads" and try again.

**ORA-29532 / "directory not found" or "file not found"** (from `LOAD_ONNX_MODEL`) -- The file did not land in `DATA_PUMP_DIR`, or the name passed to `file_name` does not match. Re-run the `DBMS_CLOUD.LIST_FILES('DATA_PUMP_DIR')` check from Step 3 and confirm the exact object name.

**ORA-13606: Error from Python** -- You're trying to load a raw Hugging Face model that hasn't been augmented with the required pre/post-processing steps. Use Oracle's pre-built augmented model from the download link in Step 1.

**ORA-54426: Tensor "input_ids" contains 2 batch dimensions** -- Same issue as above. The model needs to be augmented using OML4Py before loading. Use the pre-built version to avoid this.

**`VECTOR_EMBEDDING(DEMO_MODEL ...)` raises "model does not exist" as PRISM** -- The grant or synonym from Step 4 did not run. As `ADMIN`, re-run `GRANT MINING MODEL SELECT ON ADMIN.DEMO_MODEL TO prism;` and `CREATE OR REPLACE PUBLIC SYNONYM demo_model FOR admin.demo_model;`.

---
