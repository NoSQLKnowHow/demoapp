import { useMemo, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";

import ErrorState from "../components/ErrorState";
import LearnPanel from "../components/LearnPanel";
import { usePrismQuery } from "../hooks/usePrismQuery";
import type { GraphNeighborhood, PrismResponse } from "../lib/types";

const placeholderStyle = [{ selector: "node", style: { label: "data(label)" } }];

function GraphSection() {
  const [assetId, setAssetId] = useState<string>("");
  const neighborhoodQuery = usePrismQuery<GraphNeighborhood>({
    queryKey: ["graph-neighborhood", assetId],
    path: assetId ? `/api/v1/graph/assets/${assetId}/neighborhood` : "",
    enabled: Boolean(assetId),
  });

  const graphData = neighborhoodQuery.data?.data;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold text-slate-100">Graph projection</h2>
        <p className="text-sm text-slate-400">
          Visualize asset connectivity through Oracle SQL/PGQ. Choose an asset to fetch its neighborhood.
        </p>
      </header>

      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="mb-1 block text-xs uppercase tracking-[0.2em] text-slate-500" htmlFor="asset-id">
            Asset ID
          </label>
          <input
            id="asset-id"
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
            value={assetId}
            onChange={(event) => setAssetId(event.target.value)}
            placeholder="Enter an asset ID"
          />
        </div>
      </div>

      {neighborhoodQuery.isError ? (
        <ErrorState message={neighborhoodQuery.error.message} />
      ) : graphData ? (
        <GraphVisualization response={neighborhoodQuery.data} />
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-8 text-sm text-slate-400">
          Enter an asset ID to render its graph neighborhood.
        </div>
      )}

      <LearnPanel meta={neighborhoodQuery.data?.meta} title="Graph neighborhood query" />
    </div>
  );
}

type GraphVisualizationProps = {
  response: PrismResponse<GraphNeighborhood>;
};

function GraphVisualization({ response }: GraphVisualizationProps) {
  const neighborhood = response.data;

  const elements = useMemo(() => {
    const nodes = neighborhood.nodes.map((node) => ({
      data: { id: String(node.asset_id), label: node.name, type: node.asset_type },
    }));
    const edges = neighborhood.edges.map((edge) => ({
      data: {
        id: String(edge.connection_id),
        source: String(edge.from_asset_id),
        target: String(edge.to_asset_id),
        label: edge.connection_type,
      },
    }));
    return [...nodes, ...edges];
  }, [neighborhood]);

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-2">
        <CytoscapeComponent elements={elements} style={{ width: "100%", height: "480px" }} stylesheet={placeholderStyle} />
      </div>
      <p className="text-sm text-slate-400">
        Nodes represent infrastructure assets; edges show the physical connections between them. Learn Mode reveals the SQL/PGQ query used to populate this view.
      </p>
    </div>
  );
}

export default GraphSection;
