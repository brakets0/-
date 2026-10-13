"""报表相关的响应结构（I5c）。"""

from datetime import date

from pydantic import BaseModel


class DepartmentReportOut(BaseModel):
    """按部门聚合的月度考勤报表行。"""

    department_id: int | None = None
    department_name: str
    employee_count: int
    work_days: int
    attended_days: int
    present_days: int
    late_count: int
    early_leave_count: int
    absent_days: int
    average_working_minutes: int
    attendance_rate: float
    leave_days: float
    trip_days: float


class MonthlyReportOut(BaseModel):
    month: str
    start_date: date
    end_date: date
    scope_label: str
    rows: list[DepartmentReportOut]
