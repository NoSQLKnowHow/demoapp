-- ============================================================================
-- PRISM: Vector Search Test Queries
-- ============================================================================
-- Run as: PRISM user (connect to the PDB first)
-- Run after: prism-setup.sql, prism-seed.py, prism-ingest.py, prism-indexes.sql
-- ============================================================================

SET LINESIZE 200
SET PAGESIZE 50
COLUMN source_table FORMAT a25
COLUMN asset_name FORMAT a35
COLUMN district_name FORMAT a20
COLUMN severity FORMAT a10
COLUMN distance FORMAT 99.9999
COLUMN chunk_preview FORMAT a60

-- ============================================================================
-- Test 1: Basic semantic search across all content types
-- "Find anything related to corrosion near water"
-- ============================================================================

PROMPT
PROMPT === Test 1: Semantic search for "corrosion near water" ===
PROMPT

SELECT chunk_id, source_table, asset_name, severity,
       VECTOR_DISTANCE(embedding,
           VECTOR_EMBEDDING(DEMO_MODEL USING 'corrosion near water' AS data),
           COSINE) AS distance,
       SUBSTR(chunk_text, 1, 60) AS chunk_preview
FROM v_chunks_unified
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- ============================================================================
-- Test 2: Search only maintenance logs
-- "Find logs about electrical faults or power issues"
-- ============================================================================

PROMPT
PROMPT === Test 2: Maintenance logs search for "electrical fault power failure" ===
PROMPT

SELECT chunk_id, asset_name, severity, log_date,
       VECTOR_DISTANCE(embedding,
           VECTOR_EMBEDDING(DEMO_MODEL USING 'electrical fault power failure' AS data),
           COSINE) AS distance,
       SUBSTR(chunk_text, 1, 60) AS chunk_preview
FROM v_chunks_maintenance_logs
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- ============================================================================
-- Test 3: Hybrid search (semantic + relational filter)
-- "Find inspection findings about structural damage, but only in Harbor District"
-- ============================================================================

PROMPT
PROMPT === Test 3: Hybrid search - structural damage in Harbor District ===
PROMPT

SELECT chunk_id, source_table, asset_name, severity,
       VECTOR_DISTANCE(embedding,
           VECTOR_EMBEDDING(DEMO_MODEL USING 'structural damage crack deterioration' AS data),
           COSINE) AS distance,
       SUBSTR(chunk_text, 1, 60) AS chunk_preview
FROM v_chunks_unified
WHERE district_name = 'Harbor District'
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- ============================================================================
-- Test 4: Search inspection findings only
-- "Find findings related to safety hazards"
-- ============================================================================

PROMPT
PROMPT === Test 4: Inspection findings search for "safety hazard risk" ===
PROMPT

SELECT chunk_id, asset_name, category, severity,
       VECTOR_DISTANCE(embedding,
           VECTOR_EMBEDDING(DEMO_MODEL USING 'safety hazard risk' AS data),
           COSINE) AS distance,
       SUBSTR(chunk_text, 1, 60) AS chunk_preview
FROM v_chunks_inspection_findings
ORDER BY distance
FETCH FIRST 10 ROWS ONLY;

-- ============================================================================
-- Test 5: Compare semantic vs keyword search
-- Same query, two approaches
-- ============================================================================

PROMPT
PROMPT === Test 5a: Semantic search for "pump not working properly" ===
PROMPT

SELECT chunk_id, source_table, asset_name, severity,
       VECTOR_DISTANCE(embedding,
           VECTOR_EMBEDDING(DEMO_MODEL USING 'pump not working properly' AS data),
           COSINE) AS distance,
       SUBSTR(chunk_text, 1, 60) AS chunk_preview
FROM v_chunks_unified
ORDER BY distance
FETCH FIRST 5 ROWS ONLY;

PROMPT
PROMPT === Test 5b: Keyword search for "pump" (for comparison) ===
PROMPT

SELECT chunk_id, source_table, asset_name, severity,
       SUBSTR(chunk_text, 1, 60) AS chunk_preview
FROM v_chunks_unified
WHERE LOWER(chunk_text) LIKE '%pump%'
FETCH FIRST 5 ROWS ONLY;

PROMPT
PROMPT ============================================================================
PROMPT  Vector search tests complete.
PROMPT ============================================================================
PROMPT
