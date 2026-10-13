"""请假与外派申请的请求/响应结构（I5b）。"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class _DateRange(BaseModel):
    start_date: date
    end_date: date
    duration_days: float = Field(default=1.0, gt=0, le=30)
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def check_range(self):
        if self.end_date < self.start_date:
            raise ValueError("结束日期不能早于开始日期")
        return self


class LeaveCreate(_DateRange):
    leave_type: str = Field(min_length=1, max_length=20)


class TripCreate(_DateRange):
    pass


class ReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=500)


class RequestOut(BaseModel):
    id: int
    type: Literal["leave", "trip"]
    type_label: str
    employee_id: int
    employee_no: str | None = None
    employee_name: str | None = None
    department_id: int | None = None
    department_name: str | None = None
    start_date: date
    end_date: date
    duration_days: float
    reason: str | None = None
    status: str
    approver_name: str | None = None
    review_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
