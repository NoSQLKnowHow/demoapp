export type ResponseMeta = {
  sql?: string | null;
  execution_time_ms?: number | null;
  operation_id?: string | null;
};

export type PrismResponse<T> = {
  data: T;
  meta: ResponseMeta;
};

export type District = {
  district_id: number;
  name: string;
  classification: string;
  population: number | null;
  area_sq_km: number | null;
  description: string | null;
};

export type Asset = {
  asset_id: number;
  district_id: number;
  name: string;
  asset_type: string;
  status: string | null;
  commissioned_date: string | null;
  description: string | null;
  specifications: Record<string, unknown> | null;
};

export type AssetDetail = Asset & {
  district_name: string | null;
  maintenance_log_count: number;
  inspection_report_count: number;
  connection_count: number;
};

export type MaintenanceLogSummary = {
  log_id: number;
  asset_id: number;
  asset_name: string | null;
  log_date: string | null;
  severity: string | null;
  narrative_preview: string | null;
};

export type MaintenanceLog = {
  log_id: number;
  asset_id: number;
  log_date: string | null;
  severity: string | null;
  narrative: string;
};

export type InspectionFinding = {
  finding_id: number;
  report_id: number;
  category: string | null;
  severity: string | null;
  description: string | null;
  recommendation: string | null;
};

export type InspectionReport = {
  report_id: number;
  asset_id: number;
  inspector: string | null;
  inspect_date: string | null;
  overall_grade: string | null;
  summary: string | null;
};

export type InspectionReportDetail = InspectionReport & {
  asset_name: string | null;
  findings: InspectionFinding[];
};

export type OperationalProcedure = Record<string, unknown>;

export type GraphNode = {
  asset_id: number;
  name: string;
  asset_type: string;
  status: string | null;
  district_id: number | null;
};

export type GraphEdge = {
  connection_id: number;
  from_asset_id: number;
  to_asset_id: number;
  connection_type: string | null;
  description: string | null;
};

export type GraphNeighborhood = {
  center: GraphNode;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type GraphPath = {
  path_length: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type VectorSearchResult = {
  chunk_id: number;
  source_table: string;
  source_id: number;
  chunk_text: string;
  similarity_score: number;
  asset_name: string | null;
  asset_id: number | null;
  log_date: string | null;
  severity: string | null;
};

export type PipelineStep = {
  step: string;
  sql: string;
};

export type IngestResult = {
  source_id: number;
  chunks_created: number;
  vectors_stored: number;
  pipeline_steps: PipelineStep[];
};

export type PrismUnifiedView = {
  relational: AssetDetail;
  json_document: Record<string, unknown> | null;
  graph: GraphNeighborhood | null;
  vector_results: VectorSearchResult[];
};

export type ApiErrorShape = {
  detail?: string;
  message?: string;
};
