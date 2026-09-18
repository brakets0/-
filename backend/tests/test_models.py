"""I2：SQLAlchemy 模型、约束与 metadata 完整性测试。"""

from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import inspect

from app import models
from app.database import Base


def test_all_models_are_registered():
    expected = {
        "departments",
        "users",
        "shifts",
        "leave_requests",
        "business_trips",
        "attendance",
    }
    assert expected <= set(Base.metadata.tables)


def test_attendance_unique_and_fields():
    att = Base.metadata.tables["attendance"]
    expected_plain = {
        ("employee_id", "INTEGER"),
        ("work_date", "DATE"),
        ("shift_id", "INTEGER"),
        ("sign_in_at", "DATETIME"),
        ("sign_out_at", "DATETIME"),
        ("working_minutes", "INTEGER"),
    }
    compiled = {
        c.name: c.type.compile(dialect=None) if c.type.__class__.__name__ != "Enum" else "ENUM"
        for c in att.columns
    }
    assert {(name, compiled[name]) for name, _ in expected_plain} >= expected_plain
    assert compiled["status"] == "ENUM"
    assert set(att.c.status.type.enums) == {
        "present",
        "late",
        "early_leave",
        "absent",
        "partial",
    }


def test_shift_workdays_default_and_unique():
    shift = Base.metadata.tables["shifts"]
    workdays_col = shift.columns["workdays"]
    assert workdays_col.server_default.arg in ("'1,2,3,4,5'", "1,2,3,4,5")
    assert any(
        uc.name == "uq_shift_department_effective_from"
        for uc in shift.constraints
        if hasattr(uc, "name")
    )


def test_foreign_keys_present():
    leave = Base.metadata.tables["leave_requests"]
    has_column_fk = any(isinstance(c, ForeignKey) for c in leave.columns.values())
    has_table_fk = any(
        isinstance(constraint, ForeignKeyConstraint)
        for constraint in leave.constraints
    )
    assert has_column_fk or has_table_fk


def test_roles_and_statuses():
    user = Base.metadata.tables["users"]
    role_col = user.columns["role"]
    assert set(role_col.type.enums) == {"employee", "department_manager", "general_admin"}
