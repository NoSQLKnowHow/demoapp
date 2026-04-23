# Jupyter Notebook Plan: From RAG to Agents — Hands-On Companion Lab

**Companion notebook for the "Developer Tech Days - RAG to Agents" presentation**

**Target file:** `docs/rag_to_agents_lab.ipynb`
**Author:** Kirk Kirkconnell (Oracle Developer Relations)
**Created:** April 23, 2026

---

## Context

The "Developer Tech Days - RAG to Agents" presentation walks learners through a conceptual maturity ladder: chatbots → RAG → LLM-driven workflows → agentic AI, with supporting material on tools/skills/MCP, security, observability, and memory. The deck is architectural and has no code.

This companion notebook makes the ladder concrete with working code against the Prism (CityPulse) smart-city dataset. The chatbot tier (slides 7–8) is intentionally skipped.

The notebook reinforces the deck by progressively building one system:

1. **RAG** — grounded answers over Prism content using Oracle AI Database 26ai vector (+ hybrid) search with the in-database ONNX `DEMO_MODEL`.
2. **LLM-driven workflow** — a deterministic multi-step pipeline that uses RAG as a step, not as the whole system.
3. **Agent** — a LangGraph agent powered by Ollama that decides which tools to call, wrapping the same retrieval primitives plus the unified relational + JSON + graph + vector query, with short-term and long-term memory.

The marquee lab is a **bridge incident scenario**: given an asset (e.g., Harbor Bridge), the system retrieves recent incident data via a single Oracle query mixing relational filters, JSON `specifications`, SQL/PGQ graph traversal across `CITYPULSE_GRAPH`, and vector (or hybrid) search over `V_CHUNKS_UNIFIED`. The agent hands that context to Ollama and returns: **recommended course of action, reasoning, and next steps**.

### Database prerequisites (do NOT assume prior-lab state)

The notebook does **not** assume any prior notebook has been run. Before opening the notebook, the learner runs a documented prep sequence that is idempotent and safe to re-run:

1. `@schema-data/prism-setup.sql` — creates PRISM user, canonical tables, JSON collection, JSON Duality View, and `CITYPULSE_GRAPH`.
2. Load the `DEMO_MODEL` ONNX embedding model (per `docs/load_onnx_model.md`; environment-specific).
3. `python schema-data/prism-seed.py` — loads districts, assets, connections, procedures, logs, reports.
4. `python schema-data/prism-ingest.py` — chunks narratives and embeds them into `DOCUMENT_CHUNKS`.
5. `@schema-data/prism-indexes.sql` — creates the HNSW vector index.
6. **`@docs/rag_to_agents_prep.sql`** — creates `AGENT_MEMORY` and (optionally) a hybrid vector index for the agent's `search_incidents_semantic` tool. Idempotent.

All six steps are listed in Section 0 of the notebook with exact commands. Section 0 then runs a **readiness probe** that verifies every object the notebook depends on exists and has data; if any check fails, the cell prints the precise missing item and halts with a pointer to the relevant prep step.

### Python prerequisites

The workshop environment pre-installs the Python libraries this notebook needs; it does **not** run `pip install` at notebook start. The required packages and the minimum versions the notebook was authored against:

| Package | Minimum version | Used for |
|---------|-----------------|----------|
| `oracledb` | 2.1.0 | Oracle AI Database 26ai connectivity (thin mode) |
| `requests` | 2.25 | Raw HTTP RAG example in §1.7 (shows what a framework abstracts over) |
| `langchain` | 0.3 | Chains, prompt templates, output parsers (Sections 1–2) |
| `langchain-core` | 0.3 | Messages, `@tool` decorator, runnables |
| `langchain-ollama` | 0.2 | `ChatOllama` client for Ollama |
| `langgraph` | 0.2.50 | `StateGraph`, `ToolNode`, `MemorySaver` (Section 5) |
| `pydantic` | 2 | Structured-output validation for the workflow nodes |

If you run the notebook outside the workshop image, install these first with `pip install` (or equivalent) — the notebook itself contains no install cell.

### Ollama prerequisites

Ollama is assumed running (locally or via the workshop image) and reachable at `OLLAMA_BASE_URL`. The exact model tag is a configurable `OLLAMA_MODEL` variable, so the notebook works with whatever model is installed. Section 0 includes a reachability + model-pulled check.

---

## Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Notebook shape | New standalone `rag_to_agents_lab.ipynb` in `docs/` | Keeps data_fundamentals notebook focused on multi-model SQL; this one focuses on RAG→agent. |
| Prereqs | **No assumption of prior notebook state.** Learner runs the documented DB prep sequence plus `docs/rag_to_agents_prep.sql`. Section 0 validates readiness. | Notebook runs reliably regardless of what else has been done against the database. |
| Agent framework | **LangGraph** (StateGraph with tool-calling node + tool node) | Matches the "AI agent reasoning loop" slide 1-to-1. Current LangChain-recommended agent pattern. |
| LLM runtime | **Ollama** via `langchain-ollama.ChatOllama` | Local, private, free; matches workshop expectations. |
| Ollama model | Configurable `OLLAMA_MODEL` variable | Model tag unknown at authoring time; configurable cell lets the notebook run with `llama3.1`, `llama3.2`, `qwen2.5`, etc. |
| Embedding | In-database `DEMO_MODEL` via `VECTOR_EMBEDDING(... USING :text AS data)` | No external API, no data egress, consistent with Prism. |
| Retrieval | Vector search on `V_CHUNKS_UNIFIED`; hybrid vector+keyword search for the agent's richer retrieval tool | Demonstrates both patterns from the deck. |
| Marquee query | Single Oracle SQL statement combining relational filters, JSON `specifications` extraction, SQL/PGQ `GRAPH_TABLE` traversal, and vector search | Delivers on the "all four models in one query" requirement. |
| Scope add-ons | Tools/skills/MCP primer; security as inline callouts; observability via a per-step trace table; lightweight agent memory | User ranked security as secondary and observability as "shown and called out only." Memory is kept minimal (follow-up presentation covers it deeply). |
| Memory surface | LangGraph `MemorySaver` checkpointer (short-term/thread state) + a tiny Oracle `AGENT_MEMORY` table (cross-session notes) exposed as `remember` / `recall` tools | Demonstrates the two dominant flavors of memory without getting into embeddings-of-memories, summarization, or eviction policies. |
| Target runtime | ~60–75 minutes end-to-end | Matches a hands-on workshop slot. |

### Known constraints to handle

| Constraint | Impact | Workaround |
|------------|--------|------------|
| `GRAPH_TABLE` cannot correlate to outer query (no LATERAL) | Can't pass agent-resolved asset IDs directly into `GRAPH_TABLE WHERE` | Resolve asset in a CTE by `name`, JOIN graph results to the CTE. |
| `GRAPH_TABLE` KEY columns aren't exposed as PROPERTIES | `asset_id` isn't available inside GRAPH_TABLE COLUMNS | Match on `name` (unique property), JOIN back to `infrastructure_assets` for `asset_id`. |
| Ollama tool-calling quality varies by model | Weak models may ignore tool schemas | Configurable model + a tool-calling sanity check before the agent runs; document known-good models. |
| `VECTOR_DISTANCE` needs `FETCH FIRST N`; hybrid uses `DBMS_HYBRID_VECTOR.SEARCH` JSON spec | Same constraints the data_fundamentals lab already solved | Reuse the shape from the existing notebook's hybrid search cells. |

---

## Notebook structure

Eight sections mirror the deck's ladder. Each code cell is short and preceded by a markdown cell naming the slide/concept it reinforces.

### Section 0 — Welcome, prerequisites, and readiness probe (~7 min)

- **0.1** Title, objectives, slide map.
- **0.2** Database prerequisites (exact commands for the six prep steps).
- **0.3** Ollama prerequisites.
- **0.4** Configuration: `DB_USER`, `DB_PASSWORD`, `DB_DSN`, `ONNX_MODEL="DEMO_MODEL"`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (with options), `THREAD_ID`.
- **0.5** Imports and helpers: `show_table`, `print_json`, `_json_default`, new `show_trace(steps)` for per-step observability. (No pip install — deps are pre-provisioned; see the Python prerequisites table above.)
- **0.6** Connect to Oracle + version check.
- **0.7** Database readiness probe (comprehensive green/red summary; halts with actionable message on any miss).
- **0.8** Connect to Ollama + model smoke-test (distinguishes connection failure from missing model).

### Section 1 — RAG, grounded (~10 min) · reinforces slides 9–14

- **1.1** What RAG does; DEMO_MODEL embeds in-database.
- **1.2** Embed a query in-database and show `VECTOR_DIMS`.
- **1.3** The retriever, one function.
- **1.4** `retrieve_context(question, k=5, asset_filter=None)` against `V_CHUNKS_UNIFIED`.
- **1.5** Try it on a bearings/corrosion query.
- **1.6** Grounding the LLM.
- **1.7** RAG with **no framework** — `rag_answer_raw` using `requests.post(...)` to `/api/chat`. Shows that RAG fundamentally needs only retrieval (SQL) + prompt (f-string) + one HTTP call.
- **1.8** The same thing with LangChain — `rag_answer` using `ChatPromptTemplate | llm | StrOutputParser`. Short markdown in between: what the framework actually did, and when it starts paying off (answer: not much here, but a lot in §2).
- **1.9** A grounded question about Harbor Bridge (runs the LangChain version; raw version is already exercised in 1.7).
- **1.10** Where RAG runs out of road (slides 15–16).

### Section 2 — LLM-driven workflow (~10 min) · reinforces slides 18–22

