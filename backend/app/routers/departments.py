"""部门管理路由（I4）：列表、详情、新建、更新、指派管理员、删除。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models import Department, Shift, User
from app.schemas.organization import (
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
)


router = APIRouter(prefix="/departments", tags=["组织-部门"])


def _department_out(
    db: Session,
    dept: Department,
    *,
    managers: dict[int, User] | None = None,
    employee_counts: dict[int, int] | None = None,
    shift_counts: dict[int, int] | None = None,
) -> DepartmentOut:
    manager = None
    if dept.manager_user_id is not None:
        if managers is None:
            manager = db.get(User, dept.manager_user_id)
        else:
            manager = managers.get(dept.manager_user_id)
    if employee_counts is None:
        employee_count = db.execute(
            select(func.count())
            .select_from(User)
            .where(User.department_id == dept.id)
        ).scalar_one()
    else:
        employee_count = employee_counts.get(dept.id, 0)
    if shift_counts is None:
        shift_count = db.execute(
            select(func.count())
            .select_from(Shift)
            .where(Shift.department_id == dept.id)
        ).scalar_one()
    else:
        shift_count = shift_counts.get(dept.id, 0)
    return DepartmentOut(
        id=dept.id,
        name=dept.name,
        manager_user_id=dept.manager_user_id,
        manager_name=manager.name if manager else None,
        employee_count=employee_count,
        shift_count=shift_count,
        created_at=dept.created_at,
    )


def _assign_manager(db: Session, dept: Department, manager_user_id: int | None) -> None:
    if manager_user_id is None:
        dept.manager_user_id = None
        return

    manager = db.get(User, manager_user_id)
    if manager is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if manager.role != "department_manager":
        raise HTTPException(status_code=400, detail="只能指派部门管理员")
    if manager.department_id not in (None, dept.id):
        raise HTTPException(status_code=400, detail="所选账号不属于该部门")

    occupied = db.execute(
        select(Department).where(
            Department.manager_user_id == manager.id,
            Department.id != dept.id,
        )
    ).scalar_one_or_none()
    if occupied is not None:
        raise HTTPException(status_code=409, detail="该账号已是其他部门的管理员")

    if manager.department_id is None:
        manager.department_id = dept.id
    dept.manager_user_id = manager.id


@router.get("", response_model=list[DepartmentOut], summary="部门列表")
def list_departments(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    departments = db.execute(
        select(Department).order_by(Department.id)
    ).scalars().all()
    if not departments:
        return []

    manager_ids = [
        dept.manager_user_id
        for dept in departments
        if dept.manager_user_id is not None
    ]
    managers: dict[int, User] = {}
    if manager_ids:
        managers = {
            user.id: user
            for user in db.execute(
                select(User).where(User.id.in_(manager_ids))
            ).scalars()
        }
    employee_counts = {
        department_id: count
        for department_id, count in db.execute(
            select(User.department_id, func.count())
            .where(User.department_id.is_not(None))
            .group_by(User.department_id)
        ).all()
    }
    shift_counts = {
        department_id: count
        for department_id, count in db.execute(
            select(Shift.department_id, func.count())
            .group_by(Shift.department_id)
        ).all()
    }
    return [
        _department_out(
            db,
            dept,
            managers=managers,
            employee_counts=employee_counts,
            shift_counts=shift_counts,
        )
        for dept in departments
    ]


@router.get("/{department_id}", response_model=DepartmentOut, summary="部门详情")
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    return _department_out(db, dept)


@router.post(
    "",
    response_model=DepartmentOut,
    summary="新建部门",
    dependencies=[Depends(require_permission("department.manage"))],
)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    existing = db.execute(
        select(Department).where(Department.name == name)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="部门名称已存在")

    dept = Department(name=name)
    db.add(dept)
    db.flush()
    if payload.manager_user_id is not None:
        _assign_manager(db, dept, payload.manager_user_id)
    db.commit()
    db.refresh(dept)
    return _department_out(db, dept)


@router.patch(
    "/{department_id}",
    response_model=DepartmentOut,
    summary="更新部门",
    dependencies=[Depends(require_permission("department.manage"))],
)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
):
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="部门不存在")

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        existing = db.execute(
            select(Department).where(
                Department.name == name,
                Department.id != dept.id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="部门名称已存在")
        dept.name = name
    if "manager_user_id" in data:
        _assign_manager(db, dept, data["manager_user_id"])

    db.commit()
    db.refresh(dept)
    return _department_out(db, dept)


@router.delete(
    "/{department_id}",
    status_code=204,
    summary="删除部门",
    dependencies=[Depends(require_permission("department.manage"))],
)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
):
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=404, detail="部门不存在")

    employee_count = db.execute(
        select(func.count())
        .select_from(User)
        .where(User.department_id == dept.id)
    ).scalar_one()
    shift_count = db.execute(
        select(func.count())
        .select_from(Shift)
        .where(Shift.department_id == dept.id)
    ).scalar_one()
    if employee_count or shift_count:
        raise HTTPException(
            status_code=409,
            detail="请先移除该部门下的员工与班次",
        )

    db.delete(dept)
    db.commit()
