"""组织与班次相关的请求与响应结构（I4）。"""

from datetime import date, datetime, time

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)


def normalize_workdays(value: str) -> str:
    """校验并归一化班次工作日字符串：1=周一 ... 7=周日。"""
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise ValueError("workdays 不能为空")

    days: set[int] = set()
    for part in parts:
        try:
            day = int(part)
        except (TypeError, ValueError):
            raise ValueError("workdays 只能包含 1-7 的数字")
        if day < 1 or day > 7:
            raise ValueError("workdays 只能包含 1-7 的数字")
        if day in days:
            raise ValueError("workdays 不能包含重复的工作日")
        days.add(day)

    return ",".join(str(day) for day in sorted(days))


def _strip_required(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} 不能为空")
    return value


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    manager_user_id: int | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return _strip_required(value, "name")


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    manager_user_id: int | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _strip_required(value, "name")


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    manager_user_id: int | None = None
    manager_name: str | None = None
    employee_count: int = 0
    shift_count: int = 0
    created_at: datetime


class EmployeeCreate(BaseModel):
    employee_no: str = Field(min_length=1, max_length=50)
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=50)
    role: str = Field(
        default="employee",
        pattern=r"^(employee|department_manager|general_admin)$",
    )
    department_id: int | None = None
    status: str = Field(default="active", pattern=r"^(active|inactive)$")

    @field_validator("employee_no", "username", "name")
    @classmethod
    def strip_text(cls, value: str, info: ValidationInfo) -> str:
        return _strip_required(value, info.field_name)


class EmployeeUpdate(BaseModel):
    employee_no: str | None = Field(default=None, min_length=1, max_length=50)
    username: str | None = Field(default=None, min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    name: str | None = Field(default=None, min_length=1, max_length=50)
    role: str | None = Field(
        default=None,
        pattern=r"^(employee|department_manager|general_admin)$",
    )
    department_id: int | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")

    @field_validator("employee_no", "username", "name")
    @classmethod
    def strip_text(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is None:
            return None
        return _strip_required(value, info.field_name)


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_no: str
    username: str
    name: str
    role: str
    department_id: int | None = None
    department_name: str | None = None
    status: str
    created_at: datetime


def _validate_times(values: dict) -> dict:
    work_start = values.get("work_start")
    work_end = values.get("work_end")
    if work_start is not None and work_end is not None and work_end <= work_start:
        raise ValueError("work_end 必须晚于 work_start")

    break_start = values.get("break_start")
    break_end = values.get("break_end")
    if (break_start is None) != (break_end is None):
        raise ValueError("break_start 与 break_end 必须同时填写或同时留空")
    if break_start is not None and break_end is not None:
        if break_end <= break_start:
            raise ValueError("break_end 必须晚于 break_start")
        if work_start is not None and work_end is not None:
            if not (work_start <= break_start < break_end <= work_end):
                raise ValueError("午休时间必须落在工作时间内")
    return values


class ShiftCreate(BaseModel):
    department_id: int
    work_start: time
    work_end: time
    break_start: time | None = None
    break_end: time | None = None
    workdays: str = "1,2,3,4,5"
    effective_from: date

    @field_validator("workdays")
    @classmethod
    def validate_workdays(cls, value: str) -> str:
        return normalize_workdays(value)

    @model_validator(mode="after")
    def validate_shift_times(self):
        _validate_times(self.model_dump())
        return self


class ShiftUpdate(BaseModel):
    department_id: int | None = None
    work_start: time | None = None
    work_end: time | None = None
    break_start: time | None = None
    break_end: time | None = None
    workdays: str | None = None
    effective_from: date | None = None

    @field_validator("workdays")
    @classmethod
    def validate_workdays(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_workdays(value)

    @model_validator(mode="after")
    def validate_shift_times(self):
        _validate_times(self.model_dump())
        return self


class ShiftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    department_name: str | None = None
    work_start: time
    work_end: time
    break_start: time | None = None
    break_end: time | None = None
    workdays: str
    effective_from: date
    created_at: datetime
