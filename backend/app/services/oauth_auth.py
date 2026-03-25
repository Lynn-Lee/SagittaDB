"""
第三方 OAuth2 登录服务（Pack F）。

支持：钉钉（DingTalk）/ 飞书（Feishu）/ 企业微信（WeCom）/ OIDC（通用）。

通用流程：
  1. get_authorize_url(provider, db, callback_url, state) → 平台授权 URL
  2. handle_callback(provider, db, code, callback_url)    → 自动 provision 用户
"""
from __future__ import annotations

import base64
import json
import logging
import urllib.parse
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import Users
from app.services.system_config import SystemConfigService

logger = logging.getLogger(__name__)


# ── 公共用户 Provision ────────────────────────────────────────

async def _provision_oauth_user(
    db: AsyncSession,
    username: str,
    email: str,
    display_name: str,
    external_id: str,
    auth_type: str,
) -> Users:
    """查找或创建第三方登录用户，自动更新可变属性。"""
    result = await db.execute(
        select(Users).where(
            Users.auth_type == auth_type,
            Users.external_id == external_id,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        # 兼容首次迁移：按用户名查找
        result = await db.execute(select(Users).where(Users.username == username))
        user = result.scalar_one_or_none()

    if user is None:
        user = Users(
            username=username,
            password=hash_password("__oauth_no_local_password__"),
            display_name=display_name or username,
            email=email or "",
            auth_type=auth_type,
            external_id=external_id,
            is_active=True,
        )
        db.add(user)
        logger.info("oauth_user_provisioned: provider=%s username=%s", auth_type, username)
    else:
        user.auth_type = auth_type
        user.external_id = external_id
        if display_name:
            user.display_name = display_name
        if email:
            user.email = email

    await db.commit()
    await db.refresh(user)
    return user


# ── 钉钉（DingTalk New API v2）────────────────────────────────

async def get_dingtalk_authorize_url(
    db: AsyncSession, callback_url: str, state: str
) -> str:
    app_id = await SystemConfigService.get_value(db, "ding_login_app_id")
    if not app_id:
        raise ValueError("钉钉登录 AppKey 未配置，请在系统配置 → 钉钉通知中填写")
    params = {
        "response_type": "code",
        "client_id": app_id,
        "redirect_uri": callback_url,
        "scope": "openid",
        "prompt": "consent",
        "state": state,
    }
    return "https://login.dingtalk.com/oauth2/auth?" + urllib.parse.urlencode(params)


async def handle_dingtalk_callback(
    db: AsyncSession, code: str, callback_url: str
) -> Users:
    app_id = await SystemConfigService.get_value(db, "ding_login_app_id")
    app_secret = await SystemConfigService.get_value(db, "ding_login_app_secret")
    if not app_id or not app_secret:
        raise ValueError("钉钉登录配置不完整")

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            "https://api.dingtalk.com/v1.0/oauth2/userAccessToken",
            json={
                "clientId": app_id,
                "clientSecret": app_secret,
                "code": code,
                "grantType": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("accessToken")
        if not access_token:
            raise ValueError(f"钉钉获取 Token 失败: {token_data}")

        me_resp = await client.get(
            "https://api.dingtalk.com/v1.0/contact/users/me",
            headers={"x-acs-dingtalk-access-token": access_token},
        )
        me_resp.raise_for_status()
        user_info = me_resp.json()

    union_id = user_info.get("unionId", "")
    nick = user_info.get("nick", "")
    email = user_info.get("email", "")
    username = f"ding_{union_id[:12]}" if union_id else f"ding_{nick}"
    return await _provision_oauth_user(db, username, email, nick, union_id, "dingtalk")


# ── 飞书（Feishu / Lark）─────────────────────────────────────

async def get_feishu_authorize_url(
    db: AsyncSession, callback_url: str, state: str
) -> str:
    app_id = await SystemConfigService.get_value(db, "feishu_app_id")
    if not app_id:
        raise ValueError("飞书 App ID 未配置，请在系统配置 → 飞书通知中填写")
    params = {
        "app_id": app_id,
        "redirect_uri": callback_url,
        "scope": "contact:user.base:readonly",
        "state": state,
    }
    return "https://accounts.feishu.cn/open-apis/authen/v1/authorize?" + urllib.parse.urlencode(params)


async def handle_feishu_callback(
    db: AsyncSession, code: str, callback_url: str
) -> Users:
    app_id = await SystemConfigService.get_value(db, "feishu_app_id")
    app_secret = await SystemConfigService.get_value(db, "feishu_app_secret")
    if not app_id or not app_secret:
        raise ValueError("飞书登录配置不完整")

    creds = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token",
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/json",
            },
            json={"grant_type": "authorization_code", "code": code},
        )
        token_resp.raise_for_status()
        token_body = token_resp.json()
        if token_body.get("code") != 0:
            raise ValueError(f"飞书获取 Token 失败: {token_body.get('msg')}")
        access_token = token_body["data"]["access_token"]

        me_resp = await client.get(
            "https://open.feishu.cn/open-apis/authen/v1/user_info",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        me_resp.raise_for_status()
        me_body = me_resp.json()
        if me_body.get("code") != 0:
            raise ValueError(f"飞书获取用户信息失败: {me_body.get('msg')}")
        user_data = me_body["data"]

    open_id = user_data.get("open_id", "")
    name = user_data.get("name", "")
    email = user_data.get("email", "")
    username = f"feishu_{open_id[:12]}" if open_id else f"feishu_{name}"
    return await _provision_oauth_user(db, username, email, name, open_id, "feishu")


# ── 企业微信（WeCom）──────────────────────────────────────────

async def get_wecom_authorize_url(
    db: AsyncSession, callback_url: str, state: str
) -> str:
    corp_id = await SystemConfigService.get_value(db, "wecom_login_corp_id")
    agent_id = await SystemConfigService.get_value(db, "wecom_login_agent_id")
    if not corp_id or not agent_id:
        raise ValueError("企业微信 CorpID 或 AgentId 未配置")
    params = {
        "appid": corp_id,
        "agentid": agent_id,
        "redirect_uri": callback_url,
        "state": state,
    }
    return "https://open.work.weixin.qq.com/wwopen/sso/qrConnect?" + urllib.parse.urlencode(params)


async def handle_wecom_callback(
    db: AsyncSession, code: str, callback_url: str
) -> Users:
    corp_id = await SystemConfigService.get_value(db, "wecom_login_corp_id")
    app_secret = await SystemConfigService.get_value(db, "wecom_login_app_secret")
    if not corp_id or not app_secret:
        raise ValueError("企业微信登录配置不完整")

    async with httpx.AsyncClient(timeout=10) as client:
        # Step 1: 获取企业级 access token
        token_resp = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={"corpid": corp_id, "corpsecret": app_secret},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        if token_data.get("errcode", 0) != 0:
            raise ValueError(f"企微获取 Token 失败: {token_data.get('errmsg')}")
        access_token = token_data["access_token"]

        # Step 2: code → UserId
        uid_resp = await client.get(
            "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo",
            params={"access_token": access_token, "code": code},
        )
        uid_resp.raise_for_status()
        uid_data = uid_resp.json()
        if uid_data.get("errcode", 0) != 0:
            raise ValueError(f"企微获取用户身份失败: {uid_data.get('errmsg')}")
        user_id = uid_data.get("UserId") or uid_data.get("OpenId", "")

        # Step 3: 获取用户详情（仅 UserId 情况下有完整信息）
        name = ""
        email = ""
        if uid_data.get("UserId"):
            detail_resp = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/user/get",
                params={"access_token": access_token, "userid": user_id},
            )
            detail_resp.raise_for_status()
            detail = detail_resp.json()
            if detail.get("errcode", 0) == 0:
                name = detail.get("name", "")
                email = detail.get("email", "") or detail.get("biz_mail", "")

    username = f"wecom_{user_id[:12]}" if user_id else "wecom_user"
    return await _provision_oauth_user(db, username, email, name, user_id, "wecom")


# ── OIDC（通用 OpenID Connect）───────────────────────────────

async def get_oidc_authorize_url(
    db: AsyncSession, callback_url: str, state: str
) -> str:
    auth_endpoint = await SystemConfigService.get_value(db, "oidc_authorization_endpoint")
    client_id = await SystemConfigService.get_value(db, "oidc_client_id")
    if not auth_endpoint or not client_id:
        raise ValueError("OIDC 授权端点或 Client ID 未配置")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback_url,
        "scope": "openid email profile",
        "state": state,
    }
    return auth_endpoint + "?" + urllib.parse.urlencode(params)


