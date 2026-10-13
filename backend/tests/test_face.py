"""I6：人脸注册权限、绑定状态与人脸打卡（百度接口用 fake 替换）。"""

from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session

from app.main import app
from app.models import Department, User
from app.security import create_access_token, hash_password
from app.services.baidu_face import FaceServiceError, get_face_client


IMAGE = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2w=="


@dataclass
class Actor:
    id: int
    role: str
    department_id: int | None = None


def _headers(actor: Actor) -> dict:
    token = create_access_token(user_id=actor.id, role=actor.role)
    return {"Authorization": f"Bearer {token}"}


def _user(db, *, employee_no, username, role, department_id=None):
    user = User(
        employee_no=employee_no,
        username=username,
        password_hash=hash_password("secret123"),
        name=username,
        role=role,
        department_id=department_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed(db_engine):
    with Session(db_engine) as db:
        tech = Department(name="技术部")
        hr = Department(name="人事部")
        db.add_all([tech, hr])
        db.commit()
        db.refresh(tech)
        db.refresh(hr)
        admin = _user(db, employee_no="A1", username="admin", role="general_admin")
        manager = _user(
            db,
            employee_no="A2",
            username="manager",
            role="department_manager",
            department_id=tech.id,
        )
        worker = _user(
            db,
            employee_no="E1",
            username="worker",
            role="employee",
            department_id=tech.id,
        )
        outsider = _user(
            db,
            employee_no="E2",
            username="outsider",
            role="employee",
            department_id=hr.id,
        )
        return {
            "admin": Actor(admin.id, admin.role),
            "manager": Actor(manager.id, manager.role, tech.id),
            "worker": Actor(worker.id, worker.role, tech.id),
            "outsider": Actor(outsider.id, outsider.role, hr.id),
        }


class FakeBaiduFaceClient:
    """模拟百度云：不触网，按配置返回注册 token 或检索结果。"""

    def __init__(self, *, score: float = 95.0, user_id: str | None = "E1"):
        self.score = score
        self.user_id = user_id
        self.registered: dict[str, str] = {}
        self.search_calls = 0

    def add_face(self, user_id: str, image: str) -> str:
        token = f"token-{user_id}-{len(self.registered) + 1}"
        self.registered[user_id] = token
        return token

    def search(self, image: str, *, user_id: str | None = None) -> dict:
        self.search_calls += 1
        if self.user_id is None:
            raise FaceServiceError(222208, "人脸库中未匹配到该员工")
        return {"user_id": self.user_id, "score": self.score, "face_token": "t"}


@pytest.fixture
def face_client():
    client = FakeBaiduFaceClient()
    app.dependency_overrides[get_face_client] = lambda: client
    yield client
    app.dependency_overrides.pop(get_face_client, None)


def test_register_requires_login(app_client, db_engine, face_client):
    _seed(db_engine)
    response = app_client.post("/api/face/register", json={"image": IMAGE})
    assert response.status_code == 401


def test_employee_cannot_self_register(app_client, db_engine, face_client):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/face/register",
        json={"image": IMAGE},
        headers=_headers(actors["worker"]),
    )
    assert response.status_code == 403


def test_manager_registers_own_department(app_client, db_engine, face_client):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/face/register",
        json={"employee_id": actors["worker"].id, "image": IMAGE},
        headers=_headers(actors["manager"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["employee_no"] == "E1"
    assert body["face_registered"] is True
    assert body["face_registered_at"] is not None

    status = app_client.get("/api/face/me", headers=_headers(actors["worker"]))
    assert status.json()["face_registered"] is True


def test_manager_cannot_register_other_department(app_client, db_engine, face_client):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/face/register",
        json={"employee_id": actors["outsider"].id, "image": IMAGE},
        headers=_headers(actors["manager"]),
    )
    assert response.status_code == 403


def test_admin_can_register_any_employee(app_client, db_engine, face_client):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/face/register",
        json={"employee_id": actors["outsider"].id, "image": IMAGE},
        headers=_headers(actors["admin"]),
    )
    assert response.status_code == 200
    assert response.json()["employee_no"] == "E2"


def test_face_attendance_requires_registration(app_client, db_engine, face_client):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/face/attendance",
        json={"punch_type": "in", "image": IMAGE},
        headers=_headers(actors["worker"]),
    )
    assert response.status_code == 404


def test_face_attendance_punch_in_and_conflict(app_client, db_engine, face_client):
    actors = _seed(db_engine)
    app_client.post(
        "/api/face/register",
        json={"employee_id": actors["worker"].id, "image": IMAGE},
        headers=_headers(actors["manager"]),
    )

    first = app_client.post(
        "/api/face/attendance",
        json={"punch_type": "in", "image": IMAGE},
        headers=_headers(actors["worker"]),
    )
    assert first.status_code == 200
    body = first.json()
    assert body["employee_no"] == "E1"
    assert body["punch_type"] == "in"
    assert body["score"] == 95.0
    assert body["sign_in_at"] is not None

    again = app_client.post(
        "/api/face/attendance",
        json={"punch_type": "in", "image": IMAGE},
        headers=_headers(actors["worker"]),
    )
    assert again.status_code == 409


def test_face_attendance_rejects_low_score(app_client, db_engine, face_client):
    face_client.score = 60.0
    actors = _seed(db_engine)
    app_client.post(
        "/api/face/register",
        json={"employee_id": actors["worker"].id, "image": IMAGE},
        headers=_headers(actors["manager"]),
    )
    response = app_client.post(
        "/api/face/attendance",
        json={"punch_type": "in", "image": IMAGE},
        headers=_headers(actors["worker"]),
    )
    assert response.status_code == 401


def test_face_attendance_rejects_wrong_user(app_client, db_engine, face_client):
    face_client.user_id = "E2"
    actors = _seed(db_engine)
    app_client.post(
        "/api/face/register",
        json={"employee_id": actors["worker"].id, "image": IMAGE},
        headers=_headers(actors["manager"]),
    )
    response = app_client.post(
        "/api/face/attendance",
        json={"punch_type": "in", "image": IMAGE},
        headers=_headers(actors["worker"]),
    )
    assert response.status_code == 401


def test_invalid_image_payload_returns_422(app_client, db_engine, face_client):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/face/register",
        json={"employee_id": actors["worker"].id, "image": "not-an-image"},
        headers=_headers(actors["manager"]),
    )
    assert response.status_code == 422
