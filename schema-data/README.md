# PRISM Schema and Data Pipeline

This directory contains everything needed to build a fully-populated PRISM
database from scratch: schema DDL, sample data, vector embeddings, and the
glue scripts that wire it all together.

There are two pipelines, one for each setup:

- `adb/` — your own Oracle Autonomous Database (ADB) instance
- `free/` — Oracle Database 26ai Free (local Docker/Podman, or a LiveLabs sandbox)

Both pipelines load the same CityPulse data and produce the same end
state. They differ in user creation, password handling, and how the ONNX
embedding model gets wired up. Both use **live embedding**
(`prism-ingest.py`) to generate the vectors at load time. A faster
pre-built path (`prism-chunks-import.py`, loading `document_chunks.pkl`)
is available on ADB as an alternative; see below.

## Which pipeline should I use?

Use `free/` if you're running **Oracle Database 26ai Free**, either
locally in a Docker/Podman container or in a **LiveLabs workshop
sandbox** (LiveLabs hands you a 26ai Free instance, not ADB). You manage
the database, the connection details, and the model loading. Because
Free gives you filesystem access to the database server, you load the
ONNX model by copying it into the container with `docker cp`. Start with
`free/load-prism-database-free.md`: it is the complete, start-to-finish
guide, covering the ONNX model download, schema creation, seeding,
embedding, and indexing in one place.

Use `adb/` if you're running against your own **Oracle Autonomous
Database** instance. ADB has no filesystem access to the database
server, so the ONNX model is staged through OCI Object Storage and
pulled in with `DBMS_CLOUD.GET_OBJECT` rather than copied with
`docker cp`. Start with `adb/load-prism-database-adb.md`: it is the
complete, start-to-finish guide for the ADB setup.

---

## Directory layout

```
schema-data/
├── README.md                         (this file)
├── requirements.txt                  Python dependencies for both pipelines
├── .env                              Connection details and secrets (gitignored)
│
├── data/                             Shared pre-generated content
│   ├── maintenance_logs.json         308 LLM-generated maintenance narratives
│   ├── inspection_reports.json       60 LLM-generated reports (222 findings)
│   └── document_chunks.pkl           591 pre-chunked, pre-embedded chunks
│
├── prism-generate.py                 Regenerate the JSON content (one-time)
├── prism-chunks-export.py            Dump document_chunks to disk
├── prism-indexes.sql                 Create the HNSW vector index
├── prism-test-search.sql             Sanity-check the vector search
│
├── adb/                              Oracle Autonomous Database (ADB) pipeline
│   ├── load-prism-database-adb.md    End-to-end ADB setup guide (start here)
│   ├── prism-seed.py                 Loads sample data from data/*.json
│   ├── prism-ingest.py               Chunk + embed source rows (live embedding)
│   └── prism-chunks-import.py        Loads pre-built chunks from data/*.pkl (fast alternative)
│
└── free/                             Oracle 26ai Free pipeline
    ├── load-prism-database-free.md   End-to-end Free setup guide (start here)
    ├── prism-seed.py                 Loads sample data from data/*.json
    └── prism-ingest.py               Chunk + embed source rows (live embedding)
```

The `data/` directory is **shared** between both pipelines. Both `adb/` and
`free/` scripts look for it at `../data/` relative to themselves. Don't
duplicate the data files into either subdirectory.

---

## Embedding model

Everything in this pipeline is designed around a single ONNX embedding
model loaded into the database as `DEMO_MODEL`:

| Property | Value |
|---|---|
| Source model | `sentence-transformers/all-MiniLM-L12-v2` |
| In-database name | `DEMO_MODEL` |
| Vector dimensions | 384 |
| Distance metric | COSINE |

**If you use a different model**, the pre-built `document_chunks.pkl` is
useless. Embeddings are not portable across models — even small changes to
the architecture or training shift the vector space, and your similarity
search results will be meaningless. The import script catches the most
obvious case (wrong dimension count) and refuses to proceed, but two
384-dim models that are not the same model will fail silently with bad
results.

If you need a different model, regenerate the chunks via the fallback
path (see below) using whichever model you do have loaded.

---

## Prerequisites

For both pipelines:

- Python 3.10+ with the packages in `requirements.txt`
- A target database with the `VECTOR` type and `DBMS_VECTOR_CHAIN` package
  available (Oracle 23ai or 26ai)
- The `DEMO_MODEL` ONNX model loaded in the database (you load it
  yourself per the platform guide: `adb/load-prism-database-adb.md` or
  `free/load-prism-database-free.md`)

```bash
pip install -r requirements.txt
```

For the ADB pipeline specifically: a working `.env` with the connection
details for your ADB instance, plus an OCI Object Storage bucket you can
upload to and create a Pre-Authenticated Request (PAR) on. The ADB guide
walks through staging the ONNX model there.