async def handle_oidc_callback(
    db: AsyncSession, code: str, callback_url: str
) -> Users:
    token_endpoint = await SystemConfigService.get_value(db, "oidc_token_endpoint")
    userinfo_endpoint = await SystemConfigService.get_value(db, "oidc_userinfo_endpoint")
    client_id = await SystemConfigService.get_value(db, "oidc_client_id")
    client_secret = await SystemConfigService.get_value(db, "oidc_client_secret")
    if not token_endpoint or not client_id:
        raise ValueError("OIDC 配置不完整（Token 端点或 Client ID 缺失）")

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": callback_url,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError(f"OIDC 获取 Token 失败: {token_data}")

        user_info: dict[str, Any]
        if userinfo_endpoint:
            me_resp = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            me_resp.raise_for_status()
            user_info = me_resp.json()
        else:
            # 从 id_token payload 解码（不做签名验证，仅用于 provision）
            id_token = token_data.get("id_token", "")
            parts = id_token.split(".")
            if len(parts) >= 2:
                padded = parts[1] + "=" * (-len(parts[1]) % 4)
                user_info = json.loads(base64.urlsafe_b64decode(padded))
            else:
                raise ValueError("OIDC 无法获取用户信息：userinfo_endpoint 未配置且无 id_token")

    sub = user_info.get("sub", "")
    email = user_info.get("email", "")
    name = user_info.get("name", "") or user_info.get("preferred_username", "")
    username = str(user_info.get("preferred_username", "")) or f"oidc_{sub[:12]}"
    return await _provision_oauth_user(db, username, email, name, sub, "oidc")


