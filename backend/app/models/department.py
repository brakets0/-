"""部门表。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # 部门管理员用户 id；因 users.department_id 反向引用 departments.id，
    # 这里不建数据库外键，避免循环依赖，由服务层校验用户存在性。
    manager_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    employees = relationship("User", back_populates="department")
    shifts = relationship("Shift", back_populates="department")

