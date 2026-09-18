"""员工管理路由（I4）：总管理员管理全部，部门管理员仅限本部门。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import Attendance, BusinessTrip, Department, LeaveRequest, User
from app.permissions import get_permissions
from app.schemas.organization import (
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
)
from app.security import hash_password


router = APIRouter(prefix="/employees", tags=["组织-员工"])


def _employee_out(user: User) -> EmployeeOut:
    department = user.department
    return EmployeeOut(
        id=user.id,
        employee_no=user.employee_no,
        username=user.username,
        name=user.name,
        role=user.role,
        department_id=user.department_id,
        department_name=department.name if department else None,
        status=user.status,
        created_at=user.created_at,
    )


def _can_manage_employee(user: User = Depends(get_current_user)) -> User:
    permissions = get_permissions(user.role)
    if "employee.manage" in permissions or "employee.manage.department" in permissions:
        return user
    raise HTTPException(status_code=403, detail="权限不足")


def _resolve_department(
    db: Session,
    *,
    role: str,
    department_id: int | None,
    operator: User,
) -> Department | None:
    if role == "general_admin":
        if department_id is not None:
            raise HTTPException(status_code=400, detail="总管理员不需要所属部门")
        return None
    if department_id is None:
        raise HTTPException(status_code=400, detail="请选择所属部门")

    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    if operator.role != "general_admin" and department_id != operator.department_id:
        raise HTTPException(status_code=403, detail="只能在本部门内操作员工")
    return department


@router.get("", response_model=list[EmployeeOut], summary="员工列表")
def list_employees(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("employee.view.department")),
):
    stmt = select(User).options(selectinload(User.department)).order_by(
        User.employee_no
    )
    if user.role != "general_admin":
        stmt = stmt.where(User.department_id == user.department_id)
    employees = db.execute(stmt).scalars().all()
    return [_employee_out(item) for item in employees]


@router.post(
    "",
    response_model=EmployeeOut,
    summary="新建员工",
)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(_can_manage_employee),
):
    if user.role != "general_admin" and payload.role != "employee":
        raise HTTPException(status_code=403, detail="部门管理员只能创建普通员工")

    _resolve_department(
        db,
        role=payload.role,
        department_id=payload.department_id,
        operator=user,
    )

    if db.execute(
        select(User).where(User.employee_no == payload.employee_no)
    ).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="工号已存在")
    if db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    employee = User(
        employee_no=payload.employee_no,
        username=payload.username,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
        department_id=payload.department_id,
        status=payload.status,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return _employee_out(employee)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeOut,
    summary="更新员工",
)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(_can_manage_employee),
):
    employee = db.get(User, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    if user.role != "general_admin" and employee.department_id != user.department_id:
        raise HTTPException(status_code=403, detail="只能操作本部门员工")

    data = payload.model_dump(exclude_unset=True)
    next_role = data.get("role", employee.role)
    next_department_id = data.get("department_id", employee.department_id)

    if user.role != "general_admin":
        if next_role != "employee":
            raise HTTPException(status_code=403, detail="部门管理员只能管理普通员工")
        if next_department_id != user.department_id:
            raise HTTPException(status_code=403, detail="不能将员工移出本部门")
    _resolve_department(
        db,
        role=next_role,
        department_id=next_department_id,
        operator=user,
    )

    if (
        "employee_no" in data
        and data["employee_no"] != employee.employee_no
        and db.execute(
            select(User).where(
                User.employee_no == data["employee_no"],
                User.id != employee.id,
            )
        ).scalar_one_or_none()
    ):
        raise HTTPException(status_code=409, detail="工号已存在")
    if (
        "username" in data
        and data["username"] != employee.username
        and db.execute(
            select(User).where(
                User.username == data["username"],
                User.id != employee.id,
            )
        ).scalar_one_or_none()
    ):
        raise HTTPException(status_code=409, detail="用户名已存在")

    for key, value in data.items():
        if key == "password":
            employee.password_hash = hash_password(value)
        else:
            setattr(employee, key, value)

    stale_manager_departments = db.execute(
        select(Department).where(Department.manager_user_id == employee.id)
    ).scalars().all()
    for dept in stale_manager_departments:
        if next_role == "department_manager" and next_department_id == dept.id:
            continue
        dept.manager_user_id = None

    db.commit()
    db.refresh(employee)
    return _employee_out(employee)


@router.delete(
    "/{employee_id}",
    status_code=204,
    summary="删除员工",
    dependencies=[Depends(require_permission("employee.manage"))],
)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    employee = db.get(User, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    if employee.id == user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")

    has_attendance = db.execute(
        select(Attendance).where(Attendance.employee_id == employee_id).limit(1)
    ).scalar_one_or_none()
    has_leave = db.execute(
        select(LeaveRequest).where(LeaveRequest.employee_id == employee_id).limit(1)
    ).scalar_one_or_none()
    has_trip = db.execute(
        select(BusinessTrip).where(BusinessTrip.employee_id == employee_id).limit(1)
    ).scalar_one_or_none()
    if has_attendance or has_leave or has_trip:
        raise HTTPException(status_code=409, detail="该员工已有业务记录，不能删除")

    manager_departments = db.execute(
        select(Department).where(Department.manager_user_id == employee_id)
    ).scalars().all()
    for dept in manager_departments:
        dept.manager_user_id = None

    db.delete(employee)
    db.commit()
