"""三角色权限矩阵。

这里是后端鉴权的唯一来源：
- 路由用 require_permission("...") 声明所需权限；
- /permissions/matrix 直接返回本矩阵，方便演示与答辩说明；
- 后续新增模块时只在本文件补充权限名，避免权限散落在各处。
"""

# 普通员工：只能操作自己的数据
EMPLOYEE_PERMISSIONS = frozenset(
    {
        "profile.view.self",
        "attendance.sign",
        "attendance.view.self",
        "leave.apply",
        "leave.view.self",
        "trip.apply",
        "trip.view.self",
        "report.view.self",
    }
)

# 部门管理员：在员工权限之外，追加本部门范围的管理权限
# 只能查看/管理/分配本部门员工，查看本部门考勤，不能跨部门操作
DEPARTMENT_MANAGER_PERMISSIONS = EMPLOYEE_PERMISSIONS | frozenset(
    {
        "attendance.view.department",
        "employee.view.department",
        "employee.manage.department",
        "employee.assign.department",
        "leave.review.department",
        "trip.review.department",
        "shift.manage.department",
        "report.view.department",
    }
)

# 总管理员：跨部门管理，并独占系统级配置
GENERAL_ADMIN_PERMISSIONS = DEPARTMENT_MANAGER_PERMISSIONS | frozenset(
    {
        "department.manage",
        "employee.manage",
        "leave.review.all",
        "trip.review.all",
        "shift.manage.all",
        "report.view.all",
        "system.manage",
    }
)


ATTENDANCE_STAT_ROLES = frozenset({"employee", "department_manager"})


def is_attendance_subject(role: str) -> bool:
    """判断用户角色是否参与考勤统计：员工与部门管理员计，总管理员不计。"""
    return role in ATTENDANCE_STAT_ROLES


ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "employee": EMPLOYEE_PERMISSIONS,
    "department_manager": DEPARTMENT_MANAGER_PERMISSIONS,
    "general_admin": GENERAL_ADMIN_PERMISSIONS,
}


def get_permissions(role: str) -> frozenset[str]:
    """返回角色对应的权限集合；未知角色返回空集合（默认拒绝）。"""
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    """判断角色是否拥有指定权限。"""
    return permission in get_permissions(role)
