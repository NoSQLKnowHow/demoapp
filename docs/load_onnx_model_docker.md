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

## Step 2: Copy the Model into the Container

From your host machine, copy the model into a directory inside the running container. Replace `<container_name>` with your container's name (find it with `docker ps`).

```bash
# Create the target directory inside the container (if it doesn't exist)
docker exec <container_name> mkdir -p /opt/oracle/models

# Copy the model into the container
docker cp all_MiniLM_L12_v2.onnx <container_name>:/opt/oracle/models/
```

Again, these instructions are for Docker, so translate to Podman if that's what you're using.

---

## Step 3: Create a Database Directory Pointing at the Model

Connect as `sysdba` and create an Oracle directory object that maps to the container path, then grant the PRISM user access to it.

```bash
sqlplus sys/<password>@localhost:1521/FREEPDB1 as sysdba
```

```sql
CREATE OR REPLACE DIRECTORY model_dir AS '/opt/oracle/models';
GRANT READ, WRITE ON DIRECTORY model_dir TO prism;
```

---

## Step 4: Load the Model

Connect as the PRISM user and load the model. Replace `DEMO_MODEL` with whatever model name you want to use in Prism.

```sql
-- ============================================================
-- Load ONNX Embedding Model into Oracle Database Free
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
```

**What this does:**

1. Drops any existing model with the same name so the block is safe to re-run.
2. Uses `DBMS_VECTOR.LOAD_ONNX_MODEL` to load the model directly from the `MODEL_DIR` directory (which points at `/opt/oracle/models` inside the container) into the database's model repository.

Because you have filesystem access, there is no download-into-the-database step. The file is already where the database can read it.

---

## Step 5: Verify the Model

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

## Step 6: Grant Access to Other Users (if loaded as a different user)

If you loaded the model as a user other than PRISM (e.g., as SYS) and the Prism application runs as the PRISM user, grant access:

```sql
GRANT SELECT ANY MINING MODEL TO prism;
-- Or more specifically:
-- GRANT EXECUTE ON MINING MODEL DEMO_MODEL TO prism;
```

If you loaded the model directly as the PRISM user (as in Step 4), the model is already owned by PRISM and no additional grant is needed.

---

## Troubleshooting

**ORA-29532 / "directory not found" or "file not found"** -- The `MODEL_DIR` directory object doesn't point at the right path, the file wasn't copied into the container, or the PRISM user lacks READ on the directory. Confirm the file exists inside the container with `docker exec <container_name> ls -l /opt/oracle/models`, and re-check Step 3.

**ORA-13606: Error from Python** -- You're trying to load a raw Hugging Face model that hasn't been augmented with the required pre/post-processing steps. Use Oracle's pre-built augmented model from the download link in Step 1.

**ORA-54426: Tensor "input_ids" contains 2 batch dimensions** -- Same issue as above. The model needs to be augmented using OML4Py before loading. Use the pre-built version to avoid this.
