"""考勤表。"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


ATTENDANCE_STATUSES = ("present", "late", "early_leave", "absent", "partial")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint(
            "employee_id", "work_date", name="uq_attendance_employee_work_date"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # 记录当天实际适用的班次，便于历史追溯
    shift_id: Mapped[int | None] = mapped_column(
        ForeignKey("shifts.id"), nullable=True
    )
    is_workday: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )
    sign_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sign_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(*ATTENDANCE_STATUSES, name="attendance_status"),
        default="partial",
        nullable=False,
    )
    working_minutes: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    leave_id: Mapped[int | None] = mapped_column(
        ForeignKey("leave_requests.id"), nullable=True
    )
    trip_id: Mapped[int | None] = mapped_column(
        ForeignKey("business_trips.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employee = relationship("User", foreign_keys=[employee_id])
    shift = relationship("Shift")
    leave_request = relationship("LeaveRequest", foreign_keys=[leave_id])
    business_trip = relationship("BusinessTrip", foreign_keys=[trip_id])

