"""
v2-lite 权限体系单元测试。
"""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.approval_flow import ApprovalFlowNodeCreate
from app.schemas.query import PrivApplyRequest
from app.services.monitor import MonitorService
from app.services.query_priv import QueryPrivService
from app.services.role import BUILTIN_ROLES


def _role_permissions(name: str) -> set[str]:
    for role in BUILTIN_ROLES:
        if role["name"] == name:
            return set(role["permissions"])
    raise AssertionError(f"role {name} not found")


class TestBuiltinRolePermissions:
    def test_developer_is_menu_query_only_for_core_entry(self):
        developer = _role_permissions("developer")
        assert "menu_query" in developer
        assert "menu_monitor" not in developer
        assert "process_view" not in developer
        assert "archive_apply" not in developer

    def test_dba_group_is_resource_scoped_monitor_admin(self):
        dba_group = _role_permissions("dba_group")
        assert "menu_monitor" in dba_group
        assert "monitor_config_manage" in dba_group
        assert "monitor_all_instances" not in dba_group


class TestApprovalFlowNodeSchema:
    def test_users_type_requires_explicit_approvers(self):
        with pytest.raises(ValidationError):
            ApprovalFlowNodeCreate(order=1, node_name="指定审批人", approver_type="users")

    def test_manager_type_does_not_require_ids(self):
        node = ApprovalFlowNodeCreate(order=1, node_name="直属上级", approver_type="manager")
        assert node.approver_ids == []

    def test_any_reviewer_type_does_not_require_ids(self):
        node = ApprovalFlowNodeCreate(order=1, node_name="任意审批员", approver_type="any_reviewer")
        assert node.approver_ids == []


class TestQueryPrivilegeSchema:
    def test_table_scope_requires_table_name(self):
        with pytest.raises(ValidationError):
            PrivApplyRequest(
                title="申请表级权限",
                instance_id=1,
                db_name="analytics",
                table_name="",
                valid_date="2099-01-01",
                limit_num=100,
                priv_type=2,
                apply_reason="需要排查问题",
                audit_auth_groups="1",
                scope_type="table",
            )

    def test_database_scope_can_omit_table_name(self):
        req = PrivApplyRequest(
            title="申请库级权限",
            instance_id=1,
            db_name="analytics",
            table_name="",
            valid_date="2099-01-01",
            limit_num=100,
            priv_type=1,
            apply_reason="需要排查问题",
            audit_auth_groups="1",
            scope_type="database",
        )
        assert req.scope_type == "database"


class TestResourceScopedAccess:
    def test_query_access_respects_resource_group_intersection(self):
        instance = SimpleNamespace(resource_groups=[SimpleNamespace(id=2), SimpleNamespace(id=3)])
        user = {"resource_groups": [1, 3], "permissions": [], "is_superuser": False}
        assert QueryPrivService.user_has_instance_access(user, instance) is True

    def test_monitor_access_respects_resource_group_intersection(self):
        instance = SimpleNamespace(resource_groups=[SimpleNamespace(id=5)])
        user = {"resource_groups": [2, 5], "permissions": [], "is_superuser": False}
        assert MonitorService._can_access_instance(user, instance) is True

    def test_monitor_access_denies_out_of_scope_instance(self):
        instance = SimpleNamespace(resource_groups=[SimpleNamespace(id=8)])
        user = {"resource_groups": [2, 5], "permissions": [], "is_superuser": False}
        assert MonitorService._can_access_instance(user, instance) is False


class TestQueryPrivilegeHelpers:
    def test_table_scope_normalizes_to_table_priv(self):
        assert QueryPrivService._normalize_scope_type("table", "") == ("table", 2)

    def test_table_name_also_forces_table_scope(self):
        assert QueryPrivService._normalize_scope_type("database", "orders") == ("table", 2)

    def test_database_scope_normalizes_to_database_priv(self):
        assert QueryPrivService._normalize_scope_type("database", "") == ("database", 1)
