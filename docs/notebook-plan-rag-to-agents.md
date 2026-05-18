# Jupyter Notebook Design: From RAG to Agents (Hands-On Companion Lab)

**Companion notebook for the "Developer Tech Days - RAG to Agents" presentation**

**Target file:** `notebooks/rag_to_agents_lab.ipynb`
**Author:** Kirk Kirkconnell (Oracle Developer Relations)
**Version:** 1.1.0
**Created:** April 23, 2026
**Last Updated:** May 18, 2026

---

## Context

The "Developer Tech Days - RAG to Agents" presentation walks learners through a conceptual maturity ladder: chatbots, RAG, LLM-driven workflows, agentic AI, with supporting material on tools/skills/MCP, security, observability, and memory. The deck is architectural and has no code.

This companion notebook makes the ladder concrete with working code against the Prism (CityPulse) smart-city dataset. The chatbot tier (slides 7-8) is intentionally skipped.

The notebook reinforces the deck by progressively building one system:

1. **RAG**: grounded answers over Prism content using Oracle AI Database 26ai vector (and hybrid) search with the in-database ONNX `DEMO_MODEL`.
2. **LLM-driven workflow**: a deterministic multi-step pipeline that uses RAG as a step, not as the whole system.
3. **Agent**: a LangGraph agent powered by Ollama that decides which tools to call, wrapping the same retrieval primitives plus the unified relational + JSON + graph + vector query, with short-term and long-term memory. Both memory surfaces are durable in the same Oracle AI Database 26ai instance via `langgraph-oracledb`'s `OracleSaver` (thread checkpointer) and `OracleStore` (long-term semantic memory with HNSW vector search).

The marquee lab is a **bridge incident scenario**: given an asset (e.g., Harbor Bridge), the system retrieves recent incident data via a single Oracle query mixing relational filters, JSON `specifications`, SQL/PGQ graph traversal across `CITYPULSE_GRAPH`, and vector (or hybrid) search over `V_CHUNKS_UNIFIED`. The agent hands that context to Ollama and returns: **recommended course of action, reasoning, and next steps**.

### Database prerequisites (do NOT assume prior-lab state)

The notebook does **not** assume any prior notebook has been run. Before opening the notebook, the learner runs a documented prep sequence that is idempotent and safe to re-run:

1. `@schema-data/prism-setup.sql`: creates PRISM user, canonical tables, JSON collection, JSON Duality View, and `CITYPULSE_GRAPH`.
2. Load the `DEMO_MODEL` ONNX embedding model (per `docs/load_onnx_model.md`; environment-specific).
3. `python schema-data/prism-seed.py`: loads districts, assets, connections, procedures, logs, reports.
4. `python schema-data/prism-ingest.py`: chunks narratives and embeds them into `DOCUMENT_CHUNKS`.
5. `@schema-data/prism-indexes.sql`: creates the HNSW vector index on `DOCUMENT_CHUNKS`.
6. **`@notebooks/rag_to_agents_prep.sql`**: creates the optional hybrid vector index used by the agent's `search_incidents_semantic` tool. Idempotent.

The agent's long-term memory tables and the LangGraph thread-checkpointer tables are **not** created by a prep script. They are created by `langgraph-oracledb`'s `OracleSaver.setup()` and `OracleStore.setup()` calls from inside the notebook itself (§5.4), idempotently, on first run. This is a deliberate teaching moment: the framework owns its own schema.

All six prep steps are listed in Section 0 of the notebook with exact commands. Section 0 then runs a **readiness probe** that verifies every object the notebook depends on exists and has data; if any check fails, the cell prints the precise missing item and halts with a pointer to the relevant prep step. The probe also verifies that the `langgraph-oracledb` Python package is importable.

### Python prerequisites

The workshop environment pre-installs the Python libraries this notebook needs; it does **not** run `pip install` at notebook start. The required packages and the versions pinned in the top-level `requirements.txt`:

