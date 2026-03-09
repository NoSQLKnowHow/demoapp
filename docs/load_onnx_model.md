# Loading an ONNX Embedding Model into Oracle Autonomous Database

The challenge with ADB is that you don't have filesystem access to the database server, so you can't just drop a `.onnx` file into a directory like you can with Oracle Free Docker. Instead, you need to go through OCI Object Storage as an intermediary.

This guide covers the **recommended approach**: upload the model to Object Storage, pull it into ADB using `DBMS_CLOUD`, then load it with `DBMS_VECTOR`.

## Prerequisites

- An OCI tenancy with Object Storage access
- An Autonomous Database instance
- ADMIN access to the ADB instance (or a user with the required privileges)

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

## Step 2: Upload the Model to OCI Object Storage

### Option A: Using the OCI Console

1. Go to **Storage > Object Storage > Buckets** in the OCI Console.
2. Create a new bucket (or use an existing one), e.g., `prism-models`.
3. Click **Upload**, select the `all_MiniLM_L12_v2.onnx` file, and upload it.

### Option B: Using the OCI CLI

```bash
oci os object put \
    --bucket-name prism-models \
    --file all_MiniLM_L12_v2.onnx \
    --name all_MiniLM_L12_v2.onnx
```

---

## Step 3: Create a Pre-Authenticated Request (PAR)

A PAR gives ADB a URL it can use to download the file without needing OCI API credentials configured inside the database. This is the simplest approach.

### Using the OCI Console

1. Navigate to your bucket (`prism-models`).
2. Click the three-dot menu on the `all_MiniLM_L12_v2.onnx` object.
3. Select **Create Pre-Authenticated Request**.
4. Set:
   - **Name**: `prism-onnx-model`
   - **Pre-Authenticated Request Target**: **Object**
   - **Access Type**: **Permit object reads**
   - **Expiration**: Set a reasonable date (e.g., 7 days from now)
