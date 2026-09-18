"""认证路由：登录、查看当前账号。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.permissions import get_permissions
from app.schemas.auth import (
    LoginRequest,
    ProfileWithPermissions,
    TokenResponse,
    UserProfile,
)
from app.security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse, summary="账号密码登录")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """校验账号密码并签发 JWT；用户名不存在和密码错误返回同样的提示。"""
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已停用，请联系管理员")

    token = create_access_token(user_id=user.id, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserProfile.model_validate(user),
    )


@router.get(
    "/me", response_model=ProfileWithPermissions, summary="查看当前登录账号"
)
def read_current_user(user: User = Depends(get_current_user)):
    """返回当前账号信息与权限清单，桌面端/管理台据此渲染菜单。"""
    return ProfileWithPermissions(
        **UserProfile.model_validate(user).model_dump(),
        permissions=sorted(get_permissions(user.role)),
    )
