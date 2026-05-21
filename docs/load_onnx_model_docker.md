# Loading an ONNX Embedding Model into Oracle Database Free (Docker/Podman)

> **Running Oracle Autonomous Database (ADB) in OCI instead?** This guide does not apply to you. ADB has no filesystem access to the database server, so you must stage the model through OCI Object Storage. See [load_onnx_model_adb.md](load_onnx_model_adb.md) for that approach.

On Oracle Database Free in a Docker or Podman container, you have direct filesystem access to the database server, so loading an ONNX model is straightforward: copy the file into the container, point a database directory at it, and load it with `DBMS_VECTOR`. No Object Storage, no credentials, no PAR URLs needed. This guide is geared more towards using Docker, but it could be easily changed for Podman since the images are interchangeable.

## Prerequisites

- A running Oracle Database Free imag in either a Docker or Podman container
- The ability to run something like `docker cp` to copy and a file into that container (host shell access)
- `sysdba` access to the container's database, plus the PRISM user (created by `prism-setup.sql`)

---

## Step 1: Download the Pre-Built ONNX Model

Oracle provides a pre-built, augmented version of the all-MiniLM-L12-v2 model that works directly with AI Vector Search. No conversion or augmentation needed.

Download it from Oracle's public bucket:

```bash
wget https://adwc4pm.objectstorage.us-ashburn-1.oci.customer-oci.com/p/VBRD9P8ZFWkKvnfhrWxkpPe8K03-JIoM5h_8EJyJcpE80c108fuUjg7R5L5O7mMZ/n/adwc4pm/b/OML-Resources/o/all_MiniLM_L12_v2_augmented.zip
```

Unzip it:

```bash
unzip all_MiniLM_L12_v2_augmented.zip
```

You'll get `all_MiniLM_L12_v2.onnx` (about 133 MB).

---

## Step 2: Copy the Model into the Docker/Podman container

From your host machine, copy the model into a directory inside the running container. Replace `<container_name>` with your container's name (find it with `docker ps` in Docker).

```bash
# Create the target directory inside the container (if it doesn't exist)
docker exec <container_name> mkdir -p /opt/oracle/models

# Copy the model into the container
docker cp all_MiniLM_L12_v2.onnx <container_name>:/opt/oracle/models/
```

Again, these instructions are for Docker, so translate to Podman if that's what you're using.

---

## Step 3: Create the PRISM user and GRANT privs as SYS

Connect as `sysdba` and create an Oracle directory object that maps to the container path, then grant the PRISM user access to it.

```bash
sqlplus sys/<password>@localhost:1521/FREEPDB1 as sysdba
```

```sql
DEFINE tablespace = USERS
DEFINE pdb_name   = FREEPDB1
DEFINE dbpassword = "WelcometoOracle26ai"

SET VERIFY OFF

PROMPT
PROMPT ============================================================================
PROMPT  PRISM: Database Setup
PROMPT ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Switch to PDB and Create Application User
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [1/12] Creating PRISM user...

ALTER SESSION SET CONTAINER = &pdb_name;

-- Drop existing user if re-running (comment out for first-time setup)
DROP USER IF EXISTS prism CASCADE;

CREATE USER prism IDENTIFIED BY &dbpassword DEFAULT TABLESPACE &tablespace TEMPORARY TABLESPACE TEMP;

ALTER USER prism QUOTA UNLIMITED ON &tablespace;

PROMPT         User PRISM created.

-- ----------------------------------------------------------------------------
-- 2. Grant Privileges
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [2/12] Granting privileges...

-- Session and object creation
CREATE OR REPLACE DIRECTORY model_dir AS '/opt/oracle/models';
GRANT CONNECT, RESOURCE TO PRISM;
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

-- Grant access to the DEMO_MODEL ONNX embedding model (owned by ADMIN)
-- and create a public synonym so PRISM (and any other user) can reference
-- it by its bare name in VECTOR_EMBEDDING() calls.
GRANT READ, WRITE ON DIRECTORY model_dir TO prism;

PROMPT         Privileges granted.
```

