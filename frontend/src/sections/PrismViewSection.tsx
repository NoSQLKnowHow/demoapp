import { useState } from "react";

import ErrorState from "../components/ErrorState";
import LearnPanel from "../components/LearnPanel";
import { usePrismQuery } from "../hooks/usePrismQuery";
import type { PrismUnifiedView } from "../lib/types";

function PrismViewSection() {
  const [assetId, setAssetId] = useState<string>("");

  const query = usePrismQuery<PrismUnifiedView>({
    queryKey: ["prism-view", assetId],
    path: assetId ? `/api/v1/prism/assets/${assetId}/unified` : "",
    enabled: Boolean(assetId),
  });

  const unified = query.data?.data ?? null;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold text-slate-100">Prism view</h2>
        <p className="text-sm text-slate-400">
          Select an infrastructure asset to see relational, JSON, graph, and vector projections in one place.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="prism-asset">
            Asset ID
          </label>
          <input
            id="prism-asset"
            value={assetId}
            onChange={(event) => setAssetId(event.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
            placeholder="Enter asset ID"
          />
        </div>
      </div>

      {query.isError ? (
        <ErrorState message={query.error.message} />
      ) : query.isLoading ? (
        <p className="text-sm text-slate-400">Loading unified view…</p>
      ) : unified ? (
        <section className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
              <h3 className="text-lg font-semibold text-slate-100">Relational profile</h3>
              <pre className="overflow-x-auto rounded-lg bg-slate-950/80 p-4 text-xs text-slate-200">
                <code>{JSON.stringify(unified.relational, null, 2)}</code>
              </pre>
            </div>
            <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
              <h3 className="text-lg font-semibold text-slate-100">JSON Duality View</h3>
              <pre className="overflow-x-auto rounded-lg bg-slate-950/80 p-4 text-xs text-slate-200">
                <code>{JSON.stringify(unified.json_document ?? {}, null, 2)}</code>
              </pre>
            </div>
          </div>

          <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
            <h3 className="text-lg font-semibold text-slate-100">Vector highlights</h3>
            {unified.vector_results.length === 0 ? (
              <p className="text-sm text-slate-400">No vector matches yet for this asset.</p>
            ) : (
              <div className="space-y-3">
                {unified.vector_results.map((result) => (
                  <article key={result.chunk_id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-4">
                    <header className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-100">
                        {result.source_table} · #{result.source_id}
                      </p>
                      <p className="text-xs text-prism-teal">Score {result.similarity_score.toFixed(3)}</p>
                    </header>
                    <p className="mt-2 text-sm text-slate-200">{result.chunk_text}</p>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 text-sm text-slate-400">
          Enter an asset ID to see the unified projection.
        </div>
      )}

      <LearnPanel meta={query.data?.meta} title="Unified query orchestration" />
    </div>
  );
}

export default PrismViewSection;
