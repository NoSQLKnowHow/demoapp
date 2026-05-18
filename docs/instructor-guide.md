# Prism Workshop Instructor Runbook

This runbook supports the approved Prism workshop slide decks and the two hands-on notebooks in this repository. It is not a replacement for the approved decks.

Use the slide decks for narrative, positioning, architecture explanation, and customer-facing messaging. Use this guide for delivery logistics, notebook handoffs, checkpoints, troubleshooting, reset guidance, and cut lines.

## Approved delivery assets

| Workshop | Approved deck | Notebook | Primary purpose |
|---|---|---|---|
| Data Fundamentals for AI Application Development | `[Approved Data Fundamentals deck]` | `notebooks/data_fundamentals_lab.ipynb` | Show how Oracle Database can work with relational, JSON, graph, vector, and hybrid search patterns using one Prism dataset. |
| From RAG to Agents | `[Approved RAG to Agents deck]` | `notebooks/rag_to_agents_lab.ipynb` | Show the progression from grounded retrieval to deterministic workflows, tools, agents, and memory. |

Replace the deck placeholders above with the approved PowerPoint filenames or internal links when publishing this guide for instructors.

## How to use this guide

1. Deliver the approved deck content for the conceptual story.
2. Switch to the notebook when the deck reaches a hands-on section.
3. Use the checkpoint tables below to know when to pause, confirm learner progress, and decide whether to continue or skip optional content.
4. Use the troubleshooting section when learners hit common setup or runtime issues.
5. Use the cut lines when time is short.

## Assumptions for LiveLabs delivery

This guide assumes the workshop environment has already been provisioned before learners open the notebooks.

Expected environment:

- Oracle Database is available.
- The `PRISM` schema exists.
- Prism sample data is loaded.
- Required tables, views, property graph objects, indexes, and document chunks are present.
- The ONNX embedding model is loaded as `DEMO_MODEL`.
- Python dependencies required by the notebooks are installed.
- For the RAG-to-Agents notebook, Ollama and the selected local model are available in the LiveLabs environment.

The notebooks include readiness checks, but those checks are intended to confirm the environment, not teach learners how to build it from scratch.

## Suggested delivery formats

| Format | Suggested approach |
|---|---|
| 60-minute session | Use the Data Fundamentals notebook as the main hands-on lab. Skip or summarize the optional hybrid search section if needed. |
| 90-minute session | Run Data Fundamentals with selected optional exercises, then introduce the RAG-to-Agents deck and show key sections as a guided demo. |
| 2-hour session | Run Data Fundamentals and RAG-to-Agents as hands-on labs. Use cut lines only if the group falls behind. |
| Conference booth or short demo | Show the unified query and one agent response. Do not run every cell live. |

## Before the workshop

Use this checklist before learners join.

- Confirm the approved slide decks are the current reviewed versions.
- Confirm the LiveLabs event ID is for this event and works as it should
- Open both notebooks in the target LiveLabs environment using the event ID.
- Run the Data Fundamentals readiness check.
- Run the RAG-to-Agents Oracle readiness probe.
- Confirm Ollama responds in the RAG-to-Agents notebook.
- Confirm `DEMO_MODEL` can generate an embedding.
- Confirm the Prism sample assets include `Harbor Bridge` and `Substation Gamma`.
- Confirm the notebooks can connect as the intended workshop user.
- Confirm reset instructions are available if this environment has been used before.

## Notebook 1: Data Fundamentals delivery map

Recommended flow: slide deck introduction, notebook Sections 0-5, optional Section 6 only when time allows, then slide deck wrap-up.

