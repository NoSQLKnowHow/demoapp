-- ============================================================================
-- RAG to Agents Lab: Reset demo state between runs
-- ============================================================================
-- Run as: PRISM user
--
-- Example:
--   sqlplus prism/<password>@localhost:1521/FREEPDB1 @docs/rag_to_agents_reset.sql
--
-- Purpose:
--   The agent's remember(...) tool inserts a row into AGENT_MEMORY every
--   turn. Across re-runs of the notebook, those notes accumulate and make
--   recall() / recall_similar() return more (and eventually noisier) data
--   than the first run saw. This script clears AGENT_MEMORY so each lab
--   run starts from a known-empty memory store.
--
--   Everything else the notebook uses (assets, districts, logs, reports,
--   findings, graph edges, DOCUMENT_CHUNKS with embeddings, vector indexes,
--   the ONNX DEMO_MODEL) is populated by the prep pipeline and does NOT
--   need to be reset between runs. This script deliberately does not touch
--   those.
--
-- Short-term (thread) memory:
--   The LangGraph MemorySaver checkpointer lives in Python process memory.
--   To wipe it too, re-run cell 5.4 of the notebook — that recreates the
--   checkpointer and recompiles the graph.
--
-- Idempotent: safe to run when AGENT_MEMORY is already empty.
-- ============================================================================

SET SERVEROUTPUT ON
SET VERIFY OFF
SET FEEDBACK OFF

PROMPT
PROMPT ============================================================================
PROMPT  RAG to Agents Lab: Reset demo state
PROMPT ============================================================================

DECLARE
    v_before  NUMBER := 0;
    v_exists  NUMBER := 0;
BEGIN
    SELECT COUNT(*) INTO v_exists FROM user_tables WHERE table_name = 'AGENT_MEMORY';
    IF v_exists = 0 THEN
        DBMS_OUTPUT.PUT_LINE('AGENT_MEMORY does not exist. Run @docs/rag_to_agents_prep.sql first.');
        RETURN;
    END IF;

    SELECT COUNT(*) INTO v_before FROM agent_memory;
    DBMS_OUTPUT.PUT_LINE('AGENT_MEMORY rows before reset: ' || v_before);

    -- Truncate is faster than DELETE for larger accumulations, and resets
    -- the identity sequence so the next memory_id starts at 1 again.
    EXECUTE IMMEDIATE 'TRUNCATE TABLE agent_memory';

    DBMS_OUTPUT.PUT_LINE('AGENT_MEMORY truncated. Identity sequence reset.');
END;
/

PROMPT
PROMPT --- Verification ---
SELECT COUNT(*) AS rows_after_reset FROM agent_memory;

PROMPT
PROMPT ============================================================================
PROMPT  rag_to_agents_reset: OK
PROMPT ============================================================================
PROMPT  Next: re-run cell 5.4 of the notebook to also wipe short-term (thread)
PROMPT  memory, then re-run Sections 5.8 onward.
PROMPT ============================================================================

SET FEEDBACK ON
