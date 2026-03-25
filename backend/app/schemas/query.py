"""
在线查询 Pydantic Schema（Sprint 2）。
"""
from datetime import date
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class QueryExecuteRequest(BaseModel):
    instance_id: int
    db_name: str
    sql: str = Field(..., min_length=1, max_length=50000)
    limit_num: int = Field(default=100, ge=1, le=10000)

    @field_validator("sql")
    @classmethod
    def sql_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("SQL 不能为空")
        return v.strip()


class QueryResultResponse(BaseModel):
    column_list: list[str]
    rows: list[list[Any]]
    affected_rows: int
    cost_time_ms: int
    is_masked: bool = False
    error: str = ""


class QueryLogItem(BaseModel):
    id: int
    db_name: str
    sqllog: str
    effect_row: int
    cost_time_ms: int
    priv_check: bool
    masking: bool
    is_favorite: bool
    created_at: str

    model_config = {"from_attributes": True}


class QueryLogListResponse(BaseModel):
    total: int
    items: list[QueryLogItem]


# ─── 查询权限申请 ─────────────────────────────────────────────

class PrivApplyRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=50)
    instance_id: int
    group_id: int
    db_name: str
    table_name: str = ""
    valid_date: date
    limit_num: int = Field(default=100, ge=1, le=100000)
    priv_type: int = Field(default=1, description="1=库级 2=表级")
    apply_reason: str = Field(default="", max_length=500)
    audit_auth_groups: str = ""

    @field_validator("valid_date")
    @classmethod
    def valid_date_future(cls, v: date) -> date:
        from datetime import date as d
        if v < d.today():
            raise ValueError("有效期不能早于今天")
        return v


class PrivApplyItem(BaseModel):
    id: int
    title: str
    instance_id: int
    db_name: str
    table_name: str
    valid_date: str
    limit_num: int
    priv_type: int
    apply_reason: str
    status: int
    created_at: str

    model_config = {"from_attributes": True}


class PrivApplyListResponse(BaseModel):
    total: int
    items: list[PrivApplyItem]


class AuditPrivRequest(BaseModel):
    action: str = Field(..., description="pass 或 reject")
    remark: str = ""

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        if v not in ("pass", "reject"):
            raise ValueError("action 必须是 pass 或 reject")
        return v


class PrivilegeItem(BaseModel):
    id: int
    instance_id: int
    db_name: str
    table_name: str
    valid_date: str
    limit_num: int
    priv_type: int
    created_at: str

    model_config = {"from_attributes": True}
