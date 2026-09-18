"""演示数据种子脚本：幂等，可重复执行。"""

from datetime import date, time
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Department, Shift, User
from app.security import hash_password


DEMO_EFFECTIVE_FROM = date(2020, 1, 1)
DEFAULTS = {
    "admin": {"employee_no": "A00001", "password": "admin123"},
    "manager": {"employee_no": "A00002", "password": "manager123"},
    "employee": {"employee_no": "E00001", "password": "employee123"},
}
def _get_or_create_department(db, name: str) -> Department:
    dept = db.execute(select(Department).where(Department.name == name)).scalar_one_or_none()
    if dept is None:
        dept = Department(name=name)
        db.add(dept)
        db.flush()
    return dept


def _get_or_create_user(db, username: str, *, department_id=None, role: str) -> User:
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        options = DEFAULTS[username]
        user = User(
            employee_no=options["employee_no"],
            username=username,
            password_hash=hash_password(options["password"]),
            name=username,
            role=role,
            department_id=department_id,
        )
        db.add(user)
        db.flush()
    return user


def _get_or_create_shift(db, department_id: int) -> Shift:
    shift = db.execute(
        select(Shift).where(
            Shift.department_id == department_id,
            Shift.effective_from == DEMO_EFFECTIVE_FROM,
        )
    ).scalar_one_or_none()
    if shift is None:
        shift = Shift(
            department_id=department_id,
            work_start=time(9, 0),
            work_end=time(18, 0),
            break_start=time(12, 0),
            break_end=time(13, 0),
            workdays="1,2,3,4,5",
            effective_from=DEMO_EFFECTIVE_FROM,
        )
        db.add(shift)
        db.flush()
    return shift


def seed_data(db):
    """创建总管理员、演示部门、部门管理员、普通员工和默认班次。"""
    tech = _get_or_create_department(db, "技术部")
    hr = _get_or_create_department(db, "人事部")

    admin = _get_or_create_user(db, "admin", role="general_admin")
    manager = _get_or_create_user(
        db, "manager", department_id=tech.id, role="department_manager"
    )
    employee = _get_or_create_user(
        db, "employee", department_id=tech.id, role="employee"
    )

    tech.manager_user_id = manager.id
    _get_or_create_shift(db, tech.id)
    _get_or_create_shift(db, hr.id)

    db.commit()
    return admin, manager, employee


if __name__ == "__main__":
    session = SessionLocal()
    try:
        seed_data(session)
        print("演示数据写入完成。")
    finally:
        session.close()
