"""
可观测中心 Pydantic Schema（Sprint 5）。
"""
from datetime import date

from pydantic import BaseModel, Field, field_validator


class MonitorConfigCreate(BaseModel):
    instance_id: int
    exporter_url: str = Field(..., description="Exporter 地址，如 http://host:9104/metrics")
    exporter_type: str = Field(..., description="mysqld_exporter / postgres_exporter 等")
    collect_interval: int = Field(default=60, ge=10, le=3600)
    alert_rules_override: dict = {}

    @field_validator("exporter_url")
    @classmethod
    def url_valid(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("exporter_url 必须以 http:// 或 https:// 开头")
        return v


class MonitorConfigUpdate(BaseModel):
    exporter_url: str | None = None
    collect_interval: int | None = None
    is_enabled: bool | None = None
    alert_rules_override: dict | None = None


class MonitorConfigResponse(BaseModel):
    id: int
    instance_id: int
    instance_name: str = ""
    is_enabled: bool
    collect_interval: int
    exporter_url: str
    exporter_type: str
    alert_rules_override: dict
    created_by: str
    model_config = {"from_attributes": True}


class MonitorPrivApplyRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=50)
    instance_id: int
    group_id: int
    valid_date: date
    apply_reason: str = ""
    audit_auth_groups: str = ""

    @field_validator("valid_date")
    @classmethod
    def future_date(cls, v: date) -> date:
        from datetime import date as d
        if v < d.today():
            raise ValueError("有效期不能早于今天")
        return v


class AuditMonitorPrivRequest(BaseModel):
    action: str = Field(..., description="pass 或 reject")
    remark: str = ""

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        if v not in ("pass", "reject"):
            raise ValueError("action 必须是 pass 或 reject")
        return v


class DashboardStats(BaseModel):
    workflow_month_total: int = 0
    workflow_finish_total: int = 0
    workflow_pending_total: int = 0
    instance_total: int = 0
    query_today_total: int = 0
    monitor_instance_total: int = 0


class WorkflowTrendItem(BaseModel):
    date: str
    submit: int
    finish: int
    reject: int


class InstanceDistItem(BaseModel):
    db_type: str
    count: int
