# Prism Workshop Instructor Runbook

**Version:** 0.2.0
**Last Updated:** May 18, 2026

This runbook supports the approved Prism workshop slide decks and the two hands-on notebooks in this repository. It is not a replacement for the approved decks.

Use the slide decks for narrative, positioning, architecture explanation, and customer-facing messaging. Use this guide for delivery logistics, notebook handoffs, checkpoints, troubleshooting, reset guidance, and cut lines.

**First time delivering one of these workshops?** See [First time delivering this workshop?](#first-time-delivering-this-workshop) at the bottom of this guide for a prep checklist that covers reading, dry-running, rehearsing, and deliberate failure practice.

## Approved delivery assets

| Workshop | Approved deck | Notebook | Primary purpose |
|---|---|---|---|
| Data Fundamentals for AI Application Development | `[Approved Data Fundamentals deck]` | `notebooks/data_fundamentals_lab.ipynb` | Show how Oracle Database can work with relational, JSON, graph, vector, and hybrid search patterns using one Prism dataset. |
| From RAG to Agents | `[Approved RAG to Agents deck]` | `notebooks/rag_to_agents_lab.ipynb` | Show the progression from grounded retrieval to deterministic workflows, tools, agents, and memory. |

Replace the deck placeholders above with the approved PowerPoint filenames or internal links when publishing this guide for instructors.

## How to use this guide

1. Deliver the approved deck content for the conceptual story.
2. Switch to the notebook when the deck reaches a hands-on section.
3. Remember, we are here to pitch solutions, not features or products. Yes these labs use Oracle features and products, but that is secondary or tertiary messaging.
4. Use the checkpoint tables below to know when to pause, confirm learner progress, and decide whether to continue or skip optional content.
5. Use the troubleshooting section when learners hit common setup or runtime issues.
6. Use the cut lines when time is short.

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

## Talk-track for the marquee moments

Each workshop has one moment that carries the workshop's whole argument. If the audience walks away remembering only one thing, it should be this. These moments deserve preparation more than other parts of the lab. The scripts below are starting points; make them your own. But have *something* prepared, because winging it through the marquee moment is the most common failure mode in technical workshops.

### Data Fundamentals: the unified query (Section 5)

This is where you make or lose the workshop. Up to this point you've shown each data shape in isolation: relational rows in Section 1, JSON in Section 1, graph traversal in Section 1, vector search in Section 4. Section 5 puts them all in one SQL statement, against the same canonical dataset, in the same transaction, with no synchronization. That is the entire Data Fundamentals argument.

**Before running the cell:**

> "OK, here's the moment everything has been building toward. So far you've seen relational queries, JSON queries, graph traversal, and vector search, each in their own section. What I'm about to run is one SQL statement that does all four of those things at once. Same database. Same dataset. Same transaction. No sync layer between data shapes. Watch the result."

**During the cell execution (usually 1-3 seconds):**

Don't fill the silence with technical detail. Just say:

> "One statement. Watch what comes back."

**After the result appears:**

> "What just happened: one SQL statement traversed a graph, did a vector search, pulled JSON specifications, and applied a relational filter. Look at what isn't here. There's no Pinecone client, no Neo4j driver, no separate JSON document store, no ETL job copying data between any of them. Same canonical data, same transaction, four shapes. *This* is the converged database in one query."

If the audience seems engaged, this is the right moment to walk through the CTEs:

> "Let me show you how it's structured. There are five named subqueries up top, see the WITH clause. The first one resolves an asset by name; relational lookup. The second one extracts specifications from a JSON column. The third one does a SQL/PGQ graph traversal to find connected assets. The fourth one runs a vector search over the maintenance history. And the final SELECT assembles everything into one JSON document. No magic; just SQL doing what databases do, with data shapes that didn't exist in databases ten years ago."

If timing is tight, skip the CTE walkthrough and let the result speak for itself.

**Anti-patterns to avoid:**

- Don't read the result aloud. The audience can read.
- Don't apologize for the SQL being long. It's long *because* it does four things; that's the point.
- Don't compare to "what this would look like in MongoDB plus Pinecone plus Neo4j" by sketching code on the screen. That weakens the moment because the audience starts thinking about the comparison instead of absorbing the result.

### RAG-to-Agents: the agent's first turn (Section 5.8)

This is where the workshop's narrative arc lands. Sections 1-4 built up to this: retrieval, then grounded retrieval, then deterministic workflows over retrieval, then tools wrapping retrieval. Now an agent uses all of it autonomously.

**Before running the cell:**

> "OK, here's the moment. Up to this point, we've been the ones deciding what to do: I retrieve, I prompt, I run the workflow steps in this order. Now I'm going to give that decision to the model. I'll hand it an incident, give it a set of tools, give it an SOP for what to do with a bridge incident, and ask it to figure out the rest. Watch the stream."

**During the cell execution (30-90 seconds, depending on the local model):**

This is the hardest part to instructor through. The agent will emit chunks slowly. The audience needs guidance about what to look for, but you can't predict exactly when each event will appear. A few options for what to say:

> "Watch for three things: which tools it decides to call, what order it calls them in, and whether it remembers to call `remember` at the end. The SOP we gave it says it has to. We'll see if it complies."

Then go quiet and let the agent run. When tool calls start streaming:

> "There's the first tool call. It chose `get_asset_overview`. That makes sense; it doesn't know anything about this asset yet."

Continue narrating as new tool calls appear:

> "Now `get_recent_incidents`. Now `search_incidents_semantic` over the maintenance logs. It's building context the same way you would."

When the final answer comes back:

> "And there's the response. Recommendation, rationale, next steps. Now watch the last thing it does."

(If `remember` got called, that's visible in the trace.)

> "It called `remember`. That just wrote a note to long-term memory. Next turn, we'll see the agent recall it."

**Anti-patterns to avoid:**

- Don't pre-script what the agent will do. The model is non-deterministic; you'll be wrong sometimes. Narrate what you see, not what you expect.
- Don't apologize when the agent does something unexpected. If it calls tools in a weird order or skips one you predicted, treat that as a feature: "interesting; it didn't bother with the unified query this time. The SOP didn't require it, and the cheaper tools gave it enough context. That's a small example of why we don't hard-code the order."
- Don't get into LangGraph internals. The audience can see the agent decide. They don't need to understand `StateGraph` for the moment to land. Save framework explanation for after the demo.
- Don't refresh and re-run if the first turn produces a weak answer. Each fresh run accumulates memory state. Better to talk through the answer you got than to chase a better one. If you must re-run, run the reset script first (see [Cell idempotency](#cell-idempotency-what-is-safe-to-re-run) above).

**If the agent's behavior is unexpected:**

The agent may skip a tool you expected it to call, call an unexpected one, produce a weak final answer, or take longer than expected. None of these are workshop failures *if* you frame them right. The honest framing:

> "What we're watching is a real agent making real decisions with a local model. Some runs are sharper than others; that's the nature of working with LLMs. The architectural point still holds: it has tools, it has memory, it has a database it can query for grounded context, and it made decisions about which of those to use. Whether this particular run was its best work is a separate question from whether the pattern works."

## Reset and rerun guidance

Use reset guidance when a LiveLabs environment has already been used or when a session needs to be repeated.

| Reset need | Recommended action |
|---|---|
| RAG-to-Agents state needs cleanup | Run `notebooks/rag_to_agents_reset.sql` using the intended workshop schema. |
| RAG-to-Agents setup needs to be prepared again | Run `notebooks/rag_to_agents_prep.sql` using the intended workshop schema. |
| Data Fundamentals notebook has been run before | Confirm whether inserted maintenance logs, generated vectors, and recreated indexes should be left in place or reset by the workshop provisioning process. |
| Full environment is inconsistent | Prefer rebuilding or refreshing the LiveLabs environment instead of manually patching many objects during a live session. |

Before a repeated delivery, run the readiness checks in both notebooks again.

## Timing budget cheat sheet

When you're mid-session and the clock is moving faster than you'd like, glance here. The "where you should be" column is the most important: if the wall clock has passed a checkpoint and you're still earlier in the notebook, you're behind. The recovery column tells you what to give up to catch up.

### Data Fundamentals, 60-minute slot

| At wall clock... | You should be... | If you're behind, cut... | If you're ahead, add... |
|---|---|---|---|
| t+10 min | Wrapping Section 1 (Prism data model) | Compress Section 1 to the schema overview only; skip individual JSON and graph traversal cells | Nothing; pace is fine |
| t+25 min | Mid Section 4 (vector search) | Skip Section 3 vector-index discussion; explain the index is pre-built | Run one extra ad-hoc vector query suggested by the audience |
| t+40 min | Mid Section 5 (unified query) | Don't cut Section 5; this is the marquee. Cut Section 6 instead | Walk through the unified query CTE-by-CTE rather than just running it |
| t+55 min | Wrapping (Section 7 or end of 6) | Skip Section 6 entirely; close on Section 5's unified query result | Run optional hybrid search exercises |

### Data Fundamentals, 90-minute slot

| At wall clock... | You should be... | If you're behind, cut... | If you're ahead, add... |
|---|---|---|---|
| t+15 min | End of Section 1 (Prism data model) | Compress graph traversal in Section 1 to a single cell with brief narration | Nothing; pace is fine |
| t+30 min | End of Section 2 (embeddings) | Skip the manual embedding-generation cells; explain `DEMO_MODEL` produces vectors in-database and move on | Show what an embedding actually looks like (open the vector value) |
| t+45 min | End of Section 4 (vector search) | Skip Section 3 vector-index discussion; explain it's pre-built | Take an audience-suggested query and run it |
| t+65 min | Mid Section 5 (unified query) | Don't cut Section 5; cut Section 6 instead | Walk the unified query CTE-by-CTE |
| t+80 min | Mid or end of Section 6 (hybrid search) | Skip the rest of Section 6; jump to the wrap | Run the optional Reciprocal Rank Fusion exercise |
| t+88 min | Wrap-up | Close with the unified query result and one hybrid result side-by-side | Open up questions |

### RAG-to-Agents, 90-minute slot

| At wall clock... | You should be... | If you're behind, cut... | If you're ahead, add... |
|---|---|---|---|
| t+10 min | End of Section 0 (readiness probe) | Don't cut here; the lab depends on Section 0 passing | Briefly show what `OracleSaver.setup()` and `OracleStore.setup()` create |
| t+22 min | End of Section 1 (grounded RAG) | Skip the no-framework version (Section 1.7); go straight to the LangChain version | Run an audience-suggested grounded question |
| t+35 min | End of Section 2 (workflow) | Show one workflow output and skip the trace-table discussion | Walk the structured-output schema |
| t+48 min | End of Section 4 (unified query as tool) | Skip Section 3 if necessary; mention tools only briefly and let Section 5's tool calls show what they are | Walk the unified-query CTEs |
| t+70 min | First agent turn complete | Don't cut here; cut Section 6 instead | Walk the per-step trace in detail |
| t+82 min | Memory follow-up turn complete | Skip Section 6 (Try it yourself); close on memory inspection | Run a third turn to show the memory accumulating |
| t+88 min | Wrap-up | Show the long-term memory store contents and close | Open Q&A |

### What this is NOT

It is not a substitute for knowing the material. An instructor who hasn't run the notebook end-to-end shouldn't rely on the cheat sheet to recover; the cut decisions assume you understand what each section is for. The cheat sheet helps a prepared instructor stay on time; it doesn't rescue an unprepared one.

It is not permission to rush through the marquee moments. Section 5 (unified query) in Data Fundamentals and Section 5 (the agent's first turn) in RAG-to-Agents are the payoff sections. If you have to spend extra time on these and skip an earlier or later section to make it work, that's the right trade.

## Suggested cut lines

Use these when the group is behind schedule.

| If short on time | Cut or compress | Keep |
|---|---|---|
| Data Fundamentals is running long | Skip optional exercises and Section 6 Hybrid Vector Search. | Keep Section 5 unified query. |
| Vector index creation is slow | Explain the purpose and move on if the index already exists or later searches work. | Keep at least one vector search result. |
| RAG-to-Agents is running long | Compress Section 2 workflow discussion and skip Section 6 Try it yourself. | Keep RAG retrieval, unified query, first agent turn, and memory follow-up. |
| Ollama/model behavior is inconsistent | Use the trace and expected checkpoint explanation instead of spending too long re-running. | Keep the database grounding and tool-use explanation. |

## Live recovery playbook

When something goes wrong mid-session and the kernel itself is suspect, you have two questions to answer fast: (1) is the kernel actually broken, or am I debugging the wrong layer; and (2) what's the fastest path back to a known-good state without losing the audience.

### Is the kernel actually wedged?

Quick triage before you reach for the kernel restart:

| Symptom | Likely kernel issue? | First action |
|---|---|---|
| A cell shows `[*]` for more than 30 seconds and shouldn't | Maybe. Could be a slow query or stuck network call | Wait 60 seconds total. If the database is on a shared environment, slow is expected for vector index creation. If it's an Ollama call, see below. |
| Kernel interrupt (the square stop button) does nothing | Yes, kernel is wedged | Restart kernel; see recovery flow below |
| A cell finishes but the next cell errors with `NameError` for something you just defined | Maybe. State desync from out-of-order execution | Try re-running the cell that defined the missing name first; if that also errors, restart |
| Every cell errors with `oracledb.InterfaceError` or "connection closed" | Database connection dropped, kernel is fine | Re-run the connect cell (Section 0.6 in either notebook); skip the kernel restart |
| Every cell errors with a confusing traceback you've never seen before | Possible kernel corruption | Read the traceback once. If it's genuinely unfamiliar, restart |

**Don't restart prematurely.** A kernel restart costs you 90 seconds of recovery time minimum, and the audience watches the whole thing. Use it when you've confirmed the kernel itself is the problem, not when a cell happens to be slow.

### Recovery flow: Data Fundamentals lab

If you've decided the kernel is wedged, here's the fastest path back:

1. **Restart the kernel** (Kernel menu → Restart).
2. **Re-run Section 0** (cells 1 through ~9). This re-establishes the database connection and the readiness probe. About 15 seconds.
3. **Re-run Section 1** (cells 10 through ~28). All read-only queries; safe to re-run. About 20 seconds.
4. **Section 2: the maintenance-log insert cell** (cell 36, "Step 1: Insert a new maintenance log for Harbor Bridge") has a built-in cleanup block that deletes any prior run of this same log before inserting. Safe to re-run; it produces the same final state.
5. **Section 3: the vector index cell** (cell 40) has a drop-if-exists block at the top, so it's idempotent. Safe to re-run, but takes ~30 seconds on a shared environment.
6. **Continue from where you were.** Section 4 (vector search) and onward are all reads.

Total recovery time: about 90 seconds plus whatever Section 3 takes. If you were already past Section 3 when the kernel wedged, your recovery is closer to 60 seconds.

### Recovery flow: RAG-to-Agents lab

This one is more delicate because the agent writes memory items as it runs:

1. **Restart the kernel.**
2. **Decide: do you want to keep the agent's existing memory or start fresh?** Both are valid choices.
   - **Keep memory:** the agent's prior decisions persist; the demo continues with accumulated state. Better for "look at how this agent remembers" moments.
   - **Start fresh:** run `notebooks/rag_to_agents_reset.sql` from a SQL client before re-running cell 58 (`.setup()`). Cleaner for repeated runs, but the audience may have seen the memory write you're now erasing.
3. **Re-run Section 0** to re-establish connections and probe readiness. About 20 seconds.
4. **Re-run Sections 1 through 4** (cells 13 through ~55). All read-only retrieval and query construction; safe and necessary because Section 5 depends on the tools and the unified query they reference. About 30 seconds.
5. **Section 5: run cell 58** to rebuild `OracleStore` and `OracleSaver`. The `.setup()` calls are idempotent: existing tables are kept, missing ones are created. Safe regardless of which path you took in step 2.
6. **The agent run cells (around cell 62 onward) are the ones to be careful with.** If you already ran the first turn before the wedge and you chose "keep memory" in step 2, re-running the first turn adds a *second* memory item for the same incident. The demo will still work, but Section 5.11's memory inspection will show duplicate notes. If that bothers you, run the reset script (step 2's "start fresh" path) before continuing.

Total recovery time: about 60 seconds plus whatever the agent's first turn takes (usually 30-90 seconds depending on the model).

### A note on sequence ambiguity

The recovery flows above tell you which cells to skip after a wedge. The full reference for which cells are idempotent and which accumulate state is in [Cell idempotency: what is safe to re-run](#cell-idempotency-what-is-safe-to-re-run), immediately below.

## Cell idempotency: what is safe to re-run

When the recovery playbook (above) sends you back to re-run sections of a notebook, this is the reference for "will running this cell again break anything?" The notebooks are designed to be re-run friendly, but a few cells have specific behaviors worth knowing about.

Three categories:

- **Safe** means re-running produces the same observable result. The cell may be slow or expensive, but you can run it as many times as you want without surprises.
- **Adds state** means re-running accumulates something (database rows, memory items, etc.). The demo still works after re-running but inspection cells later may show more data than the audience saw the first time.
- **Expensive** means re-running takes significant time or rebuilds something that was already there. Idempotent in outcome but not in time-cost.

### Data Fundamentals lab

| Section / cell | Category | What happens on re-run |
|---|---|---|
| Section 0: Configuration and readiness check | Safe | Pure read-only checks; no state change. About 5 seconds. |
| Section 1: Data model exploration (all cells) | Safe | All `SELECT` queries; no writes. |
| Section 2: Embedding inspection cells | Safe | Generates an embedding for display; nothing stored. |
| Section 2: "Insert a new maintenance log and vectorize it" (cell 36) | Safe | Cell has a built-in cleanup block that deletes any prior run of this same log before inserting. Re-running is safe and produces the same final state. |
| Section 3: Vector index creation (cell 40) | Expensive | Drops the existing index and rebuilds it. About 30 seconds on a shared environment. Safe but worth skipping if you can confirm the index already exists from your prep run. |
| Section 4: Vector search cells | Safe | Read-only queries. |
| Section 5: Unified query cells | Safe | Read-only queries. |
| Section 6: Hybrid search setup (cell 64) | Expensive | Drops and recreates the `hybrid_search_demo` table, repopulates from maintenance logs and findings. About 10 seconds. Safe to re-run. |
| Section 6: Hybrid search query cells | Safe | Read-only queries. |
| Section 6: Cleanup (cell 84) | Safe | Drops the demo hybrid index. Safe to re-run (drop-if-exists pattern). |

**Bottom line for Data Fundamentals:** every cell in the notebook is idempotent. The only thing to be aware of is that cell 40 (vector index rebuild) and cell 64 (hybrid table rebuild) take longer than the others on re-run. If you're recovering from a wedge and timing is tight, you can skip cell 40 if the index was already created during your prep run.

### RAG-to-Agents lab

| Section / cell | Category | What happens on re-run |
|---|---|---|
| Section 0: Welcome, prerequisites, readiness probe | Safe | Read-only checks and connection setup. |
| Section 1: RAG retrieval and grounded answers | Safe | Read-only queries plus LLM calls. LLM calls produce different outputs on each run; that's expected for LLM demos. |
| Section 2: LLM-driven workflow | Safe | Same as Section 1: read-only retrieval plus LLM calls. |
| Section 3: Tool definitions (cell 44) | Safe | Defines Python functions; no execution side effects. |
| Section 4: Unified query and wrapper tool | Safe | Read-only queries. |
| Section 5: Memory setup (cell 58) | Safe | `OracleSaver.setup()` and `OracleStore.setup()` are idempotent. Existing tables are kept; missing ones are created. |
| Section 5: First agent run (around cell 62) | **Adds state** | Each call to `run_agent(...)` writes one new memory item to `OracleStore` and writes checkpoint rows to `OracleSaver`. Re-running creates a second memory item for the same incident; Section 5.11's inspection cell will then show both. The demo still works; the duplicate is just clutter. |
| Section 5: Follow-up turn (cell 66) | **Adds state** | Same as the first agent run, plus this turn's checkpointer rehydrates the thread state so it sees the prior turn's memory. Re-running on the same `thread_id` accumulates checkpoints. |
| Section 5.11: Memory peek | Safe | Read-only `store.search()` call. Shows whatever's in `OracleStore` right now, including any duplicates from re-runs. |

**Bottom line for RAG-to-Agents:** Sections 0 through 4 are fully idempotent. Section 5's agent run cells (the `run_agent(...)` calls) accumulate state every time they're invoked. After a wedge or between sessions, if you want a clean memory inspection in 5.11, run `notebooks/rag_to_agents_reset.sql` before re-running Section 5.

### When to reset vs. when to just re-run

| Situation | Recommended action |
|---|---|
| Mid-session kernel wedge, you want to keep the demo going | Don't reset. Re-run cells; accept that 5.11 may show duplicate memory entries. Audience won't notice. |
| Between back-to-back sessions with different audiences | Run `notebooks/rag_to_agents_reset.sql` between sessions. The second audience starts clean. |
| You're about to walk through Section 5.11 carefully | Run the reset script before the first agent turn. Keeps 5.11 inspection clean and obvious. |
| You just want to dry-run a part of the lab | Don't reset between runs. The notebook tolerates accumulated state fine; reset is for situations where audience-facing inspection cells will be confusing. |

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

## First time delivering this workshop?

Plan for 4-6 hours of focused prep, spread across at least two sittings. Most of that is reading and dry-running, not memorizing. The goal is to have already seen everything before your audience does.

### Day 1: Read and dry-run (about 3 hours)

Block off enough time to do this in one sitting if you can. Splitting it across days is fine; splitting it across more than two days breaks the continuity.

- [ ] Read this runbook end-to-end. Yes, including the tables. The tables are how you will actually use it during delivery.
- [ ] Read both approved slide decks straight through, including the speaker notes on each slide. The speaker notes are not a crutch; they cover each slide's topic in depth and are part of the material you are expected to know. Do not try to memorize talk-track yet. The goal here is to know the story arc.
- [ ] Skim both companion design docs in `docs/`: `notebook-plan-rag-to-agents.md` and the data fundamentals plan. These tell you *why* each notebook is structured the way it is, which makes the talk-track come more naturally.
- [ ] Open `notebooks/data_fundamentals_lab.ipynb` and run all cells in order against a known-good database. Watch what comes out of each cell. Do not skim.
- [ ] Open `notebooks/rag_to_agents_lab.ipynb` and do the same. The agent's first turn will take noticeably longer than the other cells; that is normal.

### Day 2: Practice and rehearse (about 2 hours)

- [ ] Walk through `data_fundamentals_lab.ipynb` again, this time saying out loud what each section is doing as if learners were in front of you. If you can record yourself or do this with a colleague, even better. You will catch the cells where you do not actually know what is happening.
- [ ] Do the same for `rag_to_agents_lab.ipynb`. Pay special attention to Section 5 (the agent loop); this is the section that benefits most from rehearsal.
- [ ] Practice the marquee moments specifically: the unified query in Data Fundamentals (Section 5) and the agent's first turn in RAG-to-Agents (Section 5). These are the payoff sections; the rest of the workshop is setup for these.
- [ ] Read the "Timing budget cheat sheet" and "Suggested cut lines" sections of this guide. You will not memorize them; the point is to know they exist so you can find them mid-session.

### Day 2 or Day 3: Break things on purpose (about 1 hour)

This is the step most new instructors skip. It is the most valuable hour of prep you will do. The goal is to see common failure modes in your own time so they are not surprises during delivery.

- [ ] In `rag_to_agents_lab.ipynb`, stop Ollama (or change `OLLAMA_BASE_URL` to a bad value) and re-run the Section 0 readiness probe. Confirm the failure message is clear. Restore.
- [ ] Change `OLLAMA_MODEL` to a model that is not installed. Re-run Section 0. Confirm the failure mode looks different from "Ollama is down."
- [ ] In either notebook, change the database connection settings to a bad value. Confirm the readiness check stops you before you have wasted time.
- [ ] Run `notebooks/rag_to_agents_reset.sql` and confirm the memory store goes back to empty.
- [ ] Look at one memory item directly in the database (`SELECT * FROM store_bridge`). Get comfortable with what the framework-managed tables actually look like, so when an audience member asks "what does that table contain," you can answer.

### Before your first session

After the prep above, the existing "Before the workshop" checklist covers what to do in the hour before learners join. Run through it every time, including your first; it is quick once you know the materials.

If something on the pre-workshop checklist surprises you, that is a signal you have not actually completed the first-time prep. Loop back rather than improvising on the day.

### What to do if you are getting paged in less than 24 hours

It happens. If you have less than a day before your first delivery:

- Skip the "break things on purpose" step (you will learn those by hitting them live; this is suboptimal but survivable).
- Skip rehearsing the talk-track out loud (you will wing it; lean harder on the approved deck for narrative).
- Do NOT skip the end-to-end dry-run of both notebooks. If you have never seen the notebooks run successfully, you cannot recover when they fail in front of an audience.
- Read the "Timing budget cheat sheet" and "Suggested cut lines" sections of this guide; you will need them.