---

## Step 4: Verify the Model

```sql
-- Check the model exists
SELECT model_name, algorithm, mining_function, model_size
FROM user_mining_models
WHERE model_name = 'DEMO_MODEL';
```

Expected output:
```
MODEL_NAME    ALGORITHM  MINING_FUNCTION  MODEL_SIZE
----------    ---------  ---------------  ----------
DEMO_MODEL    ONNX       EMBEDDING        133322334
```

Test embedding generation:

```sql
-- Generate a test embedding
SELECT VECTOR_EMBEDDING(DEMO_MODEL USING 'The quick brown fox' AS data) AS embedding
FROM dual;
```

You should see a long vector of floating point numbers.

---

## Step 5: Log in as PRISM user and create tables, indexes, etc.

```bash
sqlplus prism/<password>@localhost:1521/FREEPDB1
```

```sql
-- ----------------------------------------------------------------------------
-- 4. Create Canonical Tables
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
-- 5. Create JSON Collection Table
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [5/12] Creating JSON collection table (OPERATIONAL_PROCEDURES)...

CREATE JSON COLLECTION TABLE operational_procedures;

PROMPT         Table OPERATIONAL_PROCEDURES created.

-- ----------------------------------------------------------------------------
-- 6. Create Remaining Canonical Tables
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
-- 7. Create Standard Indexes
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
-- 8. Load ONNX Embedding Model
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [8/12] ONNX Embedding Model
PROMPT         NOTE: Model loading is environment-specific. Uncomment one of
PROMPT         the options below or load the model manually.

-- Note: The DEMO_MODEL is loaded from the Oracle-provided ONNX model
-- repository. This step requires network access from the database.
-- On ADB, the model may already be available. Adjust the model loading
-- approach based on your environment.

-- ============================================================
-- Run as: PRISM (or any user with CREATE MINING MODEL privilege
--         and READ on MODEL_DIR)
-- ============================================================

SET SERVEROUTPUT ON

DECLARE
    -- >>> EDIT THESE VALUES <<<
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

    -- Load the ONNX model from MODEL_DIR into the database
    DBMS_OUTPUT.PUT_LINE('Loading ONNX model into database...');
    DBMS_VECTOR.LOAD_ONNX_MODEL(
        directory  => 'MODEL_DIR',
        file_name  => v_onnx_file,
        model_name => v_model_name
    );
    DBMS_OUTPUT.PUT_LINE('Model loaded successfully: ' || v_model_name);
END;
/

-- Verify model is loaded
SELECT model_name, mining_function, algorithm FROM user_mining_models WHERE model_name = 'DEMO_MODEL';

```

**What this does:**

1. Drops any existing model with the same name so the block is safe to re-run.
2. Uses `DBMS_VECTOR.LOAD_ONNX_MODEL` to load the model directly from the `MODEL_DIR` directory (which points at `/opt/oracle/models` inside the container) into the database's model repository.

Because you have filesystem access, there is no download-into-the-database step. The file is already where the database can read it.

```sql
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
-- 10. Create SQL/PGQ Property Graph
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
-- 11. Create Vector Chunk Views
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

## Troubleshooting

**ORA-29532 / "directory not found" or "file not found"** -- The `MODEL_DIR` directory object doesn't point at the right path, the file wasn't copied into the container, or the PRISM user lacks READ on the directory. Confirm the file exists inside the container with `docker exec <container_name> ls -l /opt/oracle/models`, and re-check Step 3.

**ORA-13606: Error from Python** -- You're trying to load a raw Hugging Face model that hasn't been augmented with the required pre/post-processing steps. Use Oracle's pre-built augmented model from the download link in Step 1.

**ORA-54426: Tensor "input_ids" contains 2 batch dimensions** -- Same issue as above. The model needs to be augmented using OML4Py before loading. Use the pre-built version to avoid this.
