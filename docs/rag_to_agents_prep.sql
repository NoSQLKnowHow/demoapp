-- ============================================================================
-- RAG to Agents Lab: Prep Script
-- ============================================================================
-- Run as: PRISM user (the same schema loaded by schema-data/prism-setup.sql)
--
-- Example:
--   sqlplus prism/<password>@localhost:1521/FREEPDB1 @docs/rag_to_agents_prep.sql
--
-- Purpose:
--   Creates notebook-specific database objects required by rag_to_agents_lab.ipynb:
--     - AGENT_MEMORY table (long-term memory surface for the agent),
--       including a VECTOR column and HNSW index so the agent can recall
--       prior notes by semantic similarity (slide 48: "reading from memory
--       is a retrieval problem")
--     - (optional) hybrid vector index for richer semantic + keyword search
--
-- Prerequisites (run these FIRST, in order):
--   1. @schema-data/prism-setup.sql         (schema, tables, views, graph)
--   2. Load DEMO_MODEL ONNX embedding model (see docs/load_onnx_model.md)
--   3. python schema-data/prism-seed.py     (sample data)
--   4. python schema-data/prism-ingest.py   (chunk + embed narratives)
--   5. @schema-data/prism-indexes.sql       (HNSW vector index)
--   6. @docs/rag_to_agents_prep.sql         (this script)
--
-- Idempotent: safe to re-run. Existing objects are dropped and recreated.
-- ============================================================================

SET SERVEROUTPUT ON
SET VERIFY OFF
SET FEEDBACK OFF

PROMPT
PROMPT ============================================================================
PROMPT  RAG to Agents Lab: Prep
PROMPT ============================================================================

-- ----------------------------------------------------------------------------
-- 1. AGENT_MEMORY table (with embedding column)
-- ----------------------------------------------------------------------------
-- Long-term, cross-session memory surface exposed to the agent via the
-- remember(asset_name, note), recall(asset_name), and
-- recall_similar(query, asset_name) tools. Bounded note length protects
-- against prompt-injection payloads blowing out storage. The VECTOR column
-- lets the agent do semantic recall across prior notes using the same
-- in-database DEMO_MODEL embedding used elsewhere in the lab.
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [1/3] Creating AGENT_MEMORY table...

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE agent_memory CASCADE CONSTRAINTS PURGE';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN RAISE; END IF;  -- ORA-00942: table does not exist
END;
/

CREATE TABLE agent_memory (
    memory_id  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    asset_name VARCHAR2(200)  NOT NULL,
    note       VARCHAR2(1000) NOT NULL,
    embedding  VECTOR,
    created_at TIMESTAMP DEFAULT SYSTIMESTAMP
);

CREATE INDEX idx_agent_memory_asset ON agent_memory(asset_name);
CREATE INDEX idx_agent_memory_created ON agent_memory(created_at DESC);

PROMPT         Table AGENT_MEMORY created.

-- ----------------------------------------------------------------------------
-- 1b. HNSW vector index on AGENT_MEMORY.embedding
-- ----------------------------------------------------------------------------
-- Creating the index on an empty table is valid; Oracle maintains it as
-- rows are inserted. The agent's remember(...) tool embeds each note with
-- VECTOR_EMBEDDING(DEMO_MODEL USING :note AS data) on write, and
-- recall_similar(...) uses this index to rank notes by cosine distance.
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [2/3] Creating HNSW vector index on AGENT_MEMORY.embedding...

CREATE VECTOR INDEX idx_agent_memory_embedding
    ON agent_memory(embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95;

PROMPT         Vector index IDX_AGENT_MEMORY_EMBEDDING created.

-- ----------------------------------------------------------------------------
-- 2. Hybrid vector index (optional)
-- ----------------------------------------------------------------------------
-- Best-effort: some Oracle AI Database 26ai environments do not have the
-- hybrid vector feature enabled, or it requires additional setup. If the
-- attempt fails, the notebook's search_incidents_semantic tool falls back to
-- vector-only search, so this is purely an enhancement.
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [3/3] Attempting hybrid vector index on DOCUMENT_CHUNKS...

DECLARE
    e_already_exists EXCEPTION;
    PRAGMA EXCEPTION_INIT (e_already_exists, -955);  -- ORA-00955: name already used
BEGIN
    -- Drop prior version if present (idempotent)
    BEGIN
        EXECUTE IMMEDIATE 'DROP INDEX idx_chunks_hybrid';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -1418 AND SQLCODE != -942 THEN NULL; END IF;
    END;

    EXECUTE IMMEDIATE q'[
        CREATE HYBRID VECTOR INDEX idx_chunks_hybrid
            ON document_chunks(chunk_text)
            PARAMETERS('MODEL DEMO_MODEL')
    ]';

    DBMS_OUTPUT.PUT_LINE('        Hybrid vector index IDX_CHUNKS_HYBRID created.');
EXCEPTION
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('        Skipped (not available in this environment): ' ||
                             SUBSTR(SQLERRM, 1, 180));
        DBMS_OUTPUT.PUT_LINE('        Notebook will fall back to vector-only search.');
END;
/

-- ----------------------------------------------------------------------------
-- Verification
-- ----------------------------------------------------------------------------

PROMPT
PROMPT --- Verification ---

COLUMN object_name FORMAT A35
COLUMN object_type FORMAT A15
SELECT object_name, object_type
FROM user_objects
WHERE object_name IN ('AGENT_MEMORY', 'IDX_AGENT_MEMORY_ASSET',
                      'IDX_AGENT_MEMORY_CREATED',
                      'IDX_AGENT_MEMORY_EMBEDDING',
                      'IDX_CHUNKS_HYBRID')
ORDER BY object_type, object_name;

PROMPT
PROMPT ============================================================================
PROMPT  rag_to_agents_prep: OK
PROMPT ============================================================================
PROMPT  Next step: open docs/rag_to_agents_lab.ipynb and run Section 0.
PROMPT ============================================================================

SET FEEDBACK ON
