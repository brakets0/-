"""考勤路由（I5）：签到签退、个人考勤、部门考勤与个人考勤明细。"""

from datetime import date as DateType

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import require_permission
from app.models import Attendance, User
from app.permissions import ATTENDANCE_STAT_ROLES, is_attendance_subject
from app.schemas.attendance import (
    AttendanceDayOut,
    AttendanceRecordOut,
    EmployeeAttendanceOut,
    PunchRequest,
    PunchResponse,
)
from app.services import attendance as attendance_service
from app.services.attendance import PunchConflict


router = APIRouter(prefix="/attendance", tags=["考勤"])


def _record_out(record: Attendance) -> AttendanceRecordOut:
    shift = record.shift
    return AttendanceRecordOut(
        id=record.id,
        work_date=record.work_date,
        status=record.status,
        is_workday=record.is_workday,
        sign_in_at=record.sign_in_at,
        sign_out_at=record.sign_out_at,
        working_minutes=record.working_minutes,
        shift_id=record.shift_id,
        shift_work_start=shift.work_start if shift else None,
        shift_work_end=shift.work_end if shift else None,
    )


def _punch_out(record: Attendance, punch_type: str) -> PunchResponse:
    shift = record.shift
    return PunchResponse(
        id=record.id,
        work_date=record.work_date,
        punch_type=punch_type,
        status=record.status,
        is_workday=record.is_workday,
        sign_in_at=record.sign_in_at,
        sign_out_at=record.sign_out_at,
        working_minutes=record.working_minutes,
        shift_id=record.shift_id,
        shift_work_start=shift.work_start if shift else None,
        shift_work_end=shift.work_end if shift else None,
    )


def _employee_attendance(
    db: Session, employee: User, month: str | None
) -> EmployeeAttendanceOut:
    try:
        start, end = attendance_service.parse_month(month)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    records = attendance_service.month_records(db, employee.id, start, end)
    shift = attendance_service.resolve_shift(db, employee, end)
    summary = attendance_service.summarize(records, shift, start, end)
    department = employee.department
    return EmployeeAttendanceOut(
        employee_id=employee.id,
        employee_no=employee.employee_no,
        name=employee.name,
        department_name=department.name if department else None,
        month=f"{start.year:04d}-{start.month:02d}",
        summary=summary,
        records=[_record_out(record) for record in records],
    )


@router.post(
    "/punch",
    response_model=PunchResponse,
    summary="打卡（签到/签退）",
)
def punch(
    payload: PunchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attendance.sign")),
):
    if not is_attendance_subject(user.role):
        raise HTTPException(status_code=403, detail="总管理员不参与考勤")
    try:
        record = attendance_service.punch(db, user, payload.punch_type)
    except PunchConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _punch_out(record, payload.punch_type)


@router.get(
    "/me",
    response_model=EmployeeAttendanceOut,
    summary="我的考勤（按月）",
)
def my_attendance(
    month: str | None = Query(None, description="YYYY-MM，默认当前月"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attendance.view.self")),
):
    if not is_attendance_subject(user.role):
        raise HTTPException(status_code=403, detail="总管理员不参与考勤")
    return _employee_attendance(db, user, month)


@router.get(
    "",
    response_model=list[AttendanceDayOut],
    summary="考勤中心按日期查询",
)
def list_attendance(
    target_date: str | None = Query(None, alias="date", description="YYYY-MM-DD"),
    department_id: int | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attendance.view.department")),
):
    if target_date:
        try:
            work_date = DateType.fromisoformat(target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="date 需为 YYYY-MM-DD 格式")
    else:
        work_date = DateType.today()

    scope_department = department_id
    if user.role != "general_admin":
        if user.department_id is None:
            return []
        scope_department = user.department_id

    stmt = (
        select(User)
        .options(selectinload(User.department))
        .where(
            User.role.in_(ATTENDANCE_STAT_ROLES),
            User.status == "active",
        )
        .order_by(User.employee_no)
    )
    if scope_department is not None:
        stmt = stmt.where(User.department_id == scope_department)
    employees = list(db.execute(stmt).scalars())
    if not employees:
        return []

    records = list(
        db.execute(
            select(Attendance)
            .options(selectinload(Attendance.shift))
            .where(
                Attendance.work_date == work_date,
                Attendance.employee_id.in_([item.id for item in employees]),
            )
        ).scalars()
    )
    by_employee = {record.employee_id: record for record in records}

    rows: list[AttendanceDayOut] = []
    for employee in employees:
        record = by_employee.get(employee.id)
        if record is not None:
            is_workday = record.is_workday
            status = record.status
        else:
            shift = attendance_service.resolve_shift(db, employee, work_date)
            is_workday = attendance_service.is_workday_for(shift, work_date)
            status = "absent" if is_workday else None
        rows.append(
            AttendanceDayOut(
                employee_id=employee.id,
                employee_no=employee.employee_no,
                name=employee.name,
                department_id=employee.department_id,
                department_name=employee.department.name
                if employee.department
                else None,
                work_date=work_date,
                is_workday=is_workday,
                has_record=record is not None,
                status=status,
                sign_in_at=record.sign_in_at if record else None,
                sign_out_at=record.sign_out_at if record else None,
                working_minutes=record.working_minutes if record else 0,
            )
        )
    return rows


@router.get(
    "/employee/{employee_id}",
    response_model=EmployeeAttendanceOut,
    summary="指定员工的月度考勤明细",
)
def employee_attendance(
    employee_id: int,
    month: str | None = Query(None, description="YYYY-MM，默认当前月"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("attendance.view.department")),
):
    employee = db.get(User, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="员工不存在")
    if not is_attendance_subject(employee.role):
        raise HTTPException(status_code=400, detail="该账号不参与考勤")
    if user.role != "general_admin" and employee.department_id != user.department_id:
        raise HTTPException(status_code=403, detail="只能查看本部门员工考勤")
    return _employee_attendance(db, employee, month)
