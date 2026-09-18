"""FastAPI 认证/授权依赖。

get_current_user    解析 Bearer JWT 并加载当前用户；
require_roles       要求当前用户属于指定角色；
require_permission  要求当前用户拥有指定权限（权限矩阵见 app/permissions.py）。
"""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.permissions import get_permissions
from app.security import decode_access_token


bearer_scheme = HTTPBearer(
    auto_error=False, description="登录接口返回的 access_token"
)


def _unauthorized() -> HTTPException:
    """统一的 401 响应，避免向客户端暴露具体失败原因。"""
    return HTTPException(
        status_code=401,
        detail="未登录或登录状态已失效",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从请求头解析 JWT，并返回状态正常的当前用户。"""
    if credentials is None or not credentials.credentials:
        raise _unauthorized()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (PyJWTError, KeyError, TypeError, ValueError):
        raise _unauthorized()

    user = db.get(User, user_id)
    if user is None or user.status != "active":
        raise _unauthorized()
    return user


def require_roles(*roles: str):
    """生成角色校验依赖，例如 require_roles("general_admin")。"""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user

    return dependency


def require_permission(permission: str):
    """生成权限校验依赖，例如 require_permission("leave.review.department")。"""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if permission not in get_permissions(user.role):
            raise HTTPException(status_code=403, detail="权限不足")
        return user

    return dependency