5. Click **Create Pre-Authenticated Request**.
6. **Copy the URL immediately** (it won't be shown again).

The URL will look something like:
```
https://objectstorage.us-ashburn-1.oraclecloud.com/p/AbCdEf.../n/your_namespace/b/prism-models/o/all_MiniLM_L12_v2.onnx
```

### Using the OCI CLI

```bash
oci os preauth-request create \
    --bucket-name prism-models \
    --name prism-onnx-model \
    --access-type ObjectRead \
    --object-name all_MiniLM_L12_v2.onnx \
    --time-expires "2026-03-15T00:00:00Z"
```

The output will include the `access-uri`. Combine it with the Object Storage base URL to get the full PAR URL.

---

## Step 4: Load the Model into ADB

Connect to your ADB instance as the ADMIN user (or as the PRISM user if it has the required grants) using SQL Developer, SQLcl, or SQL*Plus with a wallet connection.

Run the following PL/SQL block. Replace `<YOUR_PAR_URL>` with the full PAR URL from Step 3, and replace `DEMO_MODEL` with whatever model name you want to use in Prism.

```sql
-- ============================================================
-- Load ONNX Embedding Model into ADB via Object Storage PAR
-- ============================================================
-- Run as: ADMIN or a user with CREATE MINING MODEL privilege
-- ============================================================

SET SERVEROUTPUT ON

DECLARE
    -- >>> EDIT THESE VALUES <<<
    v_par_url    VARCHAR2(1000) := '<YOUR_PAR_URL>';
    v_model_name VARCHAR2(100)  := 'DEMO_MODEL';
    v_onnx_file  VARCHAR2(100)  := 'all_MiniLM_L12_v2.onnx';
BEGIN
    -- Drop existing model if re-running
    BEGIN
        DBMS_VECTOR.DROP_ONNX_MODEL(model_name => v_model_name, force => TRUE);
        DBMS_OUTPUT.PUT_LINE('Dropped existing model: ' || v_model_name);
    EXCEPTION
        WHEN OTHERS THEN NULL;
    END;

    -- Download the ONNX file from Object Storage into DATA_PUMP_DIR
    -- Using credential_name => NULL because PAR URLs don't need credentials
    DBMS_OUTPUT.PUT_LINE('Downloading model from Object Storage...');
    DBMS_CLOUD.GET_OBJECT(
        credential_name => NULL,
        directory_name  => 'DATA_PUMP_DIR',
        object_uri      => v_par_url
    );
    DBMS_OUTPUT.PUT_LINE('Download complete.');

    -- Load the ONNX model from DATA_PUMP_DIR into the database
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

**What this does:**

1. Uses `DBMS_CLOUD.GET_OBJECT` to download the ONNX file from Object Storage (via the PAR URL) into ADB's `DATA_PUMP_DIR` directory. This is a built-in directory that ADB users have access to. No need to create a custom directory.
2. Uses `DBMS_VECTOR.LOAD_ONNX_MODEL` to load the model from `DATA_PUMP_DIR` into the database's model repository.
3. Uses `credential_name => NULL` because PAR URLs already have authentication baked in. No need to create OCI credentials inside the database.

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

## Step 6: Grant Access to the PRISM User (if loaded as ADMIN)

If you loaded the model as ADMIN and the Prism application runs as the PRISM user, you need to grant access:

```sql
-- Run as ADMIN
GRANT SELECT ANY MINING MODEL TO prism;
-- Or more specifically:
-- GRANT EXECUTE ON MINING MODEL DEMO_MODEL TO prism;
```

Alternatively, if PRISM has `CREATE MINING MODEL` privilege (which `prism-setup.sql` grants), you can run the entire Step 4 block as the PRISM user directly, and the model will be owned by PRISM with no additional grants needed.

---

## Troubleshooting

**ORA-20401: Authorization failed for URI** -- Your PAR URL has expired or is invalid. Generate a new one from Step 3.

**ORA-20000: Missing credentials** -- You used a regular Object Storage URL instead of a PAR URL. Either create a PAR or set up OCI credentials using `DBMS_CLOUD.CREATE_CREDENTIAL`.

**ORA-13606: Error from Python** -- You're trying to load a raw Hugging Face model that hasn't been augmented with the required pre/post-processing steps. Use Oracle's pre-built augmented model from the download link in Step 1.

**ORA-54426: Tensor "input_ids" contains 2 batch dimensions** -- Same issue as above. The model needs to be augmented using OML4Py before loading. Use the pre-built version to avoid this.

---

## Alternative: Using OCI Credentials Instead of PAR

If you prefer not to use PAR URLs (e.g., for automation), you can create OCI credentials inside the database:

```sql
-- Run as ADMIN
BEGIN
    DBMS_CLOUD.CREATE_CREDENTIAL(
        credential_name => 'OCI_CRED',
        user_ocid       => 'ocid1.user.oc1..aaaa...',
        tenancy_ocid    => 'ocid1.tenancy.oc1..aaaa...',
        private_key     => '<your_api_private_key>',
        fingerprint     => 'xx:xx:xx:...'
    );
END;
/
```

Then use the credential in the download step:

```sql
DBMS_CLOUD.GET_OBJECT(
    credential_name => 'OCI_CRED',
    directory_name  => 'DATA_PUMP_DIR',
    object_uri      => 'https://objectstorage.<region>.oraclecloud.com/n/<namespace>/b/<bucket>/o/all_MiniLM_L12_v2.onnx'
);
```

This is better for repeatable deployments but requires managing API keys.

---

## For Reference: Oracle Free Docker (Much Simpler)

On Oracle Free Docker, you have filesystem access, so the process is straightforward:

```bash
# On your host machine, copy the model into the Docker container
docker cp all_MiniLM_L12_v2.onnx <container_name>:/opt/oracle/models/

# Inside the container (or from sqlplus)
sqlplus sys/<password>@localhost:1521/FREEPDB1 as sysdba

CREATE OR REPLACE DIRECTORY model_dir AS '/opt/oracle/models';
GRANT READ, WRITE ON DIRECTORY model_dir TO prism;
```

```sql
-- Run as PRISM user
BEGIN
    DBMS_VECTOR.LOAD_ONNX_MODEL(
        directory  => 'MODEL_DIR',
        file_name  => 'all_MiniLM_L12_v2.onnx',
        model_name => 'DEMO_MODEL'
    );
END;
/
```

No Object Storage, no credentials, no PAR URLs needed.
