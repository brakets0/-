"""外派申请表。"""

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

from app.models.leave_request import REQUEST_STATUSES


class BusinessTrip(Base):
    __tablename__ = "business_trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[float] = mapped_column(
        Numeric(3, 1), default=1.0, nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(*REQUEST_STATUSES, name="request_status"),
        default="pending",
        nullable=False,
        index=True,
    )
    approver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    employee = relationship("User", foreign_keys=[employee_id])
    approver = relationship("User", foreign_keys=[approver_id])