| Package | Version | Used for |
|---------|---------|----------|
| `oracledb` | 4.0.0 | Oracle AI Database 26ai connectivity (thin mode) |
| `requests` | 2.32.5 | Raw HTTP RAG example in §1.7 (shows what a framework abstracts over) |
| `langchain` | 1.0.7 | Chains, prompt templates, output parsers (Sections 1-2) |
| `langchain-core` | 1.0.3 | Messages, `@tool` decorator, runnables |
| `langchain-community` | 0.4.1 | `OracleEmbeddings` (in-database `DEMO_MODEL` for `OracleStore` writes) |
| `langchain-ollama` | 1.0.0 | `ChatOllama` client for Ollama |
| `langgraph` | 1.1.10 | `StateGraph`, `ToolNode` (Section 5) |
| `langgraph-oracledb` | 1.0.1 | `OracleSaver` (checkpointer) and `OracleStore` (long-term memory) |
| `pydantic` | 2.10.6 | Structured-output validation for the workflow nodes |

If you run the notebook outside the workshop image, install these first with `pip install` (or equivalent); the notebook itself contains no install cell.

### Ollama prerequisites

Ollama is assumed running (locally or via the workshop image) and reachable at `OLLAMA_BASE_URL`. The exact model tag is a configurable `OLLAMA_MODEL` variable, so the notebook works with whatever model is installed. Section 0 includes a reachability and model-pulled check.

---

## Key decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Notebook shape | New standalone `rag_to_agents_lab.ipynb` in `notebooks/` | Keeps data_fundamentals notebook focused on multi-model SQL; this one focuses on RAG to agent. |
| Prereqs | **No assumption of prior notebook state.** Learner runs the documented DB prep sequence plus `notebooks/rag_to_agents_prep.sql`. Section 0 validates readiness. | Notebook runs reliably regardless of what else has been done against the database. |
| Agent framework | **LangGraph** (StateGraph with tool-calling node + tool node) | Matches the "AI agent reasoning loop" slide 1-to-1. Current LangChain-recommended agent pattern. |
| LLM runtime | **Ollama** via `langchain-ollama.ChatOllama` | Local, private, free; matches workshop expectations. |
| Ollama model | Configurable `OLLAMA_MODEL` variable | Model tag unknown at authoring time; configurable cell lets the notebook run with `llama3.1`, `llama3.2`, `qwen2.5`, etc. |
| Embedding | In-database `DEMO_MODEL` via `VECTOR_EMBEDDING(... USING :text AS data)` (for retrieval) and `OracleEmbeddings(... params={"provider":"database","model":DEMO_MODEL})` (for `OracleStore` writes) | No external API, no data egress, consistent with Prism. Same model drives both source-data retrieval and agent-memory retrieval. |
| Retrieval | Vector search on `V_CHUNKS_UNIFIED`; hybrid vector+keyword search for the agent's richer retrieval tool | Demonstrates both patterns from the deck. |
| Marquee query | Single Oracle SQL statement combining relational filters, JSON `specifications` extraction, SQL/PGQ `GRAPH_TABLE` traversal, and vector search | Delivers on the "all four models in one query" requirement. |
| Scope add-ons | Tools/skills/MCP primer; security as inline callouts; observability via a per-step trace table; durable agent memory (both surfaces). | User ranked security as secondary and observability as "shown and called out only." Memory is two surfaces, both durable; the follow-up presentation covers richer memory architectures (hierarchical, episodic vs. semantic, summarization, eviction). |
| Memory surface | **`langgraph-oracledb`** for both surfaces: `OracleSaver` (short-term/thread state) + `OracleStore` (cross-session semantic memory, HNSW vector search over `OracleEmbeddings(DEMO_MODEL)`) | One framework, one database, both surfaces durable. The agent's long-term memory lives in the same Oracle instance as the canonical Prism data, embedded with the same ONNX model, queryable by the same SQL. This is the most pointed UMT demonstration in the notebook. |
| Memory tools | Three thin wrappers over `OracleStore`: `remember(asset_name, note)` (namespace put), `recall(asset_name, limit)` (namespace lookup), `recall_similar(query, asset_name=None, k)` (HNSW semantic search) | Tool names and signatures stable; implementations are framework calls instead of hand-written SQL. |
| Target runtime | ~60-75 minutes end-to-end | Matches a hands-on workshop slot. |

### Known constraints to handle