- **2.1** Workflow anatomy (deck's 6-step pattern).
- **2.2** What we're building (4-step triage pipeline).
- **2.3** Classifier node (structured output).
- **2.4** RAG-retrieval node.
- **2.5** Drafter node (recommendation / rationale / next_steps).
- **2.6** Formatter node → markdown.
- **2.7** Run with a realistic bridge incident blurb + trace table.
- **2.8** Deterministic & auditable call-out.
- **2.9** Where workflows run out of road (slide 22).

### Section 3 — Tools, skills, MCP — brief primer (~5 min) · reinforces slides 29–35

- **3.1** What a tool is (typed function + docstring).
- **3.2** Six `@tool` definitions:
  1. `get_asset_overview(asset_name)` — relational + JSON.
  2. `get_recent_incidents(asset_name, days=180)` — maintenance logs + findings.
  3. `get_connected_assets(asset_name)` — SQL/PGQ graph neighbors.
  4. `search_incidents_semantic(query, asset_name=None, k=5)` — hybrid search with vector fallback.
  5. `remember(asset_name, note)` — write to `AGENT_MEMORY` (bounded length).
  6. `recall(asset_name)` — read recent notes.
- **3.3** Skills as SOPs: `BRIDGE_TRIAGE_SKILL` constant.
- **3.4** MCP in one paragraph (tools above could be MCP-exposed).
- **3.5** Security call-out (excessive agency + prompt injection).

### Section 4 — Marquee query (~10 min)

- **4.1** Why one query.
- **4.2** Anatomy (five CTEs: bridge, specs, neighbors, incidents, ranked).
- **4.3** The unified SQL (relational + JSON dot notation + SQL/PGQ GRAPH_TABLE + vector distance) returning asset/specs/graph_context/ranked_incidents as JSON.
- **4.4** Execute for Harbor Bridge + "bearing corrosion and cracking"; pretty-print.
- **4.5** Hybrid swap-in (optional).

### Section 5 — LangGraph agent with memory (~15 min) · reinforces slides 23–28, 35, 48

- **5.1** Reasoning loop → StateGraph.
- **5.2** Wrap the unified query as `get_bridge_incident_brief`.
- **5.3** Memory surfaces (checkpointer vs `AGENT_MEMORY`).
- **5.4** Bind all tools to the LLM.
- **5.5** State + nodes.
- **5.6** Compile with `MemorySaver` checkpointer.
- **5.7** System prompt (skill + prompt-injection defense + memory directives).
- **5.8** Run first turn (streaming).
- **5.9** Render answer + trace.
- **5.10** Follow-up turn demonstrating both memory surfaces.
- **5.11** Peek at `AGENT_MEMORY`.
- **5.12** Memory call-out (slide 48).
- **5.13** Observability call-out (slides 43–44).
- **5.14** Security recap.

### Section 6 — Try it yourself (~5 min)

Exercises: swap the asset, add a new tool, change `OLLAMA_MODEL`, tighten the system prompt, extend `AGENT_MEMORY` with a severity column.

### Section 7 — Cleanup and wrap-up (~2 min)

Close the connection; recap mapping sections to slides; pointers to LangGraph / Ollama / MCP / Oracle LiveLabs.

---

## Deliverables

1. **`docs/notebook-plan-rag-to-agents.md`** — this plan.
2. **`docs/rag_to_agents_prep.sql`** — idempotent prep script: creates `AGENT_MEMORY` (with drop-if-exists guard) and attempts a hybrid vector index; final `SELECT` prints `rag_to_agents_prep: OK`.
3. **`docs/rag_to_agents_lab.ipynb`** — the notebook, built to the cell-by-cell spec above.

---

## Verification plan

1. **DB prep.** Run, in order, against a fresh DB: `prism-setup.sql` → load ONNX model → `prism-seed.py` → `prism-ingest.py` → `prism-indexes.sql` → `rag_to_agents_prep.sql`. Confirm final script prints `rag_to_agents_prep: OK`.
2. **Ollama check.** `ollama list` shows the configured model; `curl $OLLAMA_BASE_URL/api/tags` responds.
3. **Readiness probe.** Run Section 0 in isolation; all green. Drop `AGENT_MEMORY`, re-run; confirm actionable failure. Re-create; green.
4. **Full run.** Restart & Run All completes without errors.
5. **Section 1 (RAG).** `rag_answer("What recent issues have been reported on Harbor Bridge?")` returns a coherent grounded answer.
6. **Section 2 (workflow).** 4-step markdown report emitted; `show_trace` shows 4 steps.
7. **Section 4 (marquee query).** All four JSON sections populated for `Harbor Bridge` + `"bearing corrosion and cracking"`.
8. **Section 5 (agent, first turn).** At least one tool call visible in stream; final `recommendation / rationale / next_steps` block; `remember(...)` called.
9. **Section 5 (memory).** Follow-up turn uses both the checkpointer and a `recall(...)`; memory peek shows at least one row.
10. **Model swap.** Changing `OLLAMA_MODEL` and re-running Section 5 still works.
11. **Security probe.** A prompt-injection user message does not cause destructive tool calls.
