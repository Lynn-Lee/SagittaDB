"""
认证路由：登录、登出、Token 刷新、2FA、当前用户信息。
"""
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user, oauth2_scheme
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_field,
    encrypt_field,
    verify_password,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    TwoFAVerifyRequest,
)
from app.services.user import UserService

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_redis():
    from redis.asyncio import Redis

    from app.core.config import settings
    r = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield r
    finally:
        await r.aclose()


@router.post("/login/", response_model=TokenResponse, summary="用户名密码登录")
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await UserService.get_by_username(db, data.username)
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    payload = {"sub": str(user.id), "username": user.username, "tenant_id": user.tenant_id}
    if user.totp_enabled:
        payload["requires_2fa"] = True

    logger.info("user_login")
    return TokenResponse(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token({"sub": str(user.id), "tenant_id": user.tenant_id}),
    )


@router.post("/login/form/", response_model=TokenResponse, include_in_schema=False)
async def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    return await login(LoginRequest(username=form_data.username, password=form_data.password), db)


@router.post("/token/refresh/", response_model=TokenResponse, summary="刷新 access_token")
async def refresh_token(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(data.refresh_token)
    except JWTError as e:
        raise HTTPException(status_code=401, detail="refresh_token 无效或已过期") from e
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="非法的 token 类型")

    user = await UserService.get_by_id(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")

    new_payload = {"sub": str(user.id), "username": user.username, "tenant_id": user.tenant_id}
    if user.totp_enabled:
        new_payload["requires_2fa"] = True
    return TokenResponse(
        access_token=create_access_token(new_payload),
        refresh_token=create_refresh_token({"sub": str(user.id), "tenant_id": user.tenant_id}),
    )


@router.post("/logout/", summary="登出")
async def logout(token: str = Depends(oauth2_scheme), redis=Depends(get_redis)):
    try:
        payload = decode_token(token)
        ttl = int(payload.get("exp", 0)) - int(time.time())
        if ttl > 0:
            await redis.setex(f"blacklist:{token}", ttl, "1")
    except JWTError:
        pass
    return {"status": 0, "msg": "已退出登录"}


@router.post("/2fa/setup/", summary="生成 TOTP 密钥")
async def setup_2fa(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    import pyotp
    db_user = await UserService.get_by_id(db, user["id"])
    if not db_user:
        raise HTTPException(404, "用户不存在")
    secret = pyotp.random_base32()
    db_user.totp_secret = encrypt_field(secret)
    await db.commit()
    totp = pyotp.TOTP(secret)
    return {
        "secret": secret,
        "provisioning_uri": totp.provisioning_uri(name=db_user.username, issuer_name="SagittaDB"),
    }


@router.post("/2fa/verify/", summary="验证 TOTP 并激活 2FA")
async def verify_2fa(data: TwoFAVerifyRequest, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    import pyotp
    db_user = await UserService.get_by_id(db, user["id"])
    if not db_user or not db_user.totp_secret:
        raise HTTPException(400, "请先调用 /2fa/setup/ 生成密钥")
    secret = decrypt_field(db_user.totp_secret)
    if not pyotp.TOTP(secret).verify(data.totp_code, valid_window=1):
        raise HTTPException(400, "TOTP 验证码错误")
    db_user.totp_enabled = True
    await db.commit()
    return {"status": 0, "msg": "2FA 已启用"}


@router.post("/2fa/disable/", summary="禁用 2FA")
async def disable_2fa(data: TwoFAVerifyRequest, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    import pyotp
    db_user = await UserService.get_by_id(db, user["id"])
    if not db_user or not db_user.totp_enabled:
        raise HTTPException(400, "2FA 未启用")
    secret = decrypt_field(db_user.totp_secret)
    if not pyotp.TOTP(secret).verify(data.totp_code, valid_window=1):
        raise HTTPException(400, "TOTP 验证码错误")
    db_user.totp_enabled = False
    db_user.totp_secret = None
    await db.commit()
    return {"status": 0, "msg": "2FA 已禁用"}


@router.get("/me/", summary="获取当前用户信息")
async def get_me(user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    db_user = await UserService.get_by_id(db, user["id"])
    if not db_user:
        raise HTTPException(404, "用户不存在")
    permissions = await UserService.get_permissions(db, db_user.id)
    return {
        "id": db_user.id, "username": db_user.username,
        "display_name": db_user.display_name, "email": db_user.email,
        "is_superuser": db_user.is_superuser, "is_active": db_user.is_active,
        "auth_type": db_user.auth_type, "totp_enabled": db_user.totp_enabled,
        "permissions": permissions,
        "resource_groups": [rg.id for rg in db_user.resource_groups],
        "tenant_id": db_user.tenant_id,
    }


@router.post("/password/change/", summary="修改密码")
async def change_password(data: ChangePasswordRequest, user=Depends(current_user), db: AsyncSession = Depends(get_db)):
    await UserService.change_password(db, user["id"], data.old_password, data.new_password)
    return {"status": 0, "msg": "密码已修改，请重新登录"}
