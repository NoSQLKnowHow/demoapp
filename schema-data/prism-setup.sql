-- ============================================================================
-- PRISM: Database Setup Script
-- ============================================================================
-- Run as: SYS AS SYSDBA (Oracle Free Docker) or ADMIN (on ADB)
-- Purpose: Creates the PRISM application user, schema objects, ONNX model,
--          JSON Duality View, and SQL/PGQ property graph.
--
-- Instructions: Edit the DEFINE values below before running.
--               For ADB: set pdb_name to your ADB service name,
--                        set tablespace to DATA.
--               For Oracle Free Docker: defaults below should work.
-- ============================================================================

-- >>> EDIT THESE VALUES BEFORE RUNNING <<<
DEFINE prism_password = CHANGE_ME
DEFINE db_service     = localhost:1521/FREEPDB1
DEFINE pdb_name       = FREEPDB1
DEFINE tablespace     = USERS -- for local
-- DEFINE tablespace = DATA -- for ADB

SET VERIFY OFF

PROMPT
PROMPT ============================================================================
PROMPT  PRISM: Database Setup
PROMPT ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Switch to PDB and Create Application User
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [1/10] Switching to PDB &pdb_name and creating PRISM user...

ALTER SESSION SET CONTAINER = &pdb_name;

-- Drop existing user if re-running (comment out for first-time setup)
DROP USER prism CASCADE;

CREATE USER prism IDENTIFIED BY "&prism_password"
    DEFAULT TABLESPACE &tablespace
    TEMPORARY TABLESPACE TEMP;

ALTER USER prism QUOTA UNLIMITED ON &tablespace;

PROMPT         User PRISM created.

-- ----------------------------------------------------------------------------
-- 2. Grant Privileges
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [2/10] Granting privileges...

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

-- Network access for ONNX model loading (if loading from URL)
-- GRANT EXECUTE ON DBMS_NETWORK_ACL_ADMIN TO prism;

PROMPT         Privileges granted.

-- ----------------------------------------------------------------------------
-- 3. Connect as PRISM User
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [3/10] Connecting as PRISM user...

CONNECT prism/"&prism_password"@"&db_service"

PROMPT         Connected as PRISM.

-- ----------------------------------------------------------------------------
-- 4. Create Canonical Tables
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [4/10] Creating canonical tables (DISTRICTS, INFRASTRUCTURE_ASSETS)...

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
PROMPT [5/10] Creating JSON collection table (OPERATIONAL_PROCEDURES)...

CREATE JSON COLLECTION TABLE operational_procedures;

PROMPT         Table OPERATIONAL_PROCEDURES created.

-- ----------------------------------------------------------------------------
-- 6. Create Remaining Canonical Tables
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [6/10] Creating remaining tables...

CREATE TABLE maintenance_logs (
    log_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_id     NUMBER NOT NULL REFERENCES infrastructure_assets(asset_id),
    log_date     DATE DEFAULT SYSDATE,
    severity     VARCHAR2(20),
    narrative    CLOB NOT NULL
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
PROMPT [7/10] Creating standard indexes...

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
PROMPT [8/10] ONNX Embedding Model
PROMPT         NOTE: Model loading is environment-specific. Uncomment one of
PROMPT         the options below or load the model manually.

-- Note: The DEMO_MODEL is loaded from the Oracle-provided ONNX model
-- repository. This step requires network access from the database.
-- On ADB, the model may already be available. Adjust the model loading
-- approach based on your environment.

-- Option A: Load from OML4Py (if available)
-- This is the simplest approach on ADB.
-- Run from a Python/OML4Py session:
--   import oml
--   oml.connect(user='prism', password='...', dsn='...')
--   from oml.utils import EmbeddingModel, EmbeddingModelConfig
--   em = EmbeddingModel(model_name='DEMO_MODEL')
--   em.export2db(model_name='DEMO_MODEL', overwrite=True)

-- Option B: Load ONNX model from object storage or file
-- BEGIN
--     DBMS_VECTOR.LOAD_ONNX_MODEL(
--         directory  => 'MODEL_DIR',
--         file_name  => 'all-MiniLM-L6-v2.onnx',
--         model_name => 'DEMO_MODEL',
--         metadata   => JSON('{"function":"embedding","embeddingOutput":"embedding","input":{"input":["DATA"]}}')
--     );
-- END;
-- /

-- Verify model is loaded
-- SELECT model_name, mining_function, algorithm FROM user_mining_models WHERE model_name = 'DEMO_MODEL';

PROMPT         Skipped (manual step). See comments in script.

-- ----------------------------------------------------------------------------
-- 9. Create JSON Duality View
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [9/10] Creating JSON Duality View (INSPECTION_REPORT_DV)...

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
PROMPT [10/10] Creating SQL/PGQ property graph (CITYPULSE_GRAPH)...

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
-- Vector Index (deferred)
-- ----------------------------------------------------------------------------
-- Note: The vector index is created AFTER seed data and vector ingestion
-- are complete. Creating the index on an empty table is valid but the index
-- will need to be rebuilt after bulk loading. For best performance, run
-- prism-seed.py and prism-ingest.py first, then run prism-indexes.sql.
-- ----------------------------------------------------------------------------

-- CREATE VECTOR INDEX idx_chunk_embedding
--     ON document_chunks(embedding)
--     ORGANIZATION INMEMORY NEIGHBOR GRAPH
--     DISTANCE COSINE
--     WITH TARGET ACCURACY 95;

-- ----------------------------------------------------------------------------
-- Verification
-- ----------------------------------------------------------------------------

PROMPT
PROMPT --- Verification ---
PROMPT
PROMPT Tables created:

SELECT table_name FROM user_tables ORDER BY table_name;

PROMPT
PROMPT Views created:

SELECT view_name FROM user_views WHERE view_name = 'INSPECTION_REPORT_DV';

PROMPT
PROMPT Property graphs created:

SELECT graph_name FROM user_property_graphs WHERE graph_name = 'CITYPULSE_GRAPH';

PROMPT
PROMPT Indexes created:

SELECT index_name, table_name FROM user_indexes ORDER BY table_name, index_name;

PROMPT
PROMPT ============================================================================
PROMPT  Prism schema setup complete.
PROMPT
PROMPT  Next steps:
PROMPT    1. Load the ONNX embedding model (see Section 8 above)
PROMPT    2. Run: python prism-seed.py     (load sample data)
PROMPT    3. Run: python prism-ingest.py   (vectorize content)
PROMPT    4. Run: @prism-indexes.sql       (create vector index)
PROMPT ============================================================================
PROMPT