# Data Fundamentals for AI Application Development

## Introduction
This workshop shows how Oracle AI Database 26ai keeps multimodel data, in-database AI, and hybrid search in one place. You will connect to a LiveLabs-provided container running the Prism smart city dataset, explore relational and JSON assets, build vector embeddings with an ONNX model, run a multimodel SQL query, and optionally create a hybrid vector search index.

### Objectives
- Understand the Prism dataset structure and the Oracle 26ai features it exercises.
- Configure a notebook or script environment that connects to the LiveLabs sandbox securely.
- Explore how Oracle SQL surfaces relational, JSON, property graph, and vector data without leaving the database.
- Generate embeddings inside the database and verify the supporting ONNX model.
- Run unified and hybrid search queries that combine semantic relevance with precise keywords.

Estimated Workshop Time: 45 minutes (plus 15 minutes for the optional hybrid search lab)

## Environment
- LiveLabs tenancy with Oracle AI Database 26ai Free (container) pre-provisioned.
- Prism schema, property graph, ONNX model `DEMO_MODEL`, and initial vector chunks already loaded.
- SQL worksheet or notebook runtime with network access to the database endpoint.

## Workshop Labs
1. Lab 1: Connect and Explore the Prism Dataset — set credentials, connect, and inspect relational, JSON, and graph structures.
2. Lab 2: Generate In-Database Vector Embeddings — confirm the ONNX model, create embeddings, and vectorize a new maintenance log.
3. Lab 3: Combine Relational, JSON, Graph, and Vector in One Query — issue a single SQL statement that unifies every data shape.
4. Lab 4 (Optional): Hybrid Vector Search — build a hybrid index and compare vector-only, text-only, and fused search results.

## Acknowledgements
- Kirk Kirkconnell, Oracle Developer Relations, for the original notebook and scenario design.
- Oracle LiveLabs team for environment provisioning guidance.
