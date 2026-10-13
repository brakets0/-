"""考勤相关的请求与响应结构（I5）。"""

from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel


class PunchRequest(BaseModel):
    punch_type: Literal["in", "out"]


class PunchResponse(BaseModel):
    id: int
    work_date: date
    punch_type: str
    status: str
    is_workday: bool
    sign_in_at: datetime | None = None
    sign_out_at: datetime | None = None
    working_minutes: int
    shift_id: int | None = None
    shift_work_start: time | None = None
    shift_work_end: time | None = None


class AttendanceRecordOut(BaseModel):
    id: int
    work_date: date
    status: str
    is_workday: bool
    sign_in_at: datetime | None = None
    sign_out_at: datetime | None = None
    working_minutes: int
    shift_id: int | None = None
    shift_work_start: time | None = None
    shift_work_end: time | None = None


class AttendanceDayOut(BaseModel):
    """考勤中心按日期展示的单人记录；无记录时按班次推断是否缺勤。"""

    employee_id: int
    employee_no: str
    name: str
    department_id: int | None = None
    department_name: str | None = None
    work_date: date
    is_workday: bool
    has_record: bool
    status: str | None = None
    sign_in_at: datetime | None = None
    sign_out_at: datetime | None = None
    working_minutes: int = 0


class AttendanceSummaryOut(BaseModel):
    work_days: int
    attended_days: int
    present_days: int
    late_count: int
    early_leave_count: int
    absent_days: int
    average_working_minutes: int
    attendance_rate: float


class EmployeeAttendanceOut(BaseModel):
    employee_id: int
    employee_no: str
    name: str
    department_name: str | None = None
    month: str
    summary: AttendanceSummaryOut
    records: list[AttendanceRecordOut]
