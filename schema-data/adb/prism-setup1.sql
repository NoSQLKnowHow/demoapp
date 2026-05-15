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
DEFINE tablespace = DATA -- for ADB

SET VERIFY OFF

PROMPT
PROMPT ============================================================================
PROMPT  PRISM: Database Setup
PROMPT ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Switch to PDB and Create Application User
-- ----------------------------------------------------------------------------

PROMPT
PROMPT [1/12] Switching to PDB &pdb_name and creating PRISM user...

ALTER SESSION SET CONTAINER = &pdb_name;

-- Drop existing user if re-running (comment out for first-time setup)
DROP USER IF EXISTS prism CASCADE;

CREATE USER prism IDENTIFIED BY "&prism_password";
    --DEFAULT TABLESPACE &tablespace
    --TEMPORARY TABLESPACE TEMP;

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

CREATE OR REPLACE PUBLIC SYNONYM demo_model FOR admin.demo_model;

PROMPT         Privileges granted.