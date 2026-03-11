"""
Pydantic models for API request and response schemas.

All API responses use the PrismResponse envelope, which includes an
optional 'meta' block for Learn Mode content (SQL text, execution time,
operation ID).
"""

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BeforeValidator


def _to_date(v):
    """Coerce datetime to date for Oracle DATE columns that include time."""
    if isinstance(v, datetime):
        return v.date()
    return v


CoerceDate = Annotated[date | None, BeforeValidator(_to_date)]

from pydantic import BaseModel, Field


# ============================================================================
# Response Envelope
# ============================================================================

class ResponseMeta(BaseModel):
    """Metadata block included in all API responses."""
    sql: str | None = Field(None, description="SQL text executed (Learn Mode only)")
    execution_time_ms: float | None = Field(None, description="Query execution time in milliseconds")
    operation_id: str | None = Field(None, description="Operation identifier for meta lookups")


class PrismResponse(BaseModel):
    """Standard response envelope for all Prism API endpoints."""
    data: Any
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


# ============================================================================
# Domain Models: Districts
# ============================================================================

class District(BaseModel):
    district_id: int
    name: str
    classification: str
    population: int | None = None
    area_sq_km: float | None = None
    description: str | None = None


# ============================================================================
# Domain Models: Infrastructure Assets
# ============================================================================

class Asset(BaseModel):
    asset_id: int
    district_id: int
    name: str
    asset_type: str
    status: str | None = "active"
    commissioned_date: CoerceDate = None
    description: str | None = None
    specifications: dict | None = None


class AssetDetail(Asset):
    """Asset with related data included."""
    district_name: str | None = None
    maintenance_log_count: int = 0
    inspection_report_count: int = 0
    connection_count: int = 0


# ============================================================================
# Domain Models: Maintenance Logs
# ============================================================================

class MaintenanceLog(BaseModel):
    log_id: int
    asset_id: int
    log_date: CoerceDate = None
    severity: str | None = None
    narrative: str


class MaintenanceLogSummary(BaseModel):
    """Maintenance log without the full narrative, for list views."""
    log_id: int
    asset_id: int
    asset_name: str | None = None
    log_date: CoerceDate = None
    severity: str | None = None
    narrative_preview: str | None = None


# ============================================================================
# Domain Models: Inspection Reports
# ============================================================================

class InspectionFinding(BaseModel):
    finding_id: int
    report_id: int
    category: str | None = None
    severity: str | None = None
    description: str | None = None
    recommendation: str | None = None


class InspectionReport(BaseModel):
    report_id: int
    asset_id: int
    inspector: str | None = None
    inspect_date: CoerceDate = None
    overall_grade: str | None = None
    summary: str | None = None


class InspectionReportDetail(InspectionReport):
    """Report with findings included."""
    asset_name: str | None = None
    findings: list[InspectionFinding] = []


# ============================================================================
# Domain Models: Connections
# ============================================================================

class AssetConnection(BaseModel):
    connection_id: int
    from_asset_id: int
    to_asset_id: int
    connection_type: str | None = None
    description: str | None = None
    from_asset_name: str | None = None
    to_asset_name: str | None = None


# ============================================================================
# Domain Models: Operational Procedures
# ============================================================================

class OperationalProcedure(BaseModel):
    """Operational procedure from the JSON collection table."""
    data: dict


# ============================================================================
# Domain Models: Vector Search
# ============================================================================

class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return")
    source_filter: str | None = Field(None, description="Filter by source table: maintenance_logs, inspection_reports, inspection_findings")
    district_filter: int | None = Field(None, description="Filter by district ID")
    severity_filter: str | None = Field(None, description="Filter by severity")


class VectorSearchResult(BaseModel):
    chunk_id: int
    source_table: str
    source_id: int
    chunk_text: str
    similarity_score: float
    asset_name: str | None = None
    asset_id: int | None = None
    log_date: CoerceDate = None
    severity: str | None = None


# ============================================================================
# Domain Models: Graph
# ============================================================================

class GraphNode(BaseModel):
    asset_id: int
    name: str
    asset_type: str
    status: str | None = None
    district_id: int | None = None


class GraphEdge(BaseModel):
    connection_id: int
    from_asset_id: int
    to_asset_id: int
    connection_type: str | None = None
    description: str | None = None


class GraphNeighborhood(BaseModel):
    center: GraphNode
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class GraphPath(BaseModel):
    path_length: int
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


# ============================================================================
# Domain Models: Data Entry (Ingest)
# ============================================================================

class NewMaintenanceLog(BaseModel):
    asset_id: int
    severity: str = Field(..., pattern="^(routine|warning|critical)$")
    narrative: str = Field(..., min_length=10)


class NewInspectionFinding(BaseModel):
    category: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    description: str = Field(..., min_length=10)
    recommendation: str = Field(..., min_length=10)


class NewInspectionReport(BaseModel):
    asset_id: int
    inspector: str = Field(..., min_length=2)
    overall_grade: str = Field(..., pattern="^[A-F]$")
    summary: str = Field(..., min_length=10)
    findings: list[NewInspectionFinding] = Field(..., min_length=1)


class PipelineStep(BaseModel):
    step: str
    sql: str


class IngestResult(BaseModel):
    """Response from the ingest endpoints, always includes pipeline steps."""
    source_id: int
    chunks_created: int
    vectors_stored: int
    pipeline_steps: list[PipelineStep] = []


# ============================================================================
# Domain Models: Prism Unified View
# ============================================================================

class PrismUnifiedView(BaseModel):
    """All projections for a single asset."""
    relational: AssetDetail
    json_document: dict | None = None
    graph: GraphNeighborhood | None = None
    vector_results: list[VectorSearchResult] = []
