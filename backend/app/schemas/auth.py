"""认证相关的请求与响应结构。"""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """登录请求体：只使用账号密码。"""

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    """对外返回的用户信息，绝不包含密码哈希。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_no: str
    username: str
    name: str
    role: str
    department_id: int | None = None
    status: str


class TokenResponse(BaseModel):
    """登录成功后的令牌信息。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class ProfileWithPermissions(UserProfile):
    """当前用户信息 + 权限清单，供前端控制菜单显示。"""

    permissions: list[str]
