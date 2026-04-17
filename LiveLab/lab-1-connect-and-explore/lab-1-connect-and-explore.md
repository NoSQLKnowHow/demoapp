# Lab 1: Connect and Explore the Prism Dataset

## Introduction
This lab prepares your Python notebook or script to talk to the LiveLabs Oracle AI Database 26ai instance and explores the Prism dataset across relational tables, JSON columns, and the property graph projection.

### Objectives
- Update notebook configuration values for your LiveLabs credentials.
- Install required Python packages and helper functions.
- Verify a successful database connection.
- Inspect Prism tables, relational rows, JSON attributes, and graph connectivity.

Estimated Time: 12 minutes

## Task 1: Configure the Notebook Environment
1. Open the LiveLabs notebook or your preferred Python environment.
2. Replace the placeholder values in the configuration cell with your LiveLabs credentials:

    ```python
    # === CONFIGURATION - UPDATE THESE VALUES ===
    DB_USER     = "your_username"
    DB_PASSWORD = "your_password"
    DB_DSN      = "localhost:1521/FREEPDB1"
    ONNX_MODEL  = "DEMO_MODEL"
    ```
3. Run the dependency cell to install packages and register helper functions:

    ```python
    # Install and import dependencies
    import oracledb
    import json
    from IPython.display import HTML, display
    from decimal import Decimal

    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    oracledb.defaults.fetch_lobs = False

    def show_table(headers, rows, max_width=80):
        """Display query results as a clean HTML table."""
        style_th = "border:1px solid #ddd; padding:6px 10px; background:#f4f4f4; text-align:left;"
        style_td = f"border:1px solid #ddd; padding:6px 10px; white-space:pre-wrap; max-width:{max_width}ch; word-wrap:break-word;"
        h = '<table style="border-collapse:collapse; font-size:13px;">'
        h += "<tr>" + "".join(f"<th style=\"{style_th}\">{c}</th>" for c in headers) + "</tr>"
        for row in rows:
            h += "<tr>" + "".join(f"<td style=\"{style_td}\">{v}</td>" for v in row) + "</tr>"
        h += "</table>"
        display(HTML(h))

    def _json_default(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return str(obj)

    def print_json(result):
        if isinstance(result, str):
            result = json.loads(result)
        print(json.dumps(result, indent=2, default=_json_default))

    def rename_fused_score(result):
        if isinstance(result, str):
            result = json.loads(result)
        for item in result:
            if 'score' in item:
                item['fused_score'] = item.pop('score')
        return result

    def show_graph(edges, node_types=None, highlight_nodes=None, title=None):
        G = nx.DiGraph()
        for src, rel, tgt in edges:
            G.add_edge(src, tgt, label=rel)

        palette = ['#4E79A7', '#F28E2B', '#59A14F', '#76B7B2', '#EDC948',
                   '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC', '#E15759']
        type_colors = {}
        if node_types:
            for i, t in enumerate(sorted(set(node_types.values()))):
                type_colors[t] = palette[i % len(palette)]

        node_colors = []
        for node in G.nodes():
            if highlight_nodes and node in highlight_nodes:
                node_colors.append('#E15759')
            elif node_types and node in node_types:
                node_colors.append(type_colors[node_types[node]])
            else:
                node_colors.append('#4E79A7')

        fig, ax = plt.subplots(figsize=(14, 9))
        pos = nx.spring_layout(G, k=2.5, seed=42)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors,
                               node_size=2200, alpha=0.9, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=7, font_weight='bold', ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color='#888888', arrows=True,
                               arrowsize=15, connectionstyle='arc3,rad=0.1', ax=ax)
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels,
                                     font_size=6, font_color='#444444', ax=ax)
        if title:
            ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        if node_types:
            handles = [mpatches.Patch(color=c, label=t) for t, c in type_colors.items()]
            if highlight_nodes:
                handles.append(mpatches.Patch(color='#E15759', label='critical incident'))
            ax.legend(handles=handles, loc='upper left', fontsize=8)
        ax.axis('off')
        plt.tight_layout()
        plt.show()

    print("Dependencies loaded.")
    ```

## Task 2: Connect to Oracle AI Database 26ai
1. Establish the database connection and confirm the version banner:

    ```python
    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
    cursor = conn.cursor()

    cursor.execute("SELECT banner FROM v$version WHERE ROWNUM = 1")
    banner = cursor.fetchone()[0]
    print(f"Connected successfully!\n{banner}")
    ```
2. Keep the connection open for the remainder of the workshop.

## Task 3: Explore the Prism Dataset
1. List the core Prism tables and their row counts to understand available data:

    ```python
    tables = [
        'DISTRICTS', 'INFRASTRUCTURE_ASSETS', 'OPERATIONAL_PROCEDURES',
        'MAINTENANCE_LOGS', 'INSPECTION_REPORTS', 'INSPECTION_FINDINGS',
        'ASSET_CONNECTIONS', 'DOCUMENT_CHUNKS'
    ]

    rows = []
    for t in tables:
        cursor.execute(f'SELECT COUNT(*) FROM {t}')
        count = cursor.fetchone()[0]
        rows.append((t, count))

    show_table(['Table', 'Row Count'], rows)
    ```
2. Review a relational join that pairs infrastructure assets with their districts:

    ```python
    cursor.execute("""
        SELECT a.asset_id, a.name, a.asset_type, a.status, d.name AS district
        FROM infrastructure_assets a
        JOIN districts d ON d.district_id = a.district_id
        ORDER BY a.asset_id
        FETCH FIRST 8 ROWS ONLY
    """)

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())
    ```
3. Use JSON dot notation to inspect technical specifications stored in JSON columns:

    ```python
    cursor.execute("""
        SELECT a.name,
               a.asset_type,
               a.specifications.spanLength_m.number()   AS span_length_m,
               a.specifications.loadCapacity_t.number() AS load_capacity_t,
               a.specifications.material.string()       AS material
        FROM infrastructure_assets a
        WHERE a.asset_type = 'bridge'
    """)

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())
    ```
4. Query the property graph projection to view asset connectivity and visualize the network:

    ```python
    cursor.execute("""
        SELECT *
        FROM GRAPH_TABLE (citypulse_graph
            MATCH (a IS asset) -[c IS connected_to]-> (b IS asset)
            COLUMNS (a.name AS from_asset,
                     c.connection_type AS relationship,
                     b.name AS to_asset)
        )
        FETCH FIRST 10 ROWS ONLY
    """)

    cols = [c[0] for c in cursor.description]
    show_table(cols, cursor.fetchall())

    cursor.execute("""
        SELECT *
        FROM GRAPH_TABLE (citypulse_graph
            MATCH (a IS asset) -[c IS connected_to]-> (b IS asset)
            COLUMNS (a.name AS from_asset, c.connection_type AS rel, b.name AS to_asset)
        )
    """)
    graph_edges = [(r[0], r[1], r[2]) for r in cursor.fetchall()]

    cursor.execute("SELECT name, asset_type FROM infrastructure_assets")
    asset_types = {r[0]: r[1] for r in cursor.fetchall()}

    show_graph(graph_edges, node_types=asset_types,
               title='Prism Infrastructure Connectivity Graph')
    ```

## Acknowledgements
- Queries and helper functions adapted from docs/data_fundamentals_lab.ipynb.
