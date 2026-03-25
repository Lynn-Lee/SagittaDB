"""
统一导出所有模型，供 Alembic autogenerate 使用。
新增模型后记得在这里 import。
"""
from app.models.base import Base, BaseModel  # noqa: F401
from app.models.user import Users, ResourceGroup, Permission  # noqa: F401
from app.models.instance import Instance, SshTunnel, InstanceTag, InstanceDatabase  # noqa: F401
from app.models.workflow import (  # noqa: F401
    SqlWorkflow, SqlWorkflowContent, WorkflowAudit, WorkflowLog,
    WorkflowStatus, WorkflowType, AuditStatus,
)
from app.models.query import QueryPrivilege, QueryPrivilegeApply, QueryLog  # noqa: F401
from app.models.system import SystemConfig, OperationLog  # noqa: F401
from app.models.masking import MaskingRule, WorkflowTemplate  # noqa: F401
from app.models.monitor import (  # noqa: F401
    MonitorCollectConfig, MonitorPrivilegeApply, MonitorPrivilege,
)

__all__ = [
    "Base", "BaseModel",
    "Users", "ResourceGroup", "Permission",
    "Instance", "SshTunnel", "InstanceTag", "InstanceDatabase",
    "SqlWorkflow", "SqlWorkflowContent", "WorkflowAudit", "WorkflowLog",
    "WorkflowStatus", "WorkflowType", "AuditStatus",
    "QueryPrivilege", "QueryPrivilegeApply", "QueryLog",
    "MonitorCollectConfig", "MonitorPrivilegeApply", "MonitorPrivilege",
    "SystemConfig", "OperationLog",
    "MaskingRule", "WorkflowTemplate",
]
