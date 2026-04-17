# Lab 3: Combine Relational, JSON, Graph, and Vector in One Query

## Introduction
With the Prism data loaded and vector index created, this lab uses a single Oracle SQL environment to run semantic search, combine multimodel data in one statement, and traverse the property graph to understand incident impact.

### Objectives
- Execute semantic search queries over the unified chunks view.
- Blend relational, JSON, graph, and vector data in a consolidated SQL query.
- Produce both tabular and JSON outputs for downstream applications.
- Investigate critical incidents by traversing the property graph.

Estimated Time: 10 minutes

## Task 1: Run Semantic Search Across Content Types
1. Use the HNSW vector index to retrieve content related to Harbor Bridge structural issues:

    ```python
    cursor.execute(f"""
        SELECT source_table,
               source_date,
               SUBSTR(chunk_text, 1, 240) AS chunk_preview,
               asset_name,
               district_name,
               ROUND(
                   VECTOR_DISTANCE(embedding,
                       VECTOR_EMBEDDING({ONNX_MODEL} USING
                           'structural damage and corrosion on Harbor Bridge' AS data),
                       COSINE), 4
               ) AS distance
        FROM v_chunks_unified
        ORDER BY distance
        FETCH FIRST 5 ROWS ONLY
    """)

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())
    ```
2. Re-run semantic search with a different query to demonstrate breadth across the dataset:

    ```python
    cursor.execute(f"""
        SELECT source_table,
               source_date,
               SUBSTR(chunk_text, 1, 240) AS chunk_preview,
               asset_name,
               district_name,
               ROUND(
                   VECTOR_DISTANCE(embedding,
                       VECTOR_EMBEDDING({ONNX_MODEL} USING
                           'equipment failures near water treatment causing environmental risk' AS data),
                       COSINE), 4
               ) AS distance
        FROM v_chunks_unified
        ORDER BY distance
        FETCH FIRST 5 ROWS ONLY
    """)

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())
    ```
3. Interpret the cosine distance: values closer to 0 indicate stronger semantic similarity even when the text does not repeat the exact search terms.

## Task 2: Issue a Multimodel SQL Query
1. Run a single SQL statement that fuses vector hits, relational specs, and graph connectivity for Harbor Bridge:

    ```python
    cursor.execute(f"""
        WITH vector_hits AS (
            SELECT source_table, source_id, chunk_text,
                   asset_id, asset_name, district_name,
                   VECTOR_DISTANCE(embedding,
                       VECTOR_EMBEDDING({ONNX_MODEL} USING
                           'maintenance issues and structural condition of Harbor Bridge' AS data),
                       COSINE) AS distance
            FROM v_chunks_unified
            ORDER BY distance
            FETCH FIRST 5 ROWS ONLY
        ),
        connected AS (
            SELECT gt.to_asset, gt.connection_type
            FROM GRAPH_TABLE (citypulse_graph
                MATCH (a IS asset) -[c IS connected_to]- (b IS asset)
                WHERE a.name = 'Harbor Bridge'
                COLUMNS (
                    b.name            AS to_asset,
                    c.connection_type AS connection_type
                )
            ) gt
        )
        SELECT vh.source_table                           AS source,
               SUBSTR(vh.chunk_text, 1, 100)             AS content_preview,
               ROUND(vh.distance, 4)                     AS vector_dist,
               ia.name                                   AS asset,
               d.name                                    AS district,
               ia.specifications.spanLength_m.number()   AS span_m,
               ia.specifications.loadCapacity_t.number() AS capacity_t,
               ia.specifications.material.string()       AS material,
               (SELECT LISTAGG(c.to_asset || ' (' || c.connection_type || ')', ', ')
                       WITHIN GROUP (ORDER BY c.to_asset)
                FROM connected c)                        AS connected_assets
        FROM vector_hits vh
        JOIN infrastructure_assets ia ON ia.asset_id = vh.asset_id
        JOIN districts d ON d.district_id = ia.district_id
        ORDER BY vh.distance
    """)

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())
    ```
