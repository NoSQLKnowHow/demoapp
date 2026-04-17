# Lab 4: Optional Hybrid Vector Search

## Introduction
This optional lab builds a dedicated hybrid search table, configures a vectorizer preference, and demonstrates Oracle Database 26ai hybrid vector search queries that fuse semantic relevance with keyword precision.

### Objectives
- Stage a hybrid search demo table populated with maintenance and inspection content.
- Create a hybrid vector index that performs chunking and embedding automatically.
- Compare vector-only, text-only, union, and intersected search modes.
- Tune score weighting and clean up demo objects when finished.

Estimated Time: 15 minutes (optional)

## Task 1: Prepare the Hybrid Search Table
1. Clean up prior runs and stage the hybrid search dataset:

    ```python
    for stmt in [
        "DROP INDEX idx_hybrid_demo FORCE",
        "DROP TABLE hybrid_search_demo PURGE",
    ]:
        try:
            cursor.execute(stmt)
        except Exception:
            pass

    try:
        cursor.execute("""
            BEGIN DBMS_VECTOR_CHAIN.DROP_PREFERENCE('prism_hybrid_pref'); END;
        """)
    except Exception:
        pass

    print("Cleanup complete (safe for re-runs).")

    cursor.execute("""
        CREATE TABLE hybrid_search_demo (
            doc_id      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            asset_name  VARCHAR2(200),
            severity    VARCHAR2(20),
            source_type VARCHAR2(50),
            content     VARCHAR2(4000) NOT NULL
        )
    """)

    cursor.execute("""
        INSERT INTO hybrid_search_demo (asset_name, severity, source_type, content)
        SELECT ia.name, ml.severity, 'maintenance_log', ml.narrative
        FROM maintenance_logs ml
        JOIN infrastructure_assets ia ON ia.asset_id = ml.asset_id
    """)
    log_count = cursor.rowcount

    cursor.execute("""
        INSERT INTO hybrid_search_demo (asset_name, severity, source_type, content)
        SELECT ia.name, inf.severity, 'inspection_finding', inf.description
        FROM inspection_findings inf
        JOIN inspection_reports ir ON ir.report_id = inf.report_id
        JOIN infrastructure_assets ia ON ia.asset_id = ir.asset_id
        WHERE inf.description IS NOT NULL
    """)
    finding_count = cursor.rowcount

    conn.commit()
    print(f"Table created and populated: {log_count} maintenance logs + {finding_count} inspection findings")
    ```

## Task 2: Create the Hybrid Vector Index
1. Build a vectorizer preference and the hybrid vector index:

    ```python
    cursor.execute("""
        BEGIN
            DBMS_VECTOR_CHAIN.CREATE_PREFERENCE(
                'prism_hybrid_pref',
                DBMS_VECTOR_CHAIN.VECTORIZER,
                JSON('{"vector_idxtype": "hnsw",
                       "model":          "DEMO_MODEL",
                       "by":             "words",
                       "max":            100,
                       "overlap":         10,
                       "split":          "recursively"}')
            );
        END;
    """)
    print("Vectorizer preference created.")

    print("Creating hybrid vector index (this may take a moment)...")
    cursor.execute("""
        CREATE HYBRID VECTOR INDEX idx_hybrid_demo
            ON hybrid_search_demo(content)
            PARAMETERS('VECTORIZER prism_hybrid_pref')
    """)
    print("Hybrid vector index idx_hybrid_demo created.")
    print()
    print("Note: The hybrid index uses MAINTENANCE AUTO, so Oracle chunking and embedding continue in the background. The first search may take 30–60 seconds.")
    ```

## Task 3: Compare Vector and Text Search Modes
1. Run a vector-only search to retrieve the most semantically similar content:

    ```python
    cursor.execute("""
        SELECT DBMS_HYBRID_VECTOR.SEARCH(
                JSON('{
                    "hybrid_index_name" : "IDX_HYBRID_DEMO",
                    "search_scorer"     : "rsf",
                    "search_fusion"     : "VECTOR_ONLY",
                    "vector": {
                        "search_text"  : "root cause analysis of electrical failures",
                        "search_mode"  : "DOCUMENT",
                        "aggregator"   : "MAX",
                        "score_weight" : 1
                    },
                    "return": {
                        "values" : ["rowid", "vector_score", "chunk_text"],
                        "topN"   : 5
                    }
                }')
        ) FROM DUAL
    """)

    result = cursor.fetchone()[0]
    print("=== Vector-Only Search ===")
    print_json(result)
    ```