| Notebook section | Approx. time | Instructor goal | Checkpoint / continue when |
|---|---:|---|---|
| Section 0: Configuration and readiness check | 3-5 min | Confirm the LiveLabs environment is ready before learners invest time in the lab. | The readiness check reports the required database objects, model, and sample data are available. |
| Section 1: Explore the Prism data model | 8-10 min | Show that the same Prism dataset supports relational, JSON, and graph access patterns. | Learners see asset rows, JSON fields, and connected asset relationships. |
| Section 2: Vector embeddings with an in-database ONNX model | 5-8 min | Show that embeddings can be generated inside Oracle Database with `DEMO_MODEL`. | Learners see a generated vector and inserted maintenance-log vectors. |
| Section 3: Create a Vector Index | 3-5 min | Explain why vector indexes matter for semantic search performance. | The vector index cell completes, or the instructor explains that an existing index is acceptable. |
| Section 4: Vector search | 5-8 min | Show semantic search over Prism maintenance and inspection context. | Learners see ranked chunks related to the natural-language query. |
| Section 5: The unified query | 8-12 min | Emphasize the main workshop proof point: relational, JSON, graph, and vector context can come together in one SQL statement. | Learners see a unified result for the target asset and related context. |
| Section 6: Optional Hybrid Vector Search | 10-15 min | Show how vector search and keyword search can be combined when time allows. | Learners see vector-only, text-only, and hybrid search results. |
| Section 7: Summary and next steps | 2-3 min | Connect the hands-on work back to the approved deck narrative. | Learners can explain why the database is acting as the shared AI application substrate. |

### Data Fundamentals talk-track reminders

- Keep the approved slide deck as the source of positioning.
- In the notebook, emphasize what each data shape adds: relational structure, JSON flexibility, graph relationships, vector similarity, and hybrid search precision.
- Treat the unified query as the main payoff.
- The optional exercises are for engagement and faster learners; they are not required for completion.

### Data Fundamentals common issues

| Symptom | Likely cause | Instructor action |
|---|---|---|
| Connection fails | Wrong connection settings or LiveLabs database not ready | Check the notebook configuration cell and confirm the workshop database service is available. |
| Readiness check reports missing tables | Schema setup did not complete | Re-run or verify the LiveLabs provisioning step that creates the Prism schema and loads data. |
| `DEMO_MODEL` is missing | ONNX model was not loaded | Use the workshop provisioning process to load the model before continuing. |
| Sample asset check fails | Data load is incomplete or wrong schema is active | Confirm the connection is using the intended `PRISM` schema and sample data set. |
| Vector index creation is slow | Expected database work, especially on shared environments | Let the cell finish when possible; if time is short, continue only if the later search cells work. |
| Hybrid search first query is slow | Oracle Text or hybrid index initialization overhead | Warn learners that the first hybrid query can take longer; skip the optional section if timing is tight. |

## Notebook 2: RAG-to-Agents delivery map

Recommended flow: use the approved RAG-to-Agents deck for the conceptual progression, then use the notebook to demonstrate the same progression hands-on.

| Notebook section | Approx. time | Instructor goal | Checkpoint / continue when |
|---|---:|---|---|
| Section 0: Welcome, prerequisites, and readiness probe | 5-8 min | Confirm Oracle and Ollama are ready. | Oracle readiness and local model checks pass. |
| Section 1: RAG, grounded | 10-12 min | Show retrieval, grounding, and a basic RAG answer using Prism context. | Learners see retrieved chunks and a grounded LLM response. |
| Section 2: LLM-driven workflow | 10-12 min | Contrast deterministic workflows with open-ended agents. | Learners see a structured incident workflow output. |
| Section 3: Tools and skills | 8-10 min | Show how tools expose controlled capabilities to the agent. | The tool definitions are available and understandable. |
| Section 4: The marquee unified query | 8-10 min | Connect the agent back to the strongest database proof point. | The unified incident context query returns usable context. |
| Section 5: Build the agent with LangGraph + Ollama | 20-25 min | Show the agent loop, tool use, short-term memory, and long-term memory. | The first turn completes and a follow-up uses memory. |
| Section 6: Try it yourself | 5-10 min | Let learners modify prompts or ask related incident questions. | Optional; skip when time is short. |
| Section 7: Cleanup and wrap-up | 2-3 min | Close resources and summarize what was built. | Learners understand how RAG, workflows, tools, agents, and memory relate. |

