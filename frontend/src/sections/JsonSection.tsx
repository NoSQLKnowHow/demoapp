import { useMemo, useState } from "react";

import ErrorState from "../components/ErrorState";
import LearnPanel from "../components/LearnPanel";
import { usePrismQuery } from "../hooks/usePrismQuery";
import type { PrismResponse } from "../lib/types";

const PROCEDURE_CATEGORIES = ["electrical", "structural", "emergency", "pipeline"];

type ProcedureDocument = Record<string, unknown> & {
  procedureId?: string;
  title?: string;
  category?: string;
  _id?: number | string;
};

function JsonSection() {
  const [category, setCategory] = useState<string>("");
  const [keyword, setKeyword] = useState<string>("");
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);

  const inspectionsQuery = usePrismQuery<ProcedureDocument[]>({
    queryKey: ["json-inspections"],
    path: "/api/v1/json/inspections",
  });

  const procedurePath = useMemo(() => {
    const params = new URLSearchParams();
    if (category) {
      params.set("category", category);
    }
    if (keyword) {
      params.set("keyword", keyword);
    }
    const queryString = params.toString();
    return `/api/v1/json/procedures${queryString ? `?${queryString}` : ""}`;
  }, [category, keyword]);

  const proceduresQuery = usePrismQuery<ProcedureDocument[]>({
    queryKey: ["json-procedures", category, keyword],
    path: procedurePath,
  });

  const mongoPath = useMemo(() => {
    const params = new URLSearchParams();
    if (category) {
      params.set("category", category);
    }
    if (keyword) {
      params.set("keyword", keyword);
    }
    const queryString = params.toString();
    return `/api/v1/json/procedures/mongodb${queryString ? `?${queryString}` : ""}`;
  }, [category, keyword]);

  const mongoQuery = usePrismQuery<ProcedureDocument[]>({
    queryKey: ["json-procedures-mongo", category, keyword],
    path: mongoPath,
    enabled: false,
  });

  const inspectionDetailQuery = usePrismQuery<ProcedureDocument>({
    queryKey: ["json-inspection", selectedReportId],
    path: selectedReportId ? `/api/v1/json/inspections/${selectedReportId}` : "",
    enabled: Boolean(selectedReportId),
  });

  const inspections = inspectionsQuery.data?.data ?? [];
  const procedures = proceduresQuery.data?.data ?? [];

  return (
    <div className="space-y-12">
      <section className="space-y-4">
        <header>
          <h2 className="text-2xl font-semibold text-slate-100">JSON projections</h2>
          <p className="text-sm text-slate-400">
            Examine Duality View documents alongside native JSON collections. Switch to Learn Mode to see the SQL and pymongo code used behind the scenes.
          </p>
        </header>
        {inspectionsQuery.isError ? (
          <ErrorState message={inspectionsQuery.error.message} />
        ) : (
          <JsonDocumentList
            documents={inspections}
            title="Inspection reports (JSON Duality View)"
            onSelect={(doc) => {
              const id = typeof doc?._id === "number" ? doc._id : Number(doc?._id);
              if (!Number.isNaN(id)) {
                setSelectedReportId(id);
              }
            }}
          />
        )}
        <LearnPanel meta={inspectionsQuery.data?.meta} title="Duality View query" />
      </section>

      {inspectionDetailQuery.isLoading ? (
        <p className="text-sm text-slate-400">Loading inspection detail…</p>
      ) : inspectionDetailQuery.isError ? (
        <ErrorState message={inspectionDetailQuery.error.message} />
      ) : inspectionDetailQuery.data ? (
        <JsonDocumentViewer title="Inspection detail" response={inspectionDetailQuery.data} />
      ) : null}

      <section className="space-y-6">
        <header className="flex flex-wrap items-end gap-4">
          <div>
            <h3 className="text-xl font-semibold text-slate-100">Operational procedures</h3>
            <p className="text-sm text-slate-400">Same JSON collection, queried via SQL and MongoDB API.</p>
          </div>
          <div className="flex gap-3">
            <div>
              <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="category">
                Category
              </label>
              <select
                id="category"
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
              >
                <option value="">All</option>
                {PROCEDURE_CATEGORIES.map((categoryOption) => (
                  <option key={categoryOption} value={categoryOption}>
                    {categoryOption}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="keyword">
                Keyword
              </label>
              <input
                id="keyword"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="thermal, bridge, leak…"
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
              />
            </div>
            <button
              type="button"
              className="self-end rounded-lg border border-prism-teal/40 px-3 py-2 text-xs font-semibold text-prism-teal hover:bg-prism-teal/10"
              onClick={() =>
                mongoQuery.refetch().catch(() => {
                  // errors surface via React Query
                })
              }
              disabled={mongoQuery.isFetching}
            >
              {mongoQuery.isFetching ? "Running…" : "Compare with MongoDB API"}
            </button>
          </div>
        </header>

        {proceduresQuery.isError ? (
          <ErrorState message={proceduresQuery.error.message} />
        ) : (
          <JsonDocumentList documents={procedures} title="Operational procedures (SQL)" />
        )}
        <LearnPanel meta={proceduresQuery.data?.meta} title="SQL against JSON collection" />

        {mongoQuery.isLoading ? <p className="text-sm text-slate-400">Running pymongo query…</p> : null}
        {mongoQuery.isError ? <ErrorState message={mongoQuery.error.message} /> : null}
        {mongoQuery.data ? (
          <LearnPanel meta={mongoQuery.data.meta} title="pymongo comparison">
            <p className="text-sm text-slate-300">
              The MongoDB API returned {mongoQuery.data.data.length} documents. The Learn Mode panel above shows both the pymongo code and equivalent SQL.
            </p>
          </LearnPanel>
        ) : null}
      </section>
    </div>
  );
}

type JsonDocumentListProps = {
  documents: ProcedureDocument[];
  title: string;
  onSelect?: (document: ProcedureDocument) => void;
};

function JsonDocumentList({ documents, title, onSelect }: JsonDocumentListProps) {
  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
      <div className="grid gap-4 md:grid-cols-2">
        {documents.map((doc, index) => (
          <button
            key={doc.procedureId ?? doc._id ?? index}
            type="button"
            onClick={() => onSelect?.(doc)}
            className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-left transition hover:border-prism-teal/50 hover:bg-slate-900/60"
          >
            <p className="text-sm font-semibold text-slate-100">{doc.title ?? doc.procedureId ?? `Document ${index + 1}`}</p>
            <p className="mt-1 text-xs text-slate-400">Category: {doc.category ?? "n/a"}</p>
            <p className="mt-2 line-clamp-3 text-sm text-slate-300">{JSON.stringify(doc).slice(0, 180)}…</p>
          </button>
        ))}
        {documents.length === 0 ? (
          <p className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
            No documents match the current filters.
          </p>
        ) : null}
      </div>
    </div>
  );
}

type JsonDocumentViewerProps = {
  title: string;
  response: PrismResponse<ProcedureDocument>;
};

function JsonDocumentViewer({ title, response }: JsonDocumentViewerProps) {
  const document = response.data;

  return (
    <section className="space-y-4">
      <header>
        <h3 className="text-xl font-semibold text-slate-100">{title}</h3>
        <p className="text-sm text-slate-400">Rendered directly from the Duality View document payload.</p>
      </header>
      <pre className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/70 p-6 text-xs text-slate-200">
        <code>{JSON.stringify(document, null, 2)}</code>
      </pre>
      <LearnPanel meta={response.meta} title="Duality View detail query" />
    </section>
  );
}

export default JsonSection;
