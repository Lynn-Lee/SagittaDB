"""
SQL 工单 Pydantic Schema（Sprint 3）。
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class WorkflowCreateRequest(BaseModel):
    workflow_name: str = Field(..., min_length=1, max_length=50)
    group_id: int
    instance_id: int
    db_name: str
    sql_content: str = Field(..., min_length=1)
    syntax_type: int = Field(default=0, description="0未知 1DDL 2DML 3导出")
    is_backup: bool = True
    run_date_start: Optional[datetime] = None
    run_date_end: Optional[datetime] = None

    @field_validator("sql_content")
    @classmethod
    def sql_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("SQL 内容不能为空")
        return v


class WorkflowAuditRequest(BaseModel):
    action: str = Field(..., description="pass 或 reject")
    remark: str = Field(default="", max_length=500)

    @field_validator("action")
    @classmethod
    def action_valid(cls, v: str) -> str:
        if v not in ("pass", "reject"):
            raise ValueError("action 必须是 pass 或 reject")
        return v


class WorkflowExecuteRequest(BaseModel):
    mode: str = Field(default="auto", description="auto=立即执行 manual=手动执行")
    timing_time: Optional[datetime] = None


class WorkflowItem(BaseModel):
    id: int
    workflow_name: str
    group_name: str
    instance_id: int
    db_name: str
    syntax_type: int
    is_backup: bool
    engineer: str
    engineer_display: str
    status: int
    status_desc: str
    audit_auth_groups: str
    run_date_start: Optional[str]
    run_date_end: Optional[str]
    finish_time: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class WorkflowDetailResponse(BaseModel):
    id: int
    workflow_name: str
    group_id: int
    group_name: str
    instance_id: int
    db_name: str
    syntax_type: int
    is_backup: bool
    engineer: str
    engineer_display: str
    status: int
    status_desc: str
    audit_auth_groups: str
    run_date_start: Optional[str]
    run_date_end: Optional[str]
    finish_time: Optional[str]
    created_at: str
    sql_content: str = ""
    review_content: str = ""
    execute_result: str = ""
    audit_logs: list[dict] = []


class WorkflowListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[WorkflowItem]


class WorkflowCheckRequest(BaseModel):
    instance_id: int
    db_name: str
    sql_content: str
