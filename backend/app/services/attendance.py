"""考勤业务规则：班次匹配、打卡状态与月度汇总（I5）。"""

from calendar import monthrange
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attendance, Shift, User
from app.services.working_time import compute_working_minutes
from app.services.working_time import is_workday as shift_has_workday
from app.services.working_time import latest_attendance_status


class PunchConflict(Exception):
    """重复打卡等业务冲突，由路由转换为 409。"""


def parse_month(month: str | None, *, today: date | None = None) -> tuple[date, date]:
    """把 'YYYY-MM' 解析为当月首尾日期；留空取当前月。"""
    if not month:
        base = today or date.today()
        start = base.replace(day=1)
    else:
        try:
            year_text, month_text = month.split("-")
            year, month_number = int(year_text), int(month_text)
            start = date(year, month_number, 1)
        except (AttributeError, TypeError, ValueError):
            raise ValueError("month 需为 YYYY-MM 格式")
    return start, date(start.year, start.month, monthrange(start.year, start.month)[1])


def date_range(start: date, end: date):
    """按天迭代 [start, end]，供工作天数统计复用。"""
    current = start
    while current <= end:
        yield current
        current = date.fromordinal(current.toordinal() + 1)


def resolve_shift(db: Session, employee: User, work_date: date) -> Shift | None:
    """取员工所在部门在 work_date 已生效的最新班次。"""
    if employee.department_id is None:
        return None
    return db.execute(
        select(Shift)
        .where(
            Shift.department_id == employee.department_id,
            Shift.effective_from <= work_date,
        )
        .order_by(Shift.effective_from.desc(), Shift.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def is_workday_for(shift: Shift | None, work_date: date) -> bool:
    """无班次时按工作日处理，避免班次缺失导致整月都算缺勤。"""
    if shift is None:
        return True
    return shift_has_workday(shift.workdays, work_date.isoweekday())


def refresh_status(record: Attendance, shift: Shift | None) -> None:
    """按打卡时间与班次刷新状态和实际工时。"""
    is_late = bool(
        shift and record.sign_in_at and record.sign_in_at.time() > shift.work_start
    )
    is_early = bool(
        shift and record.sign_out_at and record.sign_out_at.time() < shift.work_end
    )
    record.status = latest_attendance_status(
        sign_in=record.sign_in_at is not None,
        sign_out=record.sign_out_at is not None,
        is_late=is_late,
        is_early=is_early,
    )
    if record.sign_in_at and record.sign_out_at:
        record.working_minutes = compute_working_minutes(
            record.sign_in_at,
            record.sign_out_at,
            shift.break_start if shift else None,
            shift.break_end if shift else None,
        )
    else:
        record.working_minutes = 0


def get_record(db: Session, employee_id: int, work_date: date) -> Attendance | None:
    return db.execute(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.work_date == work_date,
        )
    ).scalar_one_or_none()


def punch(
    db: Session,
    employee: User,
    punch_type: str,
    *,
    now: datetime | None = None,
) -> Attendance:
    """签到/签退：同一天复用一条记录，重复打卡返回冲突。"""
    at = now or datetime.now()
    work_date = at.date()
    shift = resolve_shift(db, employee, work_date)
    record = get_record(db, employee.id, work_date)
    if record is None:
        record = Attendance(
            employee_id=employee.id,
            work_date=work_date,
            shift_id=shift.id if shift else None,
            is_workday=is_workday_for(shift, work_date),
            status="partial",
        )
        db.add(record)

    if punch_type == "in":
        if record.sign_in_at is not None:
            raise PunchConflict("今日已签到")
        record.sign_in_at = at
    elif punch_type == "out":
        if record.sign_in_at is None:
            raise PunchConflict("请先签到再签退")
        if record.sign_out_at is not None:
            raise PunchConflict("今日已签退")
        record.sign_out_at = at
    else:
        raise ValueError(f"不支持的打卡类型：{punch_type}")

    record.shift_id = shift.id if shift else None
    record.is_workday = is_workday_for(shift, work_date)
    refresh_status(record, shift)
    db.commit()
    db.refresh(record)
    return record


def month_records(db: Session, employee_id: int, start: date, end: date) -> list[Attendance]:
    return list(
        db.execute(
            select(Attendance)
            .where(
                Attendance.employee_id == employee_id,
                Attendance.work_date >= start,
                Attendance.work_date <= end,
            )
            .order_by(Attendance.work_date.desc())
        ).scalars()
    )


def count_workdays(shift: Shift | None, start: date, end: date) -> int:
    """统计区间内应出勤天数；无班次时按周一至周五计算。"""
    total = 0
    for current in date_range(start, end):
        if shift is None:
            if current.isoweekday() <= 5:
                total += 1
        elif shift_has_workday(shift.workdays, current.isoweekday()):
            total += 1
    return total


def summarize(
    records: list[Attendance],
    shift: Shift | None,
    start: date,
    end: date,
) -> dict:
    # 只统计到"今天"为止的应出勤天数，避免当月未结束就把未来日期算成缺勤。
    today = date.today()
    effective_end = min(end, today)
    work_days = count_workdays(shift, start, effective_end) if start <= effective_end else 0

    # 迟到/早退当天仍然出勤，出勤率按"打了完整卡的天数"计算。
    attended_statuses = {"present", "late", "early_leave"}
    attended_days = sum(1 for item in records if item.status in attended_statuses)
    present_days = sum(1 for item in records if item.status == "present")
    late_count = sum(1 for item in records if item.status == "late")
    early_leave_count = sum(1 for item in records if item.status == "early_leave")
    absent_days = max(0, work_days - attended_days)
    worked = [item.working_minutes for item in records if item.working_minutes > 0]
    average_working_minutes = int(sum(worked) / len(worked)) if worked else 0
    attendance_rate = (
        round(min(100.0, attended_days / work_days * 100), 1) if work_days else 0.0
    )
    return {
        "work_days": work_days,
        "attended_days": attended_days,
        "present_days": present_days,
        "late_count": late_count,
        "early_leave_count": early_leave_count,
        "absent_days": absent_days,
        "average_working_minutes": average_working_minutes,
        "attendance_rate": attendance_rate,
    }
