"""员工/管理员账号表。"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


USER_ROLES = ("employee", "department_manager", "general_admin")
USER_STATUSES = ("active", "inactive")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(*USER_ROLES, name="user_role"), nullable=False
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active", nullable=False
    )
    face_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    face_registered_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    department = relationship("Department", back_populates="employees")

    @property
    def department_name(self) -> str | None:
        """供账号资料接口直接返回所属部门名称。"""
        return self.department.name if self.department else None

    @property
    def face_registered(self) -> bool:
        """是否已完成人脸注册（仅供前端展示绑定状态）。"""
        return bool(self.face_token)
