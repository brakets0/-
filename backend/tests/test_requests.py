"""I5b：请假与外派申请、范围过滤与审批权限测试。"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Department, User
from app.security import create_access_token, hash_password


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
        employee = _user(
            db, employee_no="E1", username="employee", role="employee", department_id=tech.id
        )
        hr_employee = _user(
            db, employee_no="E2", username="hr", role="employee", department_id=hr.id
        )
        return {
            "admin": Actor(admin.id, admin.role),
            "manager": Actor(manager.id, manager.role, tech.id),
            "employee": Actor(employee.id, employee.role, tech.id),
            "hr_employee": Actor(hr_employee.id, hr_employee.role, hr.id),
        }


LEAVE_PAYLOAD = {
    "leave_type": "年假",
    "start_date": "2026-11-02",
    "end_date": "2026-11-03",
    "duration_days": 2,
    "reason": "家庭安排",
}

TRIP_PAYLOAD = {
    "start_date": "2026-11-05",
    "end_date": "2026-11-05",
    "duration_days": 1,
    "reason": "客户现场支持",
}


def test_create_leave_requires_login(app_client, db_engine):
    _seed(db_engine)
    assert app_client.post("/api/leave-requests", json=LEAVE_PAYLOAD).status_code == 401


def test_create_leave_and_scope_of_list(app_client, db_engine):
    actors = _seed(db_engine)
    created = app_client.post(
        "/api/leave-requests",
        json=LEAVE_PAYLOAD,
        headers=_headers(actors["employee"]),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["type"] == "leave"
    assert body["type_label"] == "年假"
    assert body["status"] == "pending"
    assert body["department_name"] == "技术部"

    app_client.post(
        "/api/leave-requests",
        json={**LEAVE_PAYLOAD, "leave_type": "事假"},
        headers=_headers(actors["hr_employee"]),
    )

    own = app_client.get("/api/leave-requests", headers=_headers(actors["employee"]))
    assert [item["employee_no"] for item in own.json()] == ["E1"]

    department = app_client.get(
        "/api/leave-requests", headers=_headers(actors["manager"])
    )
    assert {item["employee_no"] for item in department.json()} == {"E1"}

    all_items = app_client.get(
        "/api/leave-requests", headers=_headers(actors["admin"])
    )
    assert {item["employee_no"] for item in all_items.json()} == {"E1", "E2"}

    pending = app_client.get(
        "/api/leave-requests?status=pending", headers=_headers(actors["admin"])
    )
    assert len(pending.json()) == 2
    approved = app_client.get(
        "/api/leave-requests?status=approved", headers=_headers(actors["admin"])
    )
    assert approved.json() == []


def test_review_leave_permissions_and_conflict(app_client, db_engine):
    actors = _seed(db_engine)
    request_id = app_client.post(
        "/api/leave-requests",
        json=LEAVE_PAYLOAD,
        headers=_headers(actors["employee"]),
    ).json()["id"]

    denied_self = app_client.patch(
        f"/api/leave-requests/{request_id}/review",
        json={"status": "approved"},
        headers=_headers(actors["employee"]),
    )
    assert denied_self.status_code == 403

    reviewed = app_client.patch(
        f"/api/leave-requests/{request_id}/review",
        json={"status": "approved", "review_note": "同意"},
        headers=_headers(actors["manager"]),
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "approved"
    assert reviewed.json()["approver_name"] == "manager"
    assert reviewed.json()["review_note"] == "同意"
    assert reviewed.json()["reviewed_at"] is not None

    again = app_client.patch(
        f"/api/leave-requests/{request_id}/review",
        json={"status": "rejected"},
        headers=_headers(actors["manager"]),
    )
    assert again.status_code == 409

    other_department = app_client.post(
        "/api/leave-requests",
        json=LEAVE_PAYLOAD,
        headers=_headers(actors["hr_employee"]),
    ).json()["id"]
    cross = app_client.patch(
        f"/api/leave-requests/{other_department}/review",
        json={"status": "approved"},
        headers=_headers(actors["manager"]),
    )
    assert cross.status_code == 403

    missing = app_client.patch(
        "/api/leave-requests/999999/review",
        json={"status": "approved"},
        headers=_headers(actors["admin"]),
    )
    assert missing.status_code == 404


def test_trip_create_and_admin_review(app_client, db_engine):
    actors = _seed(db_engine)
    created = app_client.post(
        "/api/business-trips",
        json=TRIP_PAYLOAD,
        headers=_headers(actors["employee"]),
    )
    assert created.status_code == 200
    assert created.json()["type"] == "trip"
    assert created.json()["type_label"] == "外派"

    request_id = created.json()["id"]
    reviewed = app_client.patch(
        f"/api/business-trips/{request_id}/review",
        json={"status": "rejected", "review_note": "改期"},
        headers=_headers(actors["admin"]),
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "rejected"

    assert (
        app_client.get("/api/business-trips", headers=_headers(actors["manager"]))
        .json()[0]["employee_no"]
        == "E1"
    )


def test_invalid_date_range_returns_422(app_client, db_engine):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/leave-requests",
        json={**LEAVE_PAYLOAD, "start_date": "2026-11-05", "end_date": "2026-11-01"},
        headers=_headers(actors["employee"]),
    )
    assert response.status_code == 422


def test_delete_leave_scope_and_pending_rule(app_client, db_engine):
    actors = _seed(db_engine)

    own = app_client.post(
        "/api/leave-requests",
        json=LEAVE_PAYLOAD,
        headers=_headers(actors["employee"]),
    ).json()["id"]
    other = app_client.post(
        "/api/leave-requests",
        json=LEAVE_PAYLOAD,
        headers=_headers(actors["hr_employee"]),
    ).json()["id"]

    denied = app_client.delete(
        f"/api/leave-requests/{other}", headers=_headers(actors["employee"])
    )
    assert denied.status_code == 403

    cross_department = app_client.delete(
        f"/api/leave-requests/{other}", headers=_headers(actors["manager"])
    )
    assert cross_department.status_code == 403

    reviewed = app_client.patch(
        f"/api/leave-requests/{own}/review",
        json={"status": "approved"},
        headers=_headers(actors["manager"]),
    )
    assert reviewed.status_code == 200

    after_review = app_client.delete(
        f"/api/leave-requests/{own}", headers=_headers(actors["employee"])
    )
    assert after_review.status_code == 409

    manager_delete = app_client.delete(
        f"/api/leave-requests/{own}", headers=_headers(actors["manager"])
    )
    assert manager_delete.status_code == 204

    employee_delete = app_client.delete(
        f"/api/leave-requests/{other}", headers=_headers(actors["hr_employee"])
    )
    assert employee_delete.status_code == 204

    missing = app_client.delete(
        "/api/leave-requests/999999", headers=_headers(actors["admin"])
    )
    assert missing.status_code == 404
