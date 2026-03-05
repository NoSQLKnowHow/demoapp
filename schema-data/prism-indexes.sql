-- ============================================================================
-- PRISM: Post-Ingestion Index Script
-- ============================================================================
-- Run as: PRISM user
-- Run after: prism-seed.sql/prism-seed.py AND prism-ingest.py
-- Purpose: Creates the HNSW vector index on document_chunks after data
--          has been loaded and vectorized.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Vector Index (HNSW)
-- ----------------------------------------------------------------------------

CREATE VECTOR INDEX idx_chunk_embedding
    ON document_chunks(embedding)
    ORGANIZATION INMEMORY NEIGHBOR GRAPH
    DISTANCE COSINE
    WITH TARGET ACCURACY 95;

-- ----------------------------------------------------------------------------
-- 2. Verification
-- ----------------------------------------------------------------------------

-- Confirm vector index exists
SELECT index_name, index_type FROM user_indexes WHERE index_name = 'IDX_CHUNK_EMBEDDING';

-- Confirm chunk count
SELECT source_table, COUNT(*) AS chunk_count FROM document_chunks GROUP BY source_table;

PROMPT
PROMPT ============================================================================
PROMPT  Vector index created successfully.
PROMPT  Prism is ready to use.
PROMPT ============================================================================
PROMPT
