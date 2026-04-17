# Workshop Plan: Data Fundamentals for AI Application Development

## Source Materials
- docs/data_fundamentals_lab.ipynb (hands-on notebook)
- docs/notebook-plan-data-fundamentals.md (author-provided plan)

## Target Audience
Application developers building AI-enabled apps on Oracle AI Database 26ai who need hands-on exposure to multimodel data, vector embeddings, and hybrid search.

## Environment Assumptions
- Oracle AI Database 26ai Free (container) LiveLabs sandbox
- Prism schema and associated objects pre-provisioned
- Browser-based SQL worksheet / terminal access

## Workshop Mode
- draft (structure and content without screenshots or QA artifacts)

## Lab Sequence
1. Introduction (overview, prerequisites, workshop flow)
2. Lab 1: Connect and Explore the Prism Dataset (configuration, connection, relational/JSON/graph exploration)
3. Lab 2: Generate In-Database Vector Embeddings (model verification, embedding generation, maintenance log pipeline)
4. Lab 3: Combine Relational, JSON, Graph, and Vector in One Query (unified SQL example, interpretation)
5. Lab 4: Optional Hybrid Vector Search (hybrid table, hybrid index, vector/text/hybrid queries, cleanup)

## Traceability Table
| Notebook Cells | Workshop Lab/Section |
|----------------|----------------------|
| 1-7 | Introduction + Lab 1 setup |
| 9-16 | Lab 1 tasks |
| 17-26 | Lab 2 core tasks |
| 28-38 | Lab 3 unified query |
| 44-62 | Lab 4 hybrid search |
| 63-64 | Introduction summary / acknowledgements |

## Outstanding Authoring Decisions
- No screenshots or FreeSQL embeds requested
- Hybrid search positioned as optional lab with estimated extra time