For the Free pipeline: `ORACLE_DSN` (e.g., `localhost:1521/FREEPDB1`)
and `ORACLE_PASSWORD` in `.env`.

---

## Pipeline 1: Oracle Autonomous Database (ADB)

The ADB pipeline is documented end to end in **`adb/load-prism-database-adb.md`**.
Because ADB has no filesystem access to the database server, the guide
walks you through staging the ONNX model in OCI Object Storage and
pulling it into the database with `DBMS_CLOUD.GET_OBJECT`, then running
the schema DDL inlined in the guide. Open that guide and follow it start
to finish. The summary below is the shape of the process, not a
substitute for the guide.

The ADB pipeline uses **live embedding** (`prism-ingest.py`). The model
is loaded by `ADMIN` and exposed to PRISM through a grant and a public
synonym, so chunks are embedded at ingest time by calling `DEMO_MODEL`.

```bash
# 1. Stage the ONNX model in Object Storage and load it as DEMO_MODEL,
#    then create the user, schema, tables, views, graph, and JSON
#    Duality View, all per the guide.
#    (load-prism-database-adb.md, Steps 1-5)

# 2. Load the sample data into the source tables.
python adb/prism-seed.py

# 3. Chunk and embed the source rows live, writing to document_chunks.
python adb/prism-ingest.py

# 4. Build the HNSW vector index over the now-populated table.
sqlplus prism/$DBPASSWORD@$DBCONNECTION @prism-indexes.sql

# 5. (Optional) Sanity-check the vector search end-to-end.
sqlplus prism/$DBPASSWORD@$DBCONNECTION @prism-test-search.sql
```

### Fast alternative: skip live embedding

ADB ships `prism-chunks-import.py`, which loads the pre-built embeddings
from `document_chunks.pkl` in about a second instead of running the
several-minute live embedding in step 3. To use it, replace step 3 with:

```bash
python adb/prism-chunks-import.py
```

The pre-built chunks are only valid if the model loaded in your database
matches the one used to produce them (384-dim `DEMO_MODEL`); see
"Embedding model" above. When the import finishes, its data-consistency
diagnostics list any source rows without chunks attached (informational)
and any chunks pointing at missing source rows (should always be zero).

---

## Pipeline 2: Oracle Database 26ai Free

The Free pipeline is documented end to end in **`free/load-prism-database-free.md`**.
The guide walks you through each step interactively, because
the ONNX model download and the `docker cp` into the container are
manual, host-specific actions. Open that guide and follow it start to
finish. The summary below is the shape of the process, not a substitute
for the guide.

The Free pipeline uses **live vector embedding** (`prism-ingest.py`). The model
is owned directly by the PRISM user as `DEMO_MODEL`, so chunks are embedded
at ingest time.

```bash
# 1. Download the Oracle-augmented ONNX model and copy it into the
#    running container, then load it as DEMO_MODEL into the PRISM schema.
#    (load-prism-database-free.md, Steps 1-4)

# 2. Create the user, schema, tables, views, graph, and JSON Duality View
#    by running the DDL inlined in the guide as the PRISM user.
#    (load-prism-database-free.md, Step 5)

# 3. Load the sample data into the source tables.
python free/prism-seed.py

# 4. Chunk and embed the source rows live, writing to document_chunks.
python free/prism-ingest.py

# 5. Build the HNSW vector index over the now-populated table.
sqlplus prism/$ORACLE_PASSWORD@$ORACLE_DSN @prism-indexes.sql

# 6. (Optional) Sanity-check the vector search end-to-end.
sqlplus prism/$ORACLE_PASSWORD@$ORACLE_DSN @prism-test-search.sql
```

Because Free embeds at ingest time, step 4 is the slow step (several
minutes for ~591 chunks). Free has no pre-built `.pkl` import path: it
always embeds live, working against whatever model you have loaded. (ADB
can optionally skip live embedding via `prism-chunks-import.py`; Free
cannot, since the model lives only in your container.)

Whether you run locally or in a LiveLabs 26ai Free sandbox, the database
lives close to where you run these scripts, so the non-embedding steps
are quick. The live embedding in step 4 is the one part that takes real
time.

---

## Why we ship pre-generated content

Two of the four files in `data/` are LLM output, and one is the result of
a chunking-and-embedding pipeline. Both are checked into git rather than
regenerated each time. Here's why.

### Pre-generated narratives (`maintenance_logs.json`, `inspection_reports.json`)

These are produced by `prism-generate.py`, which calls an LLM (OCI
Generative AI, Anthropic Claude, or OpenAI depending on the
`LLM_PROVIDER` env var) to generate ~300 maintenance log narratives and
~60 inspection reports across the CityPulse infrastructure assets.

Reasons to pre-generate and check in:

1. **Cost.** A single run of `prism-generate.py` makes ~30 LLM calls
   producing ~50k tokens of output. At GPT-4o or Claude rates that's a
   few dollars per run. Multiply by every developer rebuilding their
   database and the numbers add up fast.

2. **Time.** Generation takes 5-10 minutes depending on the provider.
   Loading the JSON files takes seconds.

3. **Reproducibility.** Every developer's database has the same data.
   Bug reports become reproducible because "the Harbor Bridge
   maintenance log about vibration" means the same narrative for
   everyone.

4. **No API keys required.** Workshop attendees and external developers
   don't need an LLM provider account to spin up a working database.

`prism-generate.py` is still here for the rare case where you want to
regenerate the dataset with different narratives, a different LLM, or
different prompts. Run it once, commit the new JSON files, and everyone
who pulls picks up the new content.

### Pre-generated chunks and embeddings (`document_chunks.pkl`)

These are produced by `prism-chunks-export.py` running against an
already-populated database (i.e., one that has gone through `prism-seed.py`
*and* `prism-ingest.py`). The export captures each chunk's text, its
pre-computed embedding, and a natural key that lets us rejoin it to the
right source row in a freshly-seeded target database.

Reasons to pre-generate and check in:

1. **Speed.** The bottleneck in `prism-ingest.py` is the embedding step.
   Each chunk requires tokenization, a forward pass through the ONNX
   model, and a vector write. For ~590 chunks this takes several minutes
   on ADB. Loading them from a pre-built `.pkl` takes about one second.

2. **Determinism.** ONNX runtime is not bit-for-bit deterministic across
   hardware. Two databases running `prism-ingest.py` on the same source
   data can produce slightly different vectors. Pre-generated chunks
   guarantee everyone's database is identical.

3. **No model dependency at load time.** The import script does verify
   that `DEMO_MODEL` exists in the target (so query-time embedding works)
   and that dimensions match (so the vectors are usable), but it does
   not need the model to *generate* anything. This makes the import
   step more forgiving across environments.

### When to use `prism-ingest.py`

Live embedding is the **default** path on both ADB and Free (the
platform guides walk you through it). The pre-built `.pkl` import is only
an optional fast alternative on ADB. Run live ingest when:

- You're using a different embedding model.
- You've regenerated the JSON content and the pre-built chunks are stale.
- You've added a new maintenance log or inspection report through the
  Prism API and want it indexed.

`prism-ingest.py` is idempotent: each ingest function filters source
rows that already have chunks attached, so re-running only processes
the delta. Just expect it to be slower than the `.pkl` import.

---

## Common issues

**`ORA-00942: table or view "ADMIN"."DEMO_MODEL" does not exist`** when
granting access to the model on ADB. Mining models need
`GRANT MINING MODEL SELECT ON ...`, not the regular `GRANT SELECT`. The
ADB guide (`adb/load-prism-database-adb.md`) issues the correct grant.

**`Embedding model 'DEMO_MODEL' not loaded in target database`** when
running `prism-chunks-import.py` (the ADB fast alternative). The script
checks for the model in the data dictionary. On ADB the model is owned
by `ADMIN` and PRISM sees it through the public synonym, so confirm the
grant and synonym from the ADB guide ran, and that the model resolves
via `all_mining_models`.

**`Vector dimension mismatch`** when running `prism-chunks-import.py`
(the ADB fast alternative). The model loaded in the target produces a
different number of dimensions than the model used to produce the
export. Use a 384-dimension model (see "Embedding model" above) or embed
live with `prism-ingest.py` instead.

**`ORA-32044: cycle detected while executing recursive WITH query`**
elsewhere in the codebase, when doing graph traversal. Use Python-side
BFS over an adjacency list instead of recursive CTEs. CityPulse asset
connections are bidirectional, which trips up Oracle's cycle detection.

---

## Regenerating the pre-built files

Once in a while you may want to regenerate the data files from scratch.

```bash
# Regenerate the LLM-authored content.
# Requires LLM provider credentials in .env.
python prism-generate.py

# Build the database from scratch using the live-embedding path.
#   ADB:  follow adb/load-prism-database-adb.md   then   python adb/prism-seed.py
#   Free: follow free/load-prism-database-free.md  then   python free/prism-seed.py
# Then run the matching ingest script (NOT prism-chunks-import.py):
python adb/prism-ingest.py   # or: python free/prism-ingest.py

# Export the freshly-ingested chunks for future fast loads.
python prism-chunks-export.py

# Commit the updated files.
git add data/maintenance_logs.json data/inspection_reports.json data/document_chunks.pkl
git commit -m "Regenerate PRISM dataset"
```

The whole regeneration cycle takes 15-20 minutes including LLM calls.
After that, every subsequent database rebuild is back to the
seconds-not-minutes fast path.