| Constraint | Impact | Workaround |
|------------|--------|------------|
| `GRAPH_TABLE` cannot correlate to outer query (no LATERAL) | Can't pass agent-resolved asset IDs directly into `GRAPH_TABLE WHERE` | Resolve asset in a CTE by `name`, JOIN graph results to the CTE. |
| `GRAPH_TABLE` KEY columns aren't exposed as PROPERTIES | `asset_id` isn't available inside GRAPH_TABLE COLUMNS | Match on `name` (unique property), JOIN back to `infrastructure_assets` for `asset_id`. |
| Ollama tool-calling quality varies by model | Weak models may ignore tool schemas | Configurable model + a tool-calling sanity check before the agent runs; document known-good models. |
| `VECTOR_DISTANCE` needs `FETCH FIRST N`; hybrid uses `DBMS_HYBRID_VECTOR.SEARCH` JSON spec | Same constraints the data_fundamentals lab already solved | Reuse the shape from the existing notebook's hybrid search cells. |
| `OracleStore` and `OracleSaver` each need their own database connection | Sharing the module-global `conn` with the rest of the notebook could cause transaction interleaving | Open one fresh `oracledb.connect()` per surface inside §5.4; register both on a `contextlib.ExitStack` so they close cleanly on kernel shutdown. |
| `OracleStore`'s vector dimension must match the embedding model's output | Hardcoding a dimension couples the notebook to one ONNX model | Probe DEMO_MODEL's output at runtime by calling `OracleEmbeddings.embed_query("dimension probe")` and measuring the result, then pass that to `OracleStore`'s `index["dims"]`. |

---

## Notebook structure

Eight sections mirror the deck's ladder. Each code cell is short and preceded by a markdown cell naming the slide/concept it reinforces.

### Section 0: Welcome, prerequisites, and readiness probe (~7 min)

- **0.1** Title, objectives, slide map.
- **0.2** Database prerequisites (exact commands for the six prep steps).
- **0.3** Ollama prerequisites.
- **0.4** Configuration: `DB_USER`, `DB_PASSWORD`, `DB_DSN`, `ONNX_MODEL="DEMO_MODEL"`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (with options), `THREAD_ID`.
- **0.5** Imports and helpers: `show_table`, `print_json`, `_json_default`, `show_trace(steps)` for per-step observability. Includes the new `langgraph-oracledb` imports (`OracleSaver`, `OracleStore`) and `langchain-community`'s `OracleEmbeddings`. (No pip install cell; deps are pre-provisioned per the table above.)
- **0.6** Connect to Oracle + version check.
- **0.7** Database readiness probe (comprehensive green/red summary; halts with actionable message on any miss). Includes a check that `langgraph_oracledb` is importable.
- **0.8** Connect to Ollama + model smoke-test (distinguishes connection failure from missing model).

### Section 1: RAG, grounded (~10 min) · reinforces slides 9-14

- **1.1** What RAG does; DEMO_MODEL embeds in-database.
- **1.2** Embed a query in-database and show `VECTOR_DIMS`.
- **1.3** The retriever, one function.
- **1.4** `retrieve_context(question, k=5, asset_filter=None)` against `V_CHUNKS_UNIFIED`.
- **1.5** Try it on a bearings/corrosion query.
- **1.6** Grounding the LLM.
- **1.7** RAG with **no framework**: `rag_answer_raw` using `requests.post(...)` to `/api/chat`. Shows that RAG fundamentally needs only retrieval (SQL) + prompt (f-string) + one HTTP call.
- **1.8** The same thing with LangChain: `rag_answer` using `ChatPromptTemplate | llm | StrOutputParser`. Short markdown in between: what the framework actually did, and when it starts paying off (answer: not much here, but a lot in §2).
- **1.9** A grounded question about Harbor Bridge (runs the LangChain version; raw version is already exercised in 1.7).
- **1.10** Where RAG runs out of road (slides 15-16).

### Section 2: LLM-driven workflow (~10 min) · reinforces slides 18-22

