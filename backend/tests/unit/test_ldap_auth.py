"""
LDAP 认证服务单元测试（使用 mock，无需真实 LDAP 服务器）。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ldap_auth import LdapAuthService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def ldap_config():
    return {
        "ldap_enabled": "true",
        "ldap_server_uri": "ldap://ldap.test.com:389",
        "ldap_bind_dn": "cn=admin,dc=test,dc=com",
        "ldap_bind_password": "adminpass",
        "ldap_user_search_base": "ou=users,dc=test,dc=com",
        "ldap_user_filter": "(uid=%(user)s)",
        "ldap_attr_username": "uid",
        "ldap_attr_email": "mail",
        "ldap_attr_display": "cn",
    }


@pytest.mark.asyncio
async def test_ldap_disabled_raises(mock_db, ldap_config):
    """LDAP 未启用时应抛出 ValueError。"""
    ldap_config["ldap_enabled"] = "false"
    with (
        patch.object(LdapAuthService, "_get_ldap_config", AsyncMock(return_value=ldap_config)),
        pytest.raises(ValueError, match="LDAP 认证未启用"),
    ):
        await LdapAuthService.authenticate(mock_db, "alice", "pass")


@pytest.mark.asyncio
async def test_ldap_missing_server_uri_raises(mock_db, ldap_config):
    """服务器地址为空时应抛出配置不完整错误。"""
    ldap_config["ldap_server_uri"] = ""
    with (
        patch.object(LdapAuthService, "_get_ldap_config", AsyncMock(return_value=ldap_config)),
        pytest.raises(ValueError, match="配置不完整"),
    ):
        await LdapAuthService.authenticate(mock_db, "alice", "pass")


@pytest.mark.asyncio
async def test_ldap_user_not_found_raises(mock_db, ldap_config):
    """LDAP 搜索无结果时应抛出用户不存在错误。"""
    mock_svc_conn = MagicMock()
    mock_svc_conn.entries = []

    with (
        patch.object(LdapAuthService, "_get_ldap_config", AsyncMock(return_value=ldap_config)),
        patch("ldap3.Server"),
        patch("ldap3.Connection", return_value=mock_svc_conn),
        pytest.raises(ValueError, match="用户不存在"),
    ):
        await LdapAuthService.authenticate(mock_db, "ghost", "pass")


@pytest.mark.asyncio
async def test_ldap_wrong_password_raises(mock_db, ldap_config):
    """用户密码错误时应抛出密码错误。"""
    import ldap3.core.exceptions as ldap_exc

    mock_entry = MagicMock()
    mock_entry.entry_dn = "uid=alice,ou=users,dc=test,dc=com"
    mock_entry.uid.values = ["alice"]
    mock_entry.mail.values = ["alice@test.com"]
    mock_entry.cn.values = ["Alice"]

    mock_svc_conn = MagicMock()
    mock_svc_conn.entries = [mock_entry]

    def _conn_side_effect(server, user, password, **kwargs):
        if user == mock_entry.entry_dn:
            raise ldap_exc.LDAPInvalidCredentialsResult
        return mock_svc_conn

    with (
        patch.object(LdapAuthService, "_get_ldap_config", AsyncMock(return_value=ldap_config)),
        patch("ldap3.Server"),
        patch("ldap3.Connection", side_effect=_conn_side_effect),
        pytest.raises(ValueError, match="密码错误"),
    ):
        await LdapAuthService.authenticate(mock_db, "alice", "wrong")


@pytest.mark.asyncio
async def test_ldap_import_error_raises(mock_db, ldap_config):
    """ldap3 未安装时应返回友好错误提示。"""
    with (
        patch.object(LdapAuthService, "_get_ldap_config", AsyncMock(return_value=ldap_config)),
        patch.dict("sys.modules", {"ldap3": None}),
        pytest.raises((ValueError, ImportError)),
    ):
        await LdapAuthService.authenticate(mock_db, "alice", "pass")