2. Present the same logic as a JSON payload for application consumption:

    ```python
    cursor.execute(f"""
        WITH vector_hits AS (
            SELECT source_table, source_id, chunk_text, asset_id,
                   asset_name, district_name,
                   VECTOR_DISTANCE(embedding,
                       VECTOR_EMBEDDING({ONNX_MODEL} USING
                           'maintenance issues and structural condition of Harbor Bridge' AS data),
                       COSINE) AS distance
            FROM v_chunks_unified
            ORDER BY distance
            FETCH FIRST 5 ROWS ONLY
        ),
        connected AS (
            SELECT gt.to_asset, gt.connection_type
            FROM GRAPH_TABLE (citypulse_graph
                MATCH (a IS asset) -[c IS connected_to]- (b IS asset)
                WHERE a.name = 'Harbor Bridge'
                COLUMNS (
                    b.name            AS to_asset,
                    c.connection_type AS connection_type
                )
            ) gt
        ),
        result_data AS (
            SELECT vh.source_table, vh.chunk_text, vh.distance,
                   ia.name AS asset_name, d.name AS district,
                   ia.specifications AS specs
            FROM vector_hits vh
            JOIN infrastructure_assets ia ON ia.asset_id = vh.asset_id
            JOIN districts d ON d.district_id = ia.district_id
        )
        SELECT JSON_OBJECT(
                'query' VALUE 'maintenance issues and structural condition of Harbor Bridge',
                'results' VALUE (
                    SELECT JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'source'   VALUE r.source_table,
                            'preview'  VALUE SUBSTR(r.chunk_text, 1, 150),
                            'distance' VALUE ROUND(r.distance, 4),
                            'asset'    VALUE r.asset_name,
                            'district' VALUE r.district,
                            'specs'    VALUE r.specs
                        ) ORDER BY r.distance
                    ) FROM result_data r
                ),
                'connected_assets' VALUE (
                    SELECT JSON_ARRAYAGG(
                        JSON_OBJECT(
                            'asset'           VALUE c.to_asset,
                            'connection_type'  VALUE c.connection_type
                        )
                    ) FROM connected c
                )
            RETURNING JSON
        ) AS json_output
        FROM DUAL
    """)

    result = cursor.fetchone()[0]
    print_json(result)
    ```

## Task 3: Investigate Critical Incidents with Graph Traversal
1. Traverse the property graph to identify assets connected to critical incidents and review their most recent inspection summaries:

    ```python
    cursor.execute(f"""
        WITH critical_assets AS (
            SELECT DISTINCT ia.name AS asset_name
            FROM maintenance_logs ml
            JOIN infrastructure_assets ia ON ia.asset_id = ml.asset_id
            WHERE ml.severity = 'critical'
        ),
        all_connections AS (
            SELECT *
            FROM GRAPH_TABLE (citypulse_graph
                MATCH (a IS asset) -[c IS connected_to]- (b IS asset)
                COLUMNS (
                    a.name            AS from_asset,
                    c.connection_type AS connection_type,
                    b.name            AS to_asset,
                    b.asset_type      AS to_type
                )
            )
        ),
        impacted AS (
            SELECT DISTINCT
                   ac.from_asset, ac.connection_type,
                   ac.to_asset, ac.to_type
            FROM all_connections ac
            JOIN critical_assets ca ON ca.asset_name = ac.from_asset
        ),
        latest_inspections AS (
            SELECT ir.asset_id, ir.overall_grade, ir.summary,
                   ROW_NUMBER() OVER (
                       PARTITION BY ir.asset_id ORDER BY ir.inspect_date DESC
                   ) AS rn
            FROM inspection_reports ir
        )
        SELECT imp.from_asset                               AS critical_asset,
               imp.connection_type                           AS relationship,
               imp.to_asset                                  AS connected_asset,
               imp.to_type                                   AS asset_type,
               ia.specifications.voltageRating_kv.number()   AS voltage_kv,
               ia.specifications.diameter_mm.number()        AS diameter_mm,
               ia.specifications.height_m.number()           AS height_m,
               li.overall_grade                              AS last_grade,
               SUBSTR(li.summary, 1, 100)                    AS inspection_summary
        FROM impacted imp
        JOIN infrastructure_assets ia ON ia.name = imp.to_asset
        LEFT JOIN latest_inspections li
            ON li.asset_id = ia.asset_id AND li.rn = 1
        ORDER BY imp.from_asset, imp.connection_type
    """)

    cols = [c[0] for c in cursor.description]
    rows = cursor.fetchall()
    if rows:
        show_table(cols, rows)
    else:
        print("No critical-severity maintenance logs found.")
        print("Tip: Change the severity filter to 'warning' and re-run.")
    ```
2. Visualize the relationships to highlight critical assets and their neighbors:

    ```python
    if rows:
        viz_edges = [(r[0], r[1], r[2]) for r in rows]

        viz_types = {}
        critical_names = set()
        for r in rows:
            critical_names.add(r[0])
            viz_types[r[2]] = r[3]
        for name in critical_names:
            cursor.execute("SELECT asset_type FROM infrastructure_assets WHERE name = :n", {'n': name})
            result = cursor.fetchone()
            if result:
                viz_types[name] = result[0]

        show_graph(viz_edges, node_types=viz_types,
                  highlight_nodes=critical_names,
                  title='Critical Incident Impact: Connected Assets')
    else:
        print('No graph to display (no critical-severity logs found).')
    ```

## Acknowledgements
- Unified SQL patterns sourced from docs/data_fundamentals_lab.ipynb.
