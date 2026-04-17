# Lab 2: Generate In-Database Vector Embeddings

## Introduction
You will confirm the ONNX embedding model is available inside Oracle AI Database 26ai, generate example embeddings, and execute the full pipeline that inserts a new maintenance log, chunks it, and stores the resulting vectors. The lab finishes by creating an HNSW vector index over the populated chunks table.

### Objectives
- Verify that the `DEMO_MODEL` ONNX embedding model is deployed and accessible.
- Produce a sample embedding to inspect dimensionality and output format.
- Insert, chunk, and vectorize a new maintenance log inside the database.
- Create and validate an HNSW vector index for fast similarity search.

Estimated Time: 15 minutes

## Task 1: Verify the ONNX Embedding Model
1. Query `ALL_MINING_MODELS` to confirm that `DEMO_MODEL` is present and ready to use:

    ```python
    cursor.execute("""
        SELECT model_name, mining_function, algorithm, creation_date
        FROM all_mining_models
        WHERE model_name = :model_name
    """, {"model_name": ONNX_MODEL})

    result = cursor.fetchone()
    if result:
        show_table(['Model Name', 'Mining Function', 'Algorithm', 'Created'], [result])
    else:
        print(f"WARNING: Model {ONNX_MODEL} not found. Check that it has been loaded.")
    ```

## Task 2: Generate a Sample Embedding
1. Execute `VECTOR_EMBEDDING` against a short text phrase and inspect the dimensionality:

    ```python
    cursor.execute(f"""
        SELECT VECTOR_EMBEDDING({ONNX_MODEL} USING
                   'safety incident at pump station' AS data) AS embedding
        FROM DUAL
    """)
    embedding = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT VECTOR_DIMS(
            VECTOR_EMBEDDING({ONNX_MODEL} USING
                'safety incident at pump station' AS data)
        ) AS dimensions
        FROM DUAL
    """)
    dims = cursor.fetchone()[0]

    print(f"Total dimensions: {dims}")
    print("\nFirst 200 characters of the vector:")
    print(str(embedding)[:200], "...")
    ```

## Task 3: Insert, Chunk, and Embed a New Maintenance Log
1. Insert a Harbor Bridge maintenance record while cleaning up re-runs, then chunk and embed the narrative:

    ```python
    cursor.execute("SELECT asset_id FROM infrastructure_assets WHERE name = 'Harbor Bridge'")
    harbor_bridge_id = cursor.fetchone()[0]

    narrative = (
        "Detected unusual vibration patterns on the north support cable during "
        "routine sensor sweep. Frequency analysis suggests possible fatigue stress "
        "at the cable anchor point near the western abutment. Corrosion visible on "
        "three secondary cable clamps. Recommending detailed structural inspection "
        "within 48 hours and temporary load restriction to single-lane traffic."
    )

    cursor.execute("""
        DELETE FROM document_chunks
        WHERE source_table = 'maintenance_logs'
          AND source_id IN (
              SELECT log_id FROM maintenance_logs
              WHERE narrative LIKE '%north support cable%'
                AND asset_id = :asset_id
          )
    """, {'asset_id': harbor_bridge_id})
    chunks_cleaned = cursor.rowcount

    cursor.execute("""
        DELETE FROM maintenance_logs
        WHERE narrative LIKE '%north support cable%'
          AND asset_id = :asset_id
    """, {'asset_id': harbor_bridge_id})
    logs_cleaned = cursor.rowcount

    if logs_cleaned > 0:
        print(f"Cleaned up {logs_cleaned} previous log(s) and {chunks_cleaned} chunk(s) from prior runs.")

    log_id_var = cursor.var(int)
    cursor.execute("""
        INSERT INTO maintenance_logs (asset_id, log_date, severity, narrative)
        VALUES (:asset_id, SYSDATE, :severity, :narrative)
        RETURNING log_id INTO :log_id
    """, {
        'asset_id': harbor_bridge_id,
        'severity': 'warning',
        'narrative': narrative,
        'log_id': log_id_var
    })
    new_log_id = log_id_var.getvalue()[0]
    print(f"Step 1 complete: Inserted maintenance log with log_id = {new_log_id}")

    chunk_params = json.dumps({
        "max": 1000, "overlap": 100, "split": "sentence", "normalize": "all"
    })

    cursor.execute("""
        SELECT et.column_value
        FROM TABLE(
            DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS(:input_text, JSON(:chunk_params))
        ) et
    """, {'input_text': narrative, 'chunk_params': chunk_params})
    chunks_raw = cursor.fetchall()
    print(f"Step 2 complete: Created {len(chunks_raw)} chunk(s)")

    for idx, (chunk_value,) in enumerate(chunks_raw, start=1):
        if isinstance(chunk_value, str):
            try:
                chunk_json = json.loads(chunk_value)
                chunk_text = chunk_json.get("chunk_data", chunk_value)
            except json.JSONDecodeError:
                chunk_text = chunk_value
        else:
            chunk_text = str(chunk_value)

        cursor.execute(f"""
            INSERT INTO document_chunks
                (source_table, source_id, chunk_seq, chunk_text, embedding)
            VALUES (
                :source_table, :source_id, :chunk_seq, :chunk_text,
                VECTOR_EMBEDDING({ONNX_MODEL} USING :chunk_text AS data)
            )
        """, {
            'source_table': 'maintenance_logs',
            'source_id': new_log_id,
            'chunk_seq': idx,
            'chunk_text': chunk_text
        })

    conn.commit()
    print(f"Step 3 complete: Embedded and stored {len(chunks_raw)} chunk(s) in DOCUMENT_CHUNKS.")
    ```
2. Verify the chunks exist and confirm their embedding dimensionality:

    ```python
    cursor.execute("""
        SELECT dc.chunk_id,
               dc.chunk_seq,
               SUBSTR(dc.chunk_text, 1, 100) AS chunk_preview,
               VECTOR_DIMS(dc.embedding)     AS dimensions
        FROM document_chunks dc
        WHERE dc.source_table = 'maintenance_logs'
          AND dc.source_id = :log_id
        ORDER BY dc.chunk_seq
    """, {'log_id': new_log_id})

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())
    ```

## Task 4: Create an HNSW Vector Index
1. Drop any previous index and create a new HNSW vector index over `DOCUMENT_CHUNKS`:

    ```python
    cursor.execute("""
        SELECT index_name FROM user_indexes
        WHERE index_name = 'IDX_CHUNK_EMBEDDING'
    """)
    if cursor.fetchone():
        cursor.execute("DROP INDEX idx_chunk_embedding")
        print("Existing index dropped.")

    cursor.execute("""
        CREATE VECTOR INDEX idx_chunk_embedding
            ON document_chunks(embedding)
            ORGANIZATION INMEMORY NEIGHBOR GRAPH
            DISTANCE COSINE
            WITH TARGET ACCURACY 95
    """)
    print("Vector index idx_chunk_embedding created.")
    ```
2. Confirm the index status before proceeding to the next lab:

    ```python
    cursor.execute("""
        SELECT index_name, index_type, status
        FROM user_indexes
        WHERE index_name = 'IDX_CHUNK_EMBEDDING'
    """)

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())
    ```

## Acknowledgements
- Vector pipeline derived from docs/data_fundamentals_lab.ipynb.