2. Switch to text-only mode to see pure keyword matches:

    ```python
    cursor.execute("""
        SELECT DBMS_HYBRID_VECTOR.SEARCH(
                JSON('{
                    "hybrid_index_name" : "IDX_HYBRID_DEMO",
                    "search_scorer"     : "rsf",
                    "search_fusion"     : "TEXT_ONLY",
                    "text": {
                        "contains"     : "Substation AND Gamma",
                        "score_weight" : 1
                    },
                    "return": {
                        "values" : ["rowid", "text_score", "chunk_text"],
                        "topN"   : 5
                    }
                }')
        ) FROM DUAL
    """)

    result = cursor.fetchone()[0]
    print("=== Text-Only Search ===")
    print_json(result)
    ```
3. Combine the two modes with UNION fusion so results can come from either semantic or keyword matches:

    ```python
    cursor.execute("""
        SELECT DBMS_HYBRID_VECTOR.SEARCH(
                JSON('{
                    "hybrid_index_name" : "IDX_HYBRID_DEMO",
                    "search_scorer"     : "rsf",
                    "search_fusion"     : "UNION",
                    "vector": {
                        "search_text"  : "root cause analysis of electrical failures",
                        "search_mode"  : "DOCUMENT",
                        "aggregator"   : "MAX",
                        "score_weight" : 1
                    },
                    "text": {
                        "contains"     : "Substation AND Gamma",
                        "score_weight" : 1
                    },
                    "return": {
                        "values" : ["rowid", "score", "vector_score", "text_score", "chunk_text"],
                        "topN"   : 5
                    }
                }')
        ) FROM DUAL
    """)

    result = cursor.fetchone()[0]
    result = rename_fused_score(result)
    print("=== Hybrid Search (UNION with RSF) ===")
    print_json(result)
    ```
4. Restrict the results to items that satisfy both semantic and keyword criteria with INTERSECT fusion:

    ```python
    cursor.execute("""
        SELECT DBMS_HYBRID_VECTOR.SEARCH(
                JSON('{
                    "hybrid_index_name" : "IDX_HYBRID_DEMO",
                    "search_scorer"     : "rsf",
                    "search_fusion"     : "INTERSECT",
                    "vector": {
                        "search_text"  : "root cause analysis of electrical failures",
                        "search_mode"  : "DOCUMENT",
                        "aggregator"   : "MAX",
                        "score_weight" : 1
                    },
                    "text": {
                        "contains"     : "Substation AND Gamma",
                        "score_weight" : 1
                    },
                    "return": {
                        "values" : ["rowid", "score", "vector_score", "text_score", "chunk_text"],
                        "topN"   : 5
                    }
                }')
        ) FROM DUAL
    """)

    result = cursor.fetchone()[0]
    result = rename_fused_score(result)
    print("=== Hybrid Search (INTERSECT with RSF) ===")
    print_json(result)
    ```

## Task 4: Tune Weighting and Interpret Results
1. Increase the keyword weighting to favor exact matches:

    ```python
    cursor.execute("""
        SELECT DBMS_HYBRID_VECTOR.SEARCH(
                JSON('{
                    "hybrid_index_name" : "IDX_HYBRID_DEMO",
                    "search_scorer"     : "rsf",
                    "search_fusion"     : "UNION",
                    "vector": {
                        "search_text"  : "root cause analysis of electrical failures",
                        "search_mode"  : "DOCUMENT",
                        "aggregator"   : "MAX",
                        "score_weight" : 1
                    },
                    "text": {
                        "contains"     : "Substation OR Gamma",
                        "score_weight" : 5
                    },
                    "return": {
                        "values" : ["rowid", "score", "vector_score", "text_score", "chunk_text"],
                        "topN"   : 5
                    }
                }')
        ) FROM DUAL
    """)

    result = cursor.fetchone()[0]
    result = rename_fused_score(result)
    print("=== Hybrid Search (UNION, text weight = 5) ===")
    print_json(result)
    ```
2. Discuss how `vector_score`, `text_score`, and the fused score change as weighting shifts, and align the mix with your application’s precision needs.

## Task 5: Clean Up Hybrid Search Objects
1. Drop the demo index, table, and vectorizer preference when you finish experimenting:

    ```python
    cursor.execute("DROP INDEX idx_hybrid_demo FORCE")
    cursor.execute("DROP TABLE hybrid_search_demo PURGE")
    cursor.execute("""
        BEGIN
            DBMS_VECTOR_CHAIN.DROP_PREFERENCE('prism_hybrid_pref');
        END;
    """)
    conn.commit()
    print("Hybrid search demo objects cleaned up.")
    ```

## Acknowledgements
- Hybrid search workflow adapted from docs/data_fundamentals_lab.ipynb.
