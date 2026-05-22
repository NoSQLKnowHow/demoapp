# PRISM Schema and Data Pipeline

This directory contains everything needed to build a fully-populated PRISM
database from scratch: schema DDL, sample data, vector embeddings, and the
glue scripts that wire it all together.

There are two pipelines, one for each setup:

- `adb/` — Oracle Autonomous Database (ADB) in a LiveLabs sandbox
- `free/` — Oracle Database 26ai Free that you set up yourself

Both pipelines load the same CityPulse data and produce the same end
state. They differ in user creation, password handling, how the ONNX
embedding model gets wired up, and how the vector embeddings are
produced: ADB loads pre-built embeddings from `document_chunks.pkl`
(fast), while Free generates them live with `prism-ingest.py`.

## Which pipeline should I use?

Use `adb/` if you're running inside a **LiveLabs workshop sandbox**
backed by ADB. LiveLabs provisions the ADB instance and an `ADMIN`
user, places connection details in `variable.sh`, and pre-loads the
`DEMO_MODEL` ONNX model. The shell script in `adb/` is the entry point
that LiveLabs typically invokes for the workshop's database-build step.

Use `free/` if you're running **Oracle Database 26ai Free** that you
set up yourself — either locally in a Docker/Podman container, or in a
LiveLabs sandbox that hands you a 26ai Free instance. In both cases you
manage the database, the connection details, and the model loading.
Start with `free/load_onnx_model.md`: it is the complete, start-to-finish
guide for the Free setup, covering the ONNX model download, schema
creation, seeding, embedding, and indexing in one place.

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
├── adb/                              LiveLabs (ADB) pipeline
│   ├── shell_script.sh               Driver: connects as ADMIN, runs SQL
│   ├── prism-setup1.sql              Creates PRISM user, grants, synonyms
│   ├── prism-setup2.sql              Creates tables, views, graph, JSON DV
│   ├── prism-seed.py                 Loads sample data from data/*.json
│   ├── prism-ingest.py               Chunk + embed source rows (fallback path)
│   └── prism-chunks-import.py        Loads pre-built chunks from data/*.pkl
│
└── free/                             Oracle 26ai Free pipeline
    ├── load_onnx_model.md            End-to-end Free setup guide (start here)
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
- The `DEMO_MODEL` ONNX model loaded in the database (on ADB it is
  pre-loaded by LiveLabs; on Free you load it yourself per
  `free/load_onnx_model.md`)

```bash
pip install -r requirements.txt
```

For the ADB pipeline specifically: a working `.env` (or `variable.sh`)
with `DBCONNECTION` and `DBPASSWORD` set. Both the shell phase and the
Python phase use this single pair. This matches what LiveLabs provisions
automatically, so the ADB pipeline runs in LiveLabs sandboxes without
additional configuration.

For the Free pipeline: `ORACLE_DSN` (e.g., `localhost:1521/FREEPDB1`)
and `ORACLE_PASSWORD` in `.env`.

---

## Pipeline 1: LiveLabs (ADB)

Run these in order, from `schema-data/`:

```bash
# 1. Create the user, schema, tables, views, graph, and JSON Duality View.
#    Connects as ADMIN, runs prism-setup1.sql then prism-setup2.sql.
./adb/shell_script.sh

# 2. Load the sample data into the source tables.
#    Reads ../data/maintenance_logs.json and ../data/inspection_reports.json.
python adb/prism-seed.py

# 3. Load the pre-built chunks and embeddings.
#    Reads ../data/document_chunks.pkl (or .json.gz if that's all that's there).
python adb/prism-chunks-import.py

# 4. Build the HNSW vector index over the now-populated table.
sqlcl admin/$DBPASSWORD@$DBCONNECTION @prism-indexes.sql

# 5. (Optional) Sanity-check the vector search end-to-end.
sqlcl prism/$DBPASSWORD@$DBCONNECTION @prism-test-search.sql
```

When step 3 finishes, the data-consistency diagnostics will list any
source rows without chunks attached, and any chunks pointing at missing
source rows. The first category is informational (means the data files
got out of sync with the chunks export at some point); the second
should always be zero and means something is wrong if it isn't.

---

## Pipeline 2: Oracle Database 26ai Free

The Free pipeline is documented end to end in **`free/load_onnx_model.md`**.
Unlike ADB, it has no shell-script driver and no single combined setup
SQL file: the guide walks you through each step interactively, because
the ONNX model download and the `docker cp` into the container are
manual, host-specific actions. Open that guide and follow it start to
finish. The summary below is the shape of the process, not a substitute
for the guide.

The Free pipeline uses **live embedding** (`prism-ingest.py`) rather than
the pre-built `.pkl` import. The model is owned directly by the PRISM
user as `DEMO_MODEL`, so chunks are embedded at ingest time.

```bash
# 1. Download the Oracle-augmented ONNX model and copy it into the
#    running container, then load it as DEMO_MODEL into the PRISM schema.
#    (load_onnx_model.md, Steps 1-4)

# 2. Create the user, schema, tables, views, graph, and JSON Duality View
#    by running the DDL inlined in the guide as the PRISM user.
#    (load_onnx_model.md, Step 5)

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
minutes for ~591 chunks) rather than the one-second `.pkl` import the
ADB pipeline uses. The trade-off is that the Free path needs no
pre-built export and works against whatever model you have loaded.

Whether you run locally or in a LiveLabs 26ai Free sandbox, the database
lives close to where you run these scripts (no ADB network hop), so the
non-embedding steps are quick. The live embedding in step 4 is the one
part that takes real time.

---

## Why we ship pre-generated content

Two of the four files in `data/` are LLM output, and one is the result of
a chunking-and-embedding pipeline. Both are checked into git rather than
regenerated each time. Here's why.

### Pre-generated narratives (`maintenance_logs.json`, `inspection_reports.json`)

These are produced by `prism-generate.py`, which calls an LLM (OCI
Generative AI, Anthropic Claude, or OpenAI depending on the
`LLM_PROVIDER` env var) to generate ~300 maintenance log narratives and
~60 inspection reports across the 27 CityPulse infrastructure assets.

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

### When to use `prism-ingest.py` instead

On ADB this is the fallback path (the default is the fast `.pkl`
import). On Free it is the **primary** path. Either way, run it when:

- You're using a different embedding model.
- You've regenerated the JSON content and the pre-built chunks are stale.
- You've added a new maintenance log or inspection report through the
  Prism API and want it indexed.

`prism-ingest.py` is idempotent: each ingest function filters source
rows that already have chunks attached, so re-running only processes
the delta. Just expect it to be slower than the import path.

---

## Common issues

**`ORA-00942: table or view "ADMIN"."DEMO_MODEL" does not exist`** when
running `GRANT SELECT ON ADMIN.DEMO_MODEL TO prism`. Mining models need
`GRANT MINING MODEL SELECT ON ...`, not the regular `GRANT SELECT`.
`prism-setup1.sql` already does this on ADB.

**`Embedding model 'DEMO_MODEL' not loaded in target database`** when
running `prism-chunks-import.py`. The script checks `user_mining_models`
for the model. If the model is owned by a different schema (e.g., ADMIN
on ADB), PRISM sees it only via the public synonym, which doesn't appear
in `user_mining_models`. Either change the script to query
`all_mining_models`, or load `DEMO_MODEL` directly into the PRISM schema.

**`Vector dimension mismatch`** when running `prism-chunks-import.py`.
The model loaded in the target produces a different number of dimensions
than the model used to produce the export. Use a 384-dimension model
(see "Embedding model" above) or regenerate the chunks via the fallback
path.

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

# Build the database from scratch using the slow path, including
# embedding generation at load time.
#   ADB:  ./adb/shell_script.sh   then   python adb/prism-seed.py
#   Free: follow free/load_onnx_model.md   then   python free/prism-seed.py
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
