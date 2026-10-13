"""月度考勤报表聚合（I5c）。

报表以部门为单位聚合，数据全部来自考勤、请假、外派真实记录：
- 应出勤/缺勤按员工班次工作日规则推算，与「我的考勤」口径保持一致；
- 请假/外派按与统计区间重叠的工作日天数折算；
- 平均出勤率 = 出勤天数 / 应出勤天数，迟到、早退当天仍计出勤。
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Attendance,
    BusinessTrip,
    LeaveRequest,
    Shift,
    User,
)
from app.permissions import ATTENDANCE_STAT_ROLES
from app.services import attendance as attendance_service
from app.services.attendance import date_range


ATTENDED_STATUSES = {"present", "late", "early_leave"}


def _overlap_workdays(
    start: date,
    end: date,
    shift: Shift | None,
) -> float:
    """统计请假/外派与统计区间重叠的工作日天数。"""
    if end < start:
        return 0.0
    return float(attendance_service.count_workdays(shift, start, end))


def _latest_shifts(db: Session) -> dict[int, Shift]:
    """取每个部门区间内最新生效班次，供工作日推算使用。"""
    rows = db.execute(
        select(Shift).order_by(Shift.department_id, Shift.effective_from.desc(), Shift.id.desc())
    ).scalars()
    shifts: dict[int, Shift] = {}
    for shift in rows:
        shifts.setdefault(shift.department_id, shift)
    return shifts


def _summarize_department(
    employees: list[User],
    attendance_by_employee: dict[int, list[Attendance]],
    leave_by_employee: dict[int, list[LeaveRequest]],
    trip_by_employee: dict[int, list[BusinessTrip]],
    shift: Shift | None,
    start: date,
    end: date,
) -> dict:
    employee_count = len(employees)
    work_days = attendance_service.count_workdays(shift, start, end) * employee_count

    attended_days = 0
    present_days = 0
    late_count = 0
    early_leave_count = 0
    absent_days = 0
    worked_minutes: list[int] = []

    for employee in employees:
        records = attendance_by_employee.get(employee.id, [])
        for record in records:
            if not record.is_workday:
                continue
            if record.status in ATTENDED_STATUSES:
                attended_days += 1
            if record.status == "present":
                present_days += 1
            elif record.status == "late":
                late_count += 1
            elif record.status == "early_leave":
                early_leave_count += 1
            elif record.status in {"absent", "partial"}:
                absent_days += 1
            if record.working_minutes > 0:
                worked_minutes.append(record.working_minutes)

        recorded_dates = {record.work_date for record in records}
        for current in date_range(start, end):
            if current in recorded_dates:
                continue
            if attendance_service.is_workday_for(shift, current):
                absent_days += 1

    leave_days = sum(
        _overlap_workdays(max(item.start_date, start), min(item.end_date, end), shift)
        for employee in employees
        for item in leave_by_employee.get(employee.id, [])
    )
    trip_days = sum(
        _overlap_workdays(max(item.start_date, start), min(item.end_date, end), shift)
        for employee in employees
        for item in trip_by_employee.get(employee.id, [])
    )

    average_working_minutes = (
        int(sum(worked_minutes) / len(worked_minutes)) if worked_minutes else 0
    )
    attendance_rate = (
        round(min(100.0, attended_days / work_days * 100), 1) if work_days else 0.0
    )
    return {
        "employee_count": employee_count,
        "work_days": work_days,
        "attended_days": attended_days,
        "present_days": present_days,
        "late_count": late_count,
        "early_leave_count": early_leave_count,
        "absent_days": absent_days,
        "average_working_minutes": average_working_minutes,
        "attendance_rate": attendance_rate,
        "leave_days": round(leave_days, 1),
        "trip_days": round(trip_days, 1),
    }


def department_reports(
    db: Session,
    start: date,
    end: date,
    *,
    department_id: int | None = None,
) -> list[dict]:
    """按部门聚合区间报表；department_id 为空时返回全公司。"""
    employee_stmt = (
        select(User)
        .options(selectinload(User.department))
        .where(User.role.in_(ATTENDANCE_STAT_ROLES), User.status == "active")
        .order_by(User.employee_no)
    )
    if department_id is not None:
        employee_stmt = employee_stmt.where(User.department_id == department_id)
    employees = list(db.execute(employee_stmt).scalars())
    if not employees:
        return []

    employee_ids = [employee.id for employee in employees]
    shifts = _latest_shifts(db)

    records = list(
        db.execute(
            select(Attendance)
            .options(selectinload(Attendance.shift))
            .where(
                Attendance.employee_id.in_(employee_ids),
                Attendance.work_date >= start,
                Attendance.work_date <= end,
            )
        ).scalars()
    )
    attendance_by_employee: dict[int, list[Attendance]] = {}
    for record in records:
        attendance_by_employee.setdefault(record.employee_id, []).append(record)

    leaves = list(
        db.execute(
            select(LeaveRequest).where(
                LeaveRequest.employee_id.in_(employee_ids),
                LeaveRequest.start_date <= end,
                LeaveRequest.end_date >= start,
            )
        ).scalars()
    )
    leave_by_employee: dict[int, list[LeaveRequest]] = {}
    for leave in leaves:
        leave_by_employee.setdefault(leave.employee_id, []).append(leave)

    trips = list(
        db.execute(
            select(BusinessTrip).where(
                BusinessTrip.employee_id.in_(employee_ids),
                BusinessTrip.start_date <= end,
                BusinessTrip.end_date >= start,
            )
        ).scalars()
    )
    trip_by_employee: dict[int, list[BusinessTrip]] = {}
    for trip in trips:
        trip_by_employee.setdefault(trip.employee_id, []).append(trip)

    grouped: dict[int | None, list[User]] = {}
    for employee in employees:
        grouped.setdefault(employee.department_id, []).append(employee)

    rows: list[dict] = []
    for dept_id, dept_employees in grouped.items():
        shift = shifts.get(dept_id) if dept_id is not None else None
        summary = _summarize_department(
            dept_employees,
            attendance_by_employee,
            leave_by_employee,
            trip_by_employee,
            shift,
            start,
            end,
        )
        department = dept_employees[0].department
        rows.append(
            {
                "department_id": dept_id,
                "department_name": department.name if department else "未分配部门",
                **summary,
            }
        )
    rows.sort(key=lambda item: item["department_name"])
    return rows
