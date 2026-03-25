"""FastAPI 公共 Depends 依赖（Sprint 1 完整实现）。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/form/")

_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="无法验证凭据",
    headers={"WWW-Authenticate": "Bearer"},
)


async def current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """获取当前登录用户，返回含 permissions 的完整字典。"""
    try:
        payload = decode_token(token)
    except JWTError:
        raise _401

    user_id = payload.get("sub")
    if not user_id:
        raise _401

    # Token 黑名单检查（降级：Redis 不可用时放行）
    try:
        from app.core.config import settings
        from redis.asyncio import Redis
        r = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        if await r.exists(f"blacklist:{token}"):
            await r.aclose()
            raise _401
        await r.aclose()
    except HTTPException:
        raise
    except Exception:
        pass

    from app.services.user import UserService
    db_user = await UserService.get_by_id(db, int(user_id))
    if not db_user or not db_user.is_active:
        raise _401

    if payload.get("requires_2fa") and not payload.get("2fa_verified"):
        raise HTTPException(status_code=403, detail="请先完成二步验证")

    permissions = await UserService.get_permissions(db, db_user.id)

    return {
        "id": db_user.id,
        "username": db_user.username,
        "display_name": db_user.display_name,
        "is_superuser": db_user.is_superuser,
        "is_active": db_user.is_active,
        "permissions": permissions,
        "resource_groups": [rg.id for rg in db_user.resource_groups],
        "tenant_id": db_user.tenant_id,
    }


async def current_superuser(user: dict = Depends(current_user)) -> dict:
    if not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return user


def require_perm(perm: str):
    """权限校验依赖工厂，用法：Depends(require_perm('sql_review'))"""
    async def _checker(user: dict = Depends(current_user)) -> dict:
        if user.get("is_superuser"):
            return user
        if perm not in user.get("permissions", []):
            raise HTTPException(status_code=403, detail=f"缺少权限：{perm}")
        return user
    return _checker
