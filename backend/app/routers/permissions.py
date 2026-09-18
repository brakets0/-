"""权限演示路由：用于验证三角色权限矩阵的隔离效果。

这些接口既是自动化测试的落点，也方便答辩时现场演示
「员工 / 部门管理员 / 总管理员」访问同一接口的不同结果。
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, require_permission
from app.models import User
from app.permissions import ROLE_PERMISSIONS, get_permissions


router = APIRouter(prefix="/permissions", tags=["权限"])


@router.get("/me", summary="查看当前账号角色与权限")
def my_permissions(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "role": user.role,
        "permissions": sorted(get_permissions(user.role)),
    }


@router.get(
    "/matrix",
    summary="查看完整三角色权限矩阵（仅总管理员）",
    dependencies=[Depends(require_permission("system.manage"))],
)
def permission_matrix():
    return {
        role: sorted(permissions) for role, permissions in ROLE_PERMISSIONS.items()
    }


@router.get(
    "/department-check",
    summary="部门管理员权限探针",
    dependencies=[Depends(require_permission("attendance.view.department"))],
)
def department_check():
    return {"message": "部门管理权限校验通过"}


@router.get(
    "/employee-manage-check",
    summary="部门级员工管理权限探针",
    dependencies=[Depends(require_permission("employee.manage.department"))],
)
def employee_manage_check():
    return {"message": "部门员工管理权限校验通过"}


@router.get(
    "/admin-check",
    summary="总管理员权限探针",
    dependencies=[Depends(require_permission("system.manage"))],
)
def admin_check():
    return {"message": "总管理员权限校验通过"}
