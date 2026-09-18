"""班次管理路由（I4）：总管理员管理全部，部门管理员仅限本部门。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models import Attendance, Department, Shift
from app.schemas.organization import (
    ShiftCreate,
    ShiftOut,
    ShiftUpdate,
    _validate_times,
)


router = APIRouter(prefix="/shifts", tags=["组织-班次"])


def _shift_out(shift: Shift) -> ShiftOut:
    department = shift.department
    return ShiftOut(
        id=shift.id,
        department_id=shift.department_id,
        department_name=department.name if department else None,
        work_start=shift.work_start,
        work_end=shift.work_end,
        break_start=shift.break_start,
        break_end=shift.break_end,
        workdays=shift.workdays,
        effective_from=shift.effective_from,
        created_at=shift.created_at,
    )


def _require_own_department(user, department_id: int, *, message: str = "权限不足") -> None:
    if user.role != "general_admin" and department_id != user.department_id:
        raise HTTPException(status_code=403, detail=message)


@router.get("", response_model=list[ShiftOut], summary="班次列表")
def list_shifts(
    db: Session = Depends(get_db),
    user=Depends(require_permission("shift.manage.department")),
):
    stmt = select(Shift).options(selectinload(Shift.department)).order_by(
        Shift.department_id, Shift.effective_from
    )
    if user.role != "general_admin":
        stmt = stmt.where(Shift.department_id == user.department_id)
    shifts = db.execute(stmt).scalars().all()
    return [_shift_out(shift) for shift in shifts]


@router.post("", response_model=ShiftOut, summary="新建班次")
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("shift.manage.department")),
):
    _require_own_department(user, payload.department_id, message="只能管理本部门班次")
    department = db.get(Department, payload.department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="部门不存在")

    duplicate = db.execute(
        select(Shift).where(
            Shift.department_id == payload.department_id,
            Shift.effective_from == payload.effective_from,
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail="该部门在此生效日期已存在班次",
        )

    shift = Shift(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return _shift_out(shift)


@router.patch("/{shift_id}", response_model=ShiftOut, summary="更新班次")
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("shift.manage.department")),
):
    shift = db.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="班次不存在")
    _require_own_department(user, shift.department_id, message="只能管理本部门班次")

    data = payload.model_dump(exclude_unset=True)
    next_department_id = data.get("department_id", shift.department_id)
    _require_own_department(user, next_department_id, message="不能将班次移到其他部门")
    if next_department_id != shift.department_id:
        department = db.get(Department, next_department_id)
        if department is None:
            raise HTTPException(status_code=404, detail="部门不存在")

    next_effective_from = data.get("effective_from", shift.effective_from)
    duplicate = db.execute(
        select(Shift).where(
            Shift.department_id == next_department_id,
            Shift.effective_from == next_effective_from,
            Shift.id != shift.id,
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail="该部门在此生效日期已存在班次",
        )

    merged_times = {
        "work_start": data.get("work_start", shift.work_start),
        "work_end": data.get("work_end", shift.work_end),
        "break_start": data.get("break_start", shift.break_start),
        "break_end": data.get("break_end", shift.break_end),
    }
    try:
        _validate_times(merged_times)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    for key, value in data.items():
        setattr(shift, key, value)
    db.commit()
    db.refresh(shift)
    return _shift_out(shift)


@router.delete(
    "/{shift_id}",
    status_code=204,
    summary="删除班次",
)
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("shift.manage.department")),
):
    shift = db.get(Shift, shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="班次不存在")
    _require_own_department(user, shift.department_id, message="只能管理本部门班次")

    referenced = db.execute(
        select(Attendance).where(Attendance.shift_id == shift_id).limit(1)
    ).scalar_one_or_none()
    if referenced is not None:
        raise HTTPException(
            status_code=409,
            detail="已有考勤记录引用该班次，不能删除",
        )

    db.delete(shift)
    db.commit()