### RAG-to-Agents talk-track reminders

- Do not oversell the agent as magic. Emphasize controlled tool use, grounding, and observability.
- Use the workflow section to explain when deterministic orchestration is better than agent autonomy.
- Use the unified query section to reinforce that the database remains the system of record for agent context.
- Use the memory sections to distinguish conversation continuity from durable, searchable long-term memory.
- If model behavior varies, explain that this is normal for local LLM demos and that the notebook includes guardrails where needed.

### RAG-to-Agents common issues

| Symptom | Likely cause | Instructor action |
|---|---|---|
| Oracle readiness probe fails | Missing schema object, model, graph, or chunks | Stop and fix the environment before running the lab. The later sections depend on these objects. |
| Ollama check fails | Ollama is not running or the model is unavailable | Start Ollama in the LiveLabs environment or pull/verify the selected model. |
| Retrieval returns no useful chunks | Missing document chunks or embedding issue | Confirm `DOCUMENT_CHUNKS`, `V_CHUNKS_UNIFIED`, and `DEMO_MODEL` are available. |
| Agent does not call the expected tool | Local model variation | Re-run the cell, use the notebook guardrail, or explain the expected behavior using the trace. |
| Memory follow-up is weak | Prior turn did not store or retrieve the expected memory | Re-run the first turn and memory-inspection cells; confirm Oracle-backed memory tables are available. |
| Output format varies | Normal LLM variability | Focus learners on grounding, traceability, and tool use rather than exact wording. |

## Reset and rerun guidance

Use reset guidance when a LiveLabs environment has already been used or when a session needs to be repeated.

| Reset need | Recommended action |
|---|---|
| RAG-to-Agents state needs cleanup | Run `notebooks/rag_to_agents_reset.sql` using the intended workshop schema. |
| RAG-to-Agents setup needs to be prepared again | Run `notebooks/rag_to_agents_prep.sql` using the intended workshop schema. |
| Data Fundamentals notebook has been run before | Confirm whether inserted maintenance logs, generated vectors, and recreated indexes should be left in place or reset by the workshop provisioning process. |
| Full environment is inconsistent | Prefer rebuilding or refreshing the LiveLabs environment instead of manually patching many objects during a live session. |

Before a repeated delivery, run the readiness checks in both notebooks again.

## Suggested cut lines

Use these when the group is behind schedule.

| If short on time | Cut or compress | Keep |
|---|---|---|
| Data Fundamentals is running long | Skip optional exercises and Section 6 Hybrid Vector Search. | Keep Section 5 unified query. |
| Vector index creation is slow | Explain the purpose and move on if the index already exists or later searches work. | Keep at least one vector search result. |
| RAG-to-Agents is running long | Compress Section 2 workflow discussion and skip Section 6 Try it yourself. | Keep RAG retrieval, unified query, first agent turn, and memory follow-up. |
| Ollama/model behavior is inconsistent | Use the trace and expected checkpoint explanation instead of spending too long re-running. | Keep the database grounding and tool-use explanation. |

## Troubleshooting quick reference

When something fails during a live workshop, diagnose in this order:

1. Is the notebook connected to the intended database and schema?
2. Did the readiness check identify a missing object?
3. Is `DEMO_MODEL` present and able to generate an embedding?
4. Are the expected Prism sample rows present?
5. For RAG-to-Agents, is Ollama running and is the selected model available?
6. Is the issue a hard setup failure or normal LLM output variability?
7. Can the section be skipped without losing the main learning objective?

## Maintainer notes

- Keep approved slide decks authoritative for narrative and messaging.
- Keep this guide focused on delivery mechanics and recovery paths.
- When notebook section names change, update the delivery maps and checkpoint references here.
- When the LiveLabs environment changes, update the assumptions and troubleshooting sections.
- Avoid adding alternate product positioning here unless it has also been approved in the slide decks.
