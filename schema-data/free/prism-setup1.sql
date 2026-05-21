-- ============================================================================
-- PRISM: Database Setup Script (ADB)
-- ============================================================================
-- Run as: ADMIN (on ADB)
-- Purpose: Creates the PRISM application user, grants privileges, and
--          creates the public synonym for the DEMO_MODEL ONNX model.
--
-- Usage:   Invoked by shell_script.sh, which passes &dbpassword via DEFINE
--          before running this file. The shell script sources DBPASSWORD
--          from variable.sh (or ~/.env) and binds it to &dbpassword.
--
-- Note:    This is the ADB-specific setup. The Oracle Free Docker version
--          lives in ../free/prism-setup.sql and uses different defaults.
-- ============================================================================

DEFINE tablespace = USERS
DEFINE pdb_name   = FREEPDB1

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

CREATE USER prism IDENTIFIED BY "&dbpassword";
    DEFAULT TABLESPACE &tablespace
    TEMPORARY TABLESPACE TEMP;

ALTER USER prism QUOTA UNLIMITED ON &tablespace;

PROMPT         User PRISM created.

-- ----------------------------------------------------------------------------
-- 2. Grant Privileges
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

-- Network access for ONNX model loading (if loading from URL)
-- GRANT EXECUTE ON DBMS_NETWORK_ACL_ADMIN TO prism;

-- Grant access to the DEMO_MODEL ONNX embedding model (owned by ADMIN)
-- and create a public synonym so PRISM (and any other user) can reference
-- it by its bare name in VECTOR_EMBEDDING() calls.
GRANT ALTER ON MINING MODEL ADMIN.ALL_MINILM_L12_V2 TO PRISM;
GRANT SELECT ANY MINING MODEL TO PRISM;

PROMPT         Privileges granted.