- **2.1** Workflow anatomy (deck's 6-step pattern).
- **2.2** What we're building (4-step triage pipeline).
- **2.3** Classifier node (structured output).
- **2.4** RAG-retrieval node.
- **2.5** Drafter node (recommendation / rationale / next_steps).
- **2.6** Formatter node, markdown.
- **2.7** Run with a realistic bridge incident blurb + trace table.
- **2.8** Deterministic and auditable call-out.
- **2.9** Where workflows run out of road (slide 22).

### Section 3: Tools, skills, MCP brief primer (~5 min) · reinforces slides 29-35

- **3.1** What a tool is (typed function + docstring).
- **3.2** Four data-retrieval `@tool` definitions:
  1. `get_asset_overview(asset_name)`: relational + JSON.
  2. `get_recent_incidents(asset_name, days=180)`: maintenance logs + findings. (EXERCISE: defined in §3.2 by the learner.)
  3. `get_connected_assets(asset_name)`: SQL/PGQ graph neighbors.
  4. `search_incidents_semantic(query, asset_name=None, k=5)`: hybrid search with vector fallback.

  The three memory tools (`remember`, `recall`, `recall_similar`) are defined in §5.4 because they depend on the `OracleStore` instance, which is built alongside the checkpointer just before the graph is compiled.
- **3.3** Skills as SOPs: `BRIDGE_TRIAGE_SKILL` constant.
- **3.4** MCP in one paragraph (tools above could be MCP-exposed).
- **3.5** Security call-out (excessive agency + prompt injection).

### Section 4: Marquee query (~10 min)

- **4.1** Why one query.
- **4.2** Anatomy (five CTEs: bridge, specs, neighbors, incidents, ranked).
- **4.3** The unified SQL (relational + JSON dot notation + SQL/PGQ GRAPH_TABLE + vector distance) returning asset/specs/graph_context/ranked_incidents as JSON.
- **4.4** Execute for Harbor Bridge + "bearing corrosion and cracking"; pretty-print.
- **4.5** Hybrid swap-in (optional).

### Section 5: LangGraph agent with memory (~15 min) · reinforces slides 23-28, 35, 48

- **5.1** Reasoning loop, StateGraph.
- **5.2** Wrap the unified query as `get_bridge_incident_brief`.
- **5.3** Memory surfaces: short-term (`OracleSaver`) and long-term (`OracleStore`), both durable in Oracle, both backed by `langgraph-oracledb`.
- **5.4** Set up memory and tools: probe `DEMO_MODEL` dimensions, open dedicated connections for store and saver, instantiate `OracleStore` (HNSW + COSINE, `table_suffix="bridge"`) and `OracleSaver`, call `.setup()` on both. Define the three memory tools as thin wrappers over the store. Compile the graph with both surfaces wired in.
- **5.5** State definition.
- **5.6** Nodes (model, tools-sequential, enforce-remember safety net).
- **5.7** System prompt (skill + prompt-injection defense + memory directives).
- **5.8** Run first turn (streaming).
- **5.9** Render answer + trace.
- **5.10** Follow-up turn demonstrating both memory surfaces (checkpointer rehydrates the thread; `recall` pulls the note from the prior turn).
- **5.11** Peek at long-term memory via `store.search((MEMORY_NAMESPACE_ROOT,), limit=5)`.
- **5.12** Memory call-out (slide 48). Both surfaces durable; one database; same `DEMO_MODEL` for source data and agent memory.
- **5.13** Observability call-out (slides 43-44).
- **5.14** Security recap (allowlisted tools, prompt-injection defense, principle of least privilege, the lethal trifecta and why removing egress closes it).

### Section 6: Try it yourself (~5 min)

Exercises: swap the asset, add a new tool, change `OLLAMA_MODEL`, tighten the system prompt, extend memory by storing a `severity` field inside the JSON value and filtering on it in `recall`.

### Section 7: Cleanup and wrap-up (~2 min)

Close the database connection; recap mapping sections to slides; pointers to LangGraph / Ollama / MCP / Oracle LiveLabs.

---

## Deliverables

1. **`docs/notebook-plan-rag-to-agents.md`**: this design document.
2. **`notebooks/rag_to_agents_prep.sql`**: idempotent prep script. In the current version this creates only the hybrid vector index on `DOCUMENT_CHUNKS` (best-effort; the notebook falls back to vector-only search if the feature isn't available). Final `SELECT` prints `rag_to_agents_prep: OK`.
3. **`notebooks/rag_to_agents_reset.sql`**: idempotent reset script that wipes both memory surfaces (`store_bridge` and the four `checkpoint*` tables, scoped to the configured thread) between lab runs without disturbing source data.
4. **`notebooks/rag_to_agents_lab.ipynb`**: the notebook, built to the cell-by-cell spec above.

---

## Verification plan

1. **DB prep.** Run, in order, against a fresh DB: `prism-setup.sql` -> load ONNX model -> `prism-seed.py` -> `prism-ingest.py` -> `prism-indexes.sql` -> `notebooks/rag_to_agents_prep.sql`. Confirm final script prints `rag_to_agents_prep: OK`.
2. **Ollama check.** `ollama list` shows the configured model; `curl $OLLAMA_BASE_URL/api/tags` responds.
3. **Readiness probe.** Run Section 0 in isolation; all green. Uninstall `langgraph-oracledb`, re-run; confirm probe surfaces actionable failure. Reinstall; green.
4. **Full run.** Restart and Run All completes without errors.
5. **Section 1 (RAG).** `rag_answer("What recent issues have been reported on Harbor Bridge?")` returns a coherent grounded answer.
6. **Section 2 (workflow).** 4-step markdown report emitted; `show_trace` shows 4 steps.
7. **Section 4 (marquee query).** All four JSON sections populated for `Harbor Bridge` + `"bearing corrosion and cracking"`.
8. **Section 5 (agent, first turn).** At least one tool call visible in stream; final `recommendation / rationale / next_steps` block; `remember(...)` called; one row appears in `store_bridge`.
9. **Section 5 (memory).** Follow-up turn: checkpointer rehydrates prior messages; agent calls `recall(...)` and surfaces the note written in the first turn; §5.11 peek shows the note via `store.search`.
10. **Section 5 (reset).** Run `notebooks/rag_to_agents_reset.sql`; confirm `store_bridge` row count goes to 0 and the configured `thread_id` is cleared from `checkpoints`. Re-running the agent starts fresh.
11. **Model swap.** Changing `OLLAMA_MODEL` and re-running Section 5 still works.
12. **Security probe.** A prompt-injection user message does not cause destructive tool calls.

---

## Design evolution

This section captures the meaningful design changes between 1.0.0 (April 23, 2026) and the current version. The original Key Decisions table is preserved in Appendix A for reference.

### From 1.0.0 to 1.1.0 (May 18, 2026)

**What changed.** Both memory surfaces moved from their original implementations to `langgraph-oracledb`:

- **Short-term/thread memory**: `langgraph.checkpoint.memory.MemorySaver` (in-process dict) was replaced by `langgraph_oracledb.checkpoint.oracle.OracleSaver`, which writes one row per agent step to `checkpoints` / `checkpoint_blobs` / `checkpoint_writes` tables in the same Oracle instance as the canonical Prism data.
- **Long-term/persistent memory**: a hand-rolled `AGENT_MEMORY` table (one row per note, one `VARCHAR2` + one `VECTOR` column, HNSW index, hand-written SQL in the `remember` / `recall` / `recall_similar` tools) was replaced by `langgraph_oracledb.store.oracle.OracleStore`, which manages its own `store_<suffix>` and `store_vectors_<suffix>` table pair and exposes a `put` / `get` / `search` API. The three memory tools were rewritten as thin wrappers over this API; tool names and signatures are unchanged so the SOP and system prompt did not need to change.

**Why it changed.** The migration was a deliberate trade between two things:

- *Loss*: the original `AGENT_MEMORY` design was a strong teaching artifact. Section 5.11 originally peeked at the table with `SELECT ... FROM agent_memory ORDER BY created_at DESC` to make the point "this is just a table with a VECTOR column, queryable with SQL." That direct-SQL inspection is gone; `OracleStore`'s tables are framework-owned (the suffix is deterministic but the schema is opaque to the workshop audience).
- *Gain*: the UMT story got stronger. *Both* memory surfaces now live in Oracle, with the same `DEMO_MODEL` doing the embeddings, in the same converged store. The original architecture had short-term memory in process (lost on kernel restart, not durable) and long-term memory in a hand-rolled table. The new architecture has both surfaces durable in the same database the source data lives in. The argument "you don't need a separate vector DB for agent state" became "you don't need anything other than this Oracle instance for any of it."

The gain was deemed larger than the loss. Section 5.11's inspection now uses `store.search((MEMORY_NAMESPACE_ROOT,), limit=5)` instead of raw SQL; the loss of teaching directness is real but the framework call still demonstrates what's important (that the data is there and queryable).

**Schema management changes.**

- `notebooks/rag_to_agents_prep.sql` was originally creating `AGENT_MEMORY` plus the optional hybrid vector index. With `OracleStore` owning long-term memory and `OracleSaver` owning checkpoints, both call `.setup()` from the notebook to create their tables idempotently. The prep script was slimmed to *only* the optional hybrid vector index on `DOCUMENT_CHUNKS`.
- The prep script also moved from `docs/` to `notebooks/` to keep SQL co-located with the notebook that uses it.
- A new `notebooks/rag_to_agents_reset.sql` was added to wipe both memory surfaces between runs; this replaces the original guidance to truncate `AGENT_MEMORY` manually.

**Dependencies added.**

- `langgraph-oracledb==1.0.1`: the new memory persistence layer.
- `langchain-community==0.4.1`: provides `OracleEmbeddings` which `OracleStore` uses to embed memory items in-database on write.

**Path corrections.** Older doc-directory references for the RAG notebook and prep script have been corrected to `notebooks/rag_to_agents_lab.ipynb` and `notebooks/rag_to_agents_prep.sql`.

**Section restructure: §3.2 and §5.4.** In the original plan, all six tools (four data-retrieval + `remember` + `recall`) were defined together in §3.2. In the current notebook, the three memory tools (`remember`, `recall`, `recall_similar`) are deferred to §5.4 because their implementation depends on the `OracleStore` instance, which is built alongside the checkpointer just before the graph is compiled. The notebook's §3.2 explicitly notes this deferral so the learner isn't confused by the count.

**Exercise 6.5 ("Try it yourself").** The original exercise asked the learner to add a `severity` column to `AGENT_MEMORY`. With framework-managed schema, schema modifications aren't appropriate. The exercise was rewritten to ask the learner to store severity as another field inside the `OracleStore` value's JSON dict, and to filter on it client-side in the `recall` wrapper. Same pedagogical intent, different mechanism.

### Not changed

The marquee unified-query design (§4) didn't change. The RAG primitives (§1) didn't change. The workflow shape (§2) didn't change. The skill/SOP framing (§3.3), the prompt-injection defense (§5.7, §5.14), the per-step observability trace (§5.13), and the section-to-slide crosswalk all carried over intact.

---

## Appendix A: Original key decisions (1.0.0)

Preserved verbatim from the April 23, 2026 version of this document so that future readers can see the architectural starting point. **Current decisions are in the Key Decisions section above; this appendix is historical.**

| Decision | Choice (1.0.0) | Rationale (1.0.0) |
|----------|----------------|-------------------|
| Notebook shape | New standalone `rag_to_agents_lab.ipynb` in `notebooks/` | Keeps data_fundamentals notebook focused on multi-model SQL; this one focuses on RAG to agent. |
| Prereqs | No assumption of prior notebook state. Learner runs the documented DB prep sequence plus `notebooks/rag_to_agents_prep.sql`. Section 0 validates readiness. | Notebook runs reliably regardless of what else has been done against the database. |
| Agent framework | LangGraph (StateGraph with tool-calling node + tool node) | Matches the "AI agent reasoning loop" slide 1-to-1. Current LangChain-recommended agent pattern. |
| LLM runtime | Ollama via `langchain-ollama.ChatOllama` | Local, private, free; matches workshop expectations. |
| Ollama model | Configurable `OLLAMA_MODEL` variable | Model tag unknown at authoring time; configurable cell lets the notebook run with `llama3.1`, `llama3.2`, `qwen2.5`, etc. |
| Embedding | In-database `DEMO_MODEL` via `VECTOR_EMBEDDING(... USING :text AS data)` | No external API, no data egress, consistent with Prism. |
| Retrieval | Vector search on `V_CHUNKS_UNIFIED`; hybrid vector+keyword search for the agent's richer retrieval tool | Demonstrates both patterns from the deck. |
| Marquee query | Single Oracle SQL statement combining relational filters, JSON `specifications` extraction, SQL/PGQ `GRAPH_TABLE` traversal, and vector search | Delivers on the "all four models in one query" requirement. |
| Scope add-ons | Tools/skills/MCP primer; security as inline callouts; observability via a per-step trace table; lightweight agent memory | User ranked security as secondary and observability as "shown and called out only." Memory is kept minimal (follow-up presentation covers it deeply). |
| Memory surface | LangGraph `MemorySaver` checkpointer (short-term/thread state) + a tiny Oracle `AGENT_MEMORY` table (cross-session notes) exposed as `remember` / `recall` tools | Demonstrates the two dominant flavors of memory without getting into embeddings-of-memories, summarization, or eviction policies. |
| Target runtime | ~60-75 minutes end-to-end | Matches a hands-on workshop slot. |
