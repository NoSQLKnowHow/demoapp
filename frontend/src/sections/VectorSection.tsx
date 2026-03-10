import { useState } from "react";

import ErrorState from "../components/ErrorState";
import LearnPanel from "../components/LearnPanel";
import { usePrismMutation } from "../hooks/usePrismQuery";
import type { PrismResponse, VectorSearchResult } from "../lib/types";

type VectorSearchPayload = {
  query: string;
  top_k: number;
  source_filter?: string | null;
  district_filter?: number | null;
  severity_filter?: string | null;
};

type KeywordSearchPayload = {
  query: string;
  limit: number;
};

function VectorSection() {
  const [query, setQuery] = useState("corrosion near water main");
  const [topK, setTopK] = useState(10);
  const [error, setError] = useState<string | null>(null);

  const vectorSearch = usePrismMutation<VectorSearchPayload, VectorSearchResult[]>({
    path: "/api/v1/vector/search",
  });

  const keywordSearch = usePrismMutation<KeywordSearchPayload, VectorSearchResult[]>({
    path: "/api/v1/vector/search/keyword",
  });

  const [vectorResults, setVectorResults] = useState<PrismResponse<VectorSearchResult[]> | null>(null);
  const [keywordResults, setKeywordResults] = useState<PrismResponse<VectorSearchResult[]> | null>(null);

  const handleSearch = async () => {
    setError(null);
    try {
      const [vectorResponse, keywordResponse] = await Promise.all([
        vectorSearch.mutateAsync({ query, top_k: topK }),
        keywordSearch.mutateAsync({ query, limit: topK }),
      ]);
      setVectorResults(vectorResponse);
      setKeywordResults(keywordResponse);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Vector search failed.";
      setError(message);
      setVectorResults(null);
      setKeywordResults(null);
    }
  };

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold text-slate-100">Vector search</h2>
        <p className="text-sm text-slate-400">
          Compare semantic search against keyword search using the same canonical dataset.
        </p>
      </header>

      <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[280px]">
            <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="vector-query">
              Query
            </label>
            <input
              id="vector-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="top-k">
              Top K
            </label>
            <input
              id="top-k"
              type="number"
              min={1}
              max={50}
              value={topK}
              onChange={(event) => setTopK(Number(event.target.value))}
              className="w-24 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
            />
          </div>
          <button
            type="button"
            className="self-end rounded-lg bg-prism-teal px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-400"
            onClick={handleSearch}
            disabled={vectorSearch.isPending || keywordSearch.isPending}
          >
            {vectorSearch.isPending || keywordSearch.isPending ? "Searching…" : "Run search"}
          </button>
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}

      <div className="grid gap-6 md:grid-cols-2">
        <SearchResults title="Semantic results" response={vectorResults} isLoading={vectorSearch.isPending} />
        <SearchResults title="Keyword results" response={keywordResults} isLoading={keywordSearch.isPending} />
      </div>
    </div>
  );
}

type SearchResultsProps = {
  title: string;
  response: PrismResponse<VectorSearchResult[]> | null;
  isLoading: boolean;
};

function SearchResults({ title, response, isLoading }: SearchResultsProps) {
  if (isLoading) {
    return (
      <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
        <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
        <p className="text-sm text-slate-400">Running query…</p>
      </section>
    );
  }

  if (!response) {
    return (
      <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
        <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
        <p className="text-sm text-slate-400">Run a search to see results.</p>
      </section>
    );
  }

  const results = response.data ?? [];

  if (results.length === 0) {
    return (
      <section className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
        <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
        <p className="text-sm text-slate-400">No matches found.</p>
      </section>
    );
  }

  return (
    <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-950/60 p-6">
      <div>
        <h3 className="text-lg font-semibold text-slate-100">{title}</h3>
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Similarity ranked</p>
      </div>
      <div className="space-y-4">
        {results.map((result) => (
          <article key={result.chunk_id} className="space-y-2 rounded-lg border border-slate-800 bg-slate-950/70 p-4">
            <header className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-slate-100">
                {result.source_table} · #{result.source_id}
              </p>
              <p className="text-xs text-prism-teal">Score: {result.similarity_score.toFixed(3)}</p>
            </header>
            <p className="text-sm text-slate-200">{result.chunk_text}</p>
            <dl className="grid gap-3 text-xs text-slate-400 md:grid-cols-3">
              <div>
                <dt className="uppercase tracking-[0.2em]">Asset</dt>
                <dd>{result.asset_name ?? "n/a"}</dd>
              </div>
              <div>
                <dt className="uppercase tracking-[0.2em]">Date</dt>
                <dd>{result.log_date ?? "n/a"}</dd>
              </div>
              <div>
                <dt className="uppercase tracking-[0.2em]">Severity</dt>
                <dd>{result.severity ?? "n/a"}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
      <LearnPanel meta={response.meta} title={`SQL used for ${title.toLowerCase()}`} />
    </section>
  );
}

export default VectorSection;
