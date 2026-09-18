"""I2：种子数据幂等性与依赖完整性测试。"""

from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Department, Shift, User
from app.seed import hash_password, seed_data


def test_hash_password_works():
    h = hash_password("admin123")
    assert h != "admin123"
    assert h.startswith("$2")


def test_seed_creates_roles_and_is_idempotent():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    from app.database import Base

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_data(db)
        assert db.execute(select(User).where(User.role == "general_admin")).scalar_one()
        assert db.execute(select(User).where(User.role == "department_manager")).scalar_one()
        assert db.execute(select(User).where(User.role == "employee")).scalar_one()
        assert db.execute(select(Department).where(Department.name == "技术部")).scalar_one()
        assert db.execute(select(Shift)).scalars().all()

    # 再次执行不应新增重复用户
    with Session(engine) as db:
        seed_data(db)
        assert len(db.execute(select(User)).scalars().all()) == 3

