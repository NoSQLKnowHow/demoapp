import { useEffect, useMemo, useState } from "react";

import DataTable, { type TableColumn } from "../components/DataTable";
import ErrorState from "../components/ErrorState";
import LearnPanel from "../components/LearnPanel";
import { usePrismQuery } from "../hooks/usePrismQuery";
import type {
  Asset,
  AssetDetail,
  District,
  MaintenanceLogSummary,
  PrismResponse,
} from "../lib/types";

function RelationalSection() {
  const [selectedDistrict, setSelectedDistrict] = useState<number | "">("");
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);

  const districtsQuery = usePrismQuery<District[]>({
    queryKey: ["districts"],
    path: "/api/v1/relational/districts",
  });

  const districtOptions = districtsQuery.data?.data ?? [];

  const districtLookup = useMemo(() => {
    return new Map(districtOptions.map((district) => [district.district_id, district.name]));
  }, [districtOptions]);

  const assetPath = useMemo(() => {
    const params = new URLSearchParams();
    if (selectedDistrict !== "") {
      params.set("district_id", String(selectedDistrict));
    }
    const queryString = params.toString();
    return `/api/v1/relational/assets${queryString ? `?${queryString}` : ""}`;
  }, [selectedDistrict]);

  const assetsQuery = usePrismQuery<Asset[]>({
    queryKey: ["assets", selectedDistrict],
    path: assetPath,
  });

  const assets = assetsQuery.data?.data ?? [];

  useEffect(() => {
    if (assets.length === 0) {
      setSelectedAssetId(null);
      return;
    }
    setSelectedAssetId((current) => {
      if (current && assets.some((asset) => asset.asset_id === current)) {
        return current;
      }
      return assets[0].asset_id;
    });
  }, [assets]);

  const assetDetailQuery = usePrismQuery<AssetDetail>({
    queryKey: ["asset-detail", selectedAssetId],
    path: selectedAssetId ? `/api/v1/relational/assets/${selectedAssetId}` : "",
    enabled: Boolean(selectedAssetId),
  });

  const maintenanceLogsQuery = usePrismQuery<MaintenanceLogSummary[]>({
    queryKey: ["maintenance-logs", selectedAssetId],
    path: selectedAssetId ? `/api/v1/relational/maintenance-logs?asset_id=${selectedAssetId}` : "",
    enabled: Boolean(selectedAssetId),
  });

  const assetColumns: TableColumn<Asset>[] = useMemo(
    () => [
      {
        key: "name",
        header: "Asset",
        render: (row) => (
          <div>
            <p className="font-medium text-slate-100">{row.name}</p>
            <p className="text-xs text-slate-400">{row.asset_type}</p>
          </div>
        ),
      },
      {
        key: "district",
        header: "District",
        render: (row) => districtLookup.get(row.district_id) ?? row.district_id,
      },
      {
        key: "status",
        header: "Status",
        render: (row) => row.status ?? "—",
      },
      {
        key: "commissioned",
        header: "Commissioned",
        render: (row) => row.commissioned_date ?? "—",
      },
    ],
    [districtLookup],
  );

  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <header>
          <h2 className="text-2xl font-semibold text-slate-100">Relational projection</h2>
          <p className="text-sm text-slate-400">
            Query the canonical CityPulse tables. Filter by district and inspect assets backed by JSON columns.
          </p>
        </header>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.2em] text-slate-400" htmlFor="district">
              District
            </label>
            <select
              id="district"
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-prism-teal focus:outline-none"
              value={selectedDistrict}
              onChange={(event) => {
                const value = event.target.value;
                setSelectedDistrict(value === "" ? "" : Number(value));
                setSelectedAssetId(null);
              }}
            >
              <option value="">All districts</option>
              {districtOptions.map((district) => (
                <option key={district.district_id} value={district.district_id}>
                  {district.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        {assetsQuery.isError ? (
          <ErrorState message={assetsQuery.error.message} />
        ) : (
          <div>
            <DataTable
              data={assets}
              columns={assetColumns}
              emptyMessage={assetsQuery.isLoading ? "Loading assets…" : "No assets found."}
              getRowKey={(item) => item.asset_id}
              onRowClick={(item) => setSelectedAssetId(item.asset_id)}
              getRowClassName={(item) => (item.asset_id === selectedAssetId ? "bg-prism-teal/10" : "")}
            />
            <p className="mt-2 text-xs text-slate-500">
              Click an asset row to view details and recent maintenance activity.
            </p>
          </div>
        )}
        <LearnPanel meta={assetsQuery.data?.meta} />
      </section>

      {selectedAssetId ? null : (
        <div className="text-sm text-slate-400">
          Select an asset to drill into maintenance history, specifications, and inspection rollups.
        </div>
      )}

      <section>
        <div className="space-y-6">
          <header className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-slate-100">Asset detail</h3>
            <div className="text-sm text-slate-400">
              {selectedAssetId ? `Asset ID ${selectedAssetId}` : "Choose an asset above."}
            </div>
          </header>

          {selectedAssetId ? (
            <div className="space-y-6">
              {assetDetailQuery.isError ? (
                <ErrorState message={assetDetailQuery.error.message} />
              ) : assetDetailQuery.isLoading ? (
                <p className="text-sm text-slate-400">Loading asset detail…</p>
              ) : assetDetailQuery.data ? (
                <AssetDetailCard response={assetDetailQuery.data} />
              ) : null}

              <LearnPanel meta={assetDetailQuery.data?.meta} title="SQL driving the asset detail view" />

              <div className="space-y-3">
                <h4 className="text-lg font-semibold text-slate-100">Recent maintenance logs</h4>
                {maintenanceLogsQuery.isError ? (
                  <ErrorState message={maintenanceLogsQuery.error.message} />
                ) : maintenanceLogsQuery.isLoading ? (
                  <p className="text-sm text-slate-400">Fetching maintenance history…</p>
                ) : (
                  <MaintenanceLogsList response={maintenanceLogsQuery.data} />
                )}
                <LearnPanel meta={maintenanceLogsQuery.data?.meta} title="Maintenance log query" />
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}

function AssetDetailCard({ response }: { response: PrismResponse<AssetDetail> }) {
  const asset = response.data;

  return (
    <div className="grid gap-6 rounded-xl border border-slate-800 bg-slate-950/40 p-6 md:grid-cols-2">
      <div className="space-y-4">
        <h4 className="text-lg font-semibold text-slate-100">Profile</h4>
        <div className="space-y-3 text-sm text-slate-300">
          <DetailRow label="Name" value={asset.name} />
          <DetailRow label="District" value={asset.district_name ?? asset.district_id} />
          <DetailRow label="Type" value={asset.asset_type} />
          <DetailRow label="Status" value={asset.status ?? "—"} />
          <DetailRow label="Commissioned" value={asset.commissioned_date ?? "—"} />
        </div>
      </div>
      <div className="space-y-4">
        <h4 className="text-lg font-semibold text-slate-100">Activity overview</h4>
        <div className="grid grid-cols-3 gap-4 text-sm text-slate-300">
          <StatBlock label="Maintenance logs" value={asset.maintenance_log_count} />
          <StatBlock label="Inspection reports" value={asset.inspection_report_count} />
          <StatBlock label="Graph connections" value={asset.connection_count} />
        </div>
        <div>
          <h5 className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">Specifications</h5>
          <pre className="overflow-x-auto rounded-lg bg-slate-950/80 p-4 text-xs text-slate-200">
            <code>{JSON.stringify(asset.specifications ?? {}, null, 2)}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}

function MaintenanceLogsList({ response }: { response: PrismResponse<MaintenanceLogSummary[]> | undefined }) {
  const logs = response?.data ?? [];

  if (logs.length === 0) {
    return <p className="text-sm text-slate-400">No maintenance activity recorded for this asset in the current window.</p>;
  }

  return (
    <div className="space-y-3">
      {logs.map((log) => (
        <div key={log.log_id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm font-semibold text-slate-100">Log {log.log_id}</div>
            <div className="text-xs uppercase tracking-[0.2em] text-slate-400">
              {log.log_date ?? "Undated"}
            </div>
          </div>
          <div className="mt-2 text-xs text-prism-teal">Severity: {log.severity ?? "n/a"}</div>
          <p className="mt-3 text-sm text-slate-200">{log.narrative_preview ?? "(No preview available)"}</p>
        </div>
      ))}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="text-sm text-slate-200">{value}</p>
    </div>
  );
}

function StatBlock({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4 text-center">
      <p className="text-2xl font-semibold text-slate-100">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
    </div>
  );
}

export default RelationalSection;