# ── 统一分发入口 ──────────────────────────────────────────────

SUPPORTED_PROVIDERS = ("dingtalk", "feishu", "wecom", "oidc")

_PROVIDER_ENABLED_KEY: dict[str, str] = {
    "dingtalk": "ding_login_enabled",
    "feishu":   "feishu_login_enabled",
    "wecom":    "wecom_login_enabled",
    "oidc":     "oidc_enabled",
}

_GET_URL = {
    "dingtalk": get_dingtalk_authorize_url,
    "feishu":   get_feishu_authorize_url,
    "wecom":    get_wecom_authorize_url,
    "oidc":     get_oidc_authorize_url,
}

_HANDLE_CB = {
    "dingtalk": handle_dingtalk_callback,
    "feishu":   handle_feishu_callback,
    "wecom":    handle_wecom_callback,
    "oidc":     handle_oidc_callback,
}


async def get_authorize_url(
    provider: str, db: AsyncSession, callback_url: str, state: str
) -> str:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"不支持的登录方式: {provider}")
    enabled_key = _PROVIDER_ENABLED_KEY[provider]
    enabled = await SystemConfigService.get_value(db, enabled_key)
    if enabled.lower() != "true":
        raise ValueError(f"{provider} 登录未启用，请在系统配置中开启")
    return await _GET_URL[provider](db, callback_url, state)


async def handle_callback(
    provider: str, db: AsyncSession, code: str, callback_url: str
) -> Users:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"不支持的登录方式: {provider}")
    return await _HANDLE_CB[provider](db, code, callback_url)
