"""pytest 公共测试依赖。"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password


PROJECT_TMP = Path(__file__).resolve().parent.parent / ".pytest_tmp"


@pytest.fixture
def tmp_path() -> Path:
    """覆盖内置 tmp_path：使用项目内可写目录，避免系统 Temp 权限问题。"""
    PROJECT_TMP.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(dir=PROJECT_TMP))


@pytest.fixture
def db_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    session = Session(db_engine)
    yield session
    session.close()


@pytest.fixture
def seed_user(db_session) -> User:
    user = User(
        employee_no="T0001",
        username="tester",
        password_hash=hash_password("secret123"),
        name="测试用户",
        role="employee",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def app_client(db_engine):
    """以 SQLite 覆盖 get_db 的 TestClient，避免连接真实 MySQL。"""

    def override_get_db():
        session = Session(db_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
