"""I5：打卡、个人考勤、部门考勤与工时/状态计算测试。"""

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy.orm import Session

from app.models import Department, Shift, User
from app.security import create_access_token, hash_password
from app.services import attendance as attendance_service


@dataclass
class Actor:
    id: int
    role: str
    department_id: int | None = None


def _make_user(db, *, employee_no, username, role, department_id=None):
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


def _make_shift(db, department_id):
    shift = Shift(
        department_id=department_id,
        work_start=time(9, 0),
        work_end=time(18, 0),
        break_start=time(12, 0),
        break_end=time(13, 0),
        workdays="1,2,3,4,5",
        effective_from=date(2020, 1, 1),
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


def _headers(*, user_id, role):
    token = create_access_token(user_id=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def _seed(db_engine):
    """建两个部门、四种账号与一个技术部班次，返回登录用 Actor。"""
    with Session(db_engine) as db:
        tech = Department(name="技术部")
        hr = Department(name="人事部")
        db.add_all([tech, hr])
        db.commit()
        db.refresh(tech)
        db.refresh(hr)

        admin = _make_user(
            db, employee_no="A00001", username="admin", role="general_admin"
        )
        manager = _make_user(
            db,
            employee_no="A00002",
            username="manager",
            role="department_manager",
            department_id=tech.id,
        )
        employee = _make_user(
            db,
            employee_no="E00001",
            username="employee",
            role="employee",
            department_id=tech.id,
        )
        hr_employee = _make_user(
            db,
            employee_no="E00002",
            username="hr_employee",
            role="employee",
            department_id=hr.id,
        )
        _make_shift(db, tech.id)
        return {
            "admin": Actor(admin.id, admin.role, admin.department_id),
            "manager": Actor(manager.id, manager.role, manager.department_id),
            "employee": Actor(employee.id, employee.role, employee.department_id),
            "hr_employee": Actor(
                hr_employee.id, hr_employee.role, hr_employee.department_id
            ),
            "tech_id": tech.id,
            "hr_id": hr.id,
        }


def _auth(actor: Actor) -> dict:
    return _headers(user_id=actor.id, role=actor.role)


def test_punch_requires_login(app_client, db_engine):
    _seed(db_engine)
    response = app_client.post("/api/attendance/punch", json={"punch_type": "in"})
    assert response.status_code == 401


def test_punch_in_then_out(app_client, db_engine):
    actors = _seed(db_engine)
    headers = _auth(actors["employee"])

    sign_in = app_client.post(
        "/api/attendance/punch", json={"punch_type": "in"}, headers=headers
    )
    assert sign_in.status_code == 200
    body = sign_in.json()
    assert body["punch_type"] == "in"
    assert body["sign_in_at"] is not None
    assert body["sign_out_at"] is None
    assert body["shift_work_start"] == "09:00:00"

    sign_out = app_client.post(
        "/api/attendance/punch", json={"punch_type": "out"}, headers=headers
    )
    assert sign_out.status_code == 200
    assert sign_out.json()["sign_out_at"] is not None


def test_duplicate_punch_returns_409(app_client, db_engine):
    actors = _seed(db_engine)
    headers = _auth(actors["employee"])

    assert (
        app_client.post(
            "/api/attendance/punch", json={"punch_type": "in"}, headers=headers
        ).status_code
        == 200
    )
    duplicate = app_client.post(
        "/api/attendance/punch", json={"punch_type": "in"}, headers=headers
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "今日已签到"


def test_punch_out_before_in_returns_409(app_client, db_engine):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/attendance/punch",
        json={"punch_type": "out"},
        headers=_auth(actors["employee"]),
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "请先签到再签退"


def test_general_admin_cannot_punch(app_client, db_engine):
    actors = _seed(db_engine)
    response = app_client.post(
        "/api/attendance/punch",
        json={"punch_type": "in"},
        headers=_auth(actors["admin"]),
    )
    assert response.status_code == 403


def test_my_attendance_returns_records(app_client, db_engine):
    actors = _seed(db_engine)
    employee_headers = _auth(actors["employee"])

    empty = app_client.get("/api/attendance/me", headers=employee_headers)
    assert empty.status_code == 200
    assert empty.json()["records"] == []

    app_client.post(
        "/api/attendance/punch", json={"punch_type": "in"}, headers=employee_headers
    )
    response = app_client.get("/api/attendance/me", headers=employee_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["records"]) == 1
    assert payload["month"] == date.today().strftime("%Y-%m")
    assert payload["summary"]["work_days"] >= 1

    admin_response = app_client.get(
        "/api/attendance/me", headers=_auth(actors["admin"])
    )
    assert admin_response.status_code == 403

    assert app_client.get("/api/attendance/me").status_code == 401


def test_department_attendance_scope(app_client, db_engine):
    actors = _seed(db_engine)
    app_client.post(
        "/api/attendance/punch",
        json={"punch_type": "in"},
        headers=_auth(actors["employee"]),
    )

    today = date.today().isoformat()

    manager_rows = app_client.get(
        f"/api/attendance?date={today}", headers=_auth(actors["manager"])
    )
    assert manager_rows.status_code == 200
    rows = manager_rows.json()
    assert {row["employee_id"] for row in rows} == {
        actors["manager"].id,
        actors["employee"].id,
    }
    assert {row["department_name"] for row in rows} == {"技术部"}
    recorded = [row for row in rows if row["has_record"]]
    assert [row["employee_id"] for row in recorded] == [actors["employee"].id]
    assert all(row["status"] != "absent" for row in recorded)

    # 员工没有部门考勤查看权限
    assert (
        app_client.get(
            f"/api/attendance?date={today}", headers=_auth(actors["employee"])
        ).status_code
        == 403
    )

    admin_rows = app_client.get(
        f"/api/attendance?date={today}", headers=_auth(actors["admin"])
    )
    assert admin_rows.status_code == 200
    admin_payload = admin_rows.json()
    ids = {row["employee_id"] for row in admin_payload}
    assert ids == {
        actors["manager"].id,
        actors["employee"].id,
        actors["hr_employee"].id,
    }
    assert actors["admin"].id not in ids
    hr_row = next(
        row for row in admin_payload if row["employee_id"] == actors["hr_employee"].id
    )
    assert hr_row["has_record"] is False
    assert hr_row["status"] in {"absent", None}

    filtered = app_client.get(
        f"/api/attendance?date={today}&department_id={actors['hr_id']}",
        headers=_auth(actors["admin"]),
    )
    assert {row["employee_id"] for row in filtered.json()} == {
        actors["hr_employee"].id
    }


def test_invalid_date_query_returns_400(app_client, db_engine):
    actors = _seed(db_engine)
    response = app_client.get(
        "/api/attendance?date=2026-13-99", headers=_auth(actors["admin"])
    )
    assert response.status_code == 400


def test_employee_attendance_detail_permission(app_client, db_engine):
    actors = _seed(db_engine)

    denied = app_client.get(
        f"/api/attendance/employee/{actors['hr_employee'].id}",
        headers=_auth(actors["manager"]),
    )
    assert denied.status_code == 403

    allowed = app_client.get(
        f"/api/attendance/employee/{actors['employee'].id}",
        headers=_auth(actors["manager"]),
    )
    assert allowed.status_code == 200
    assert allowed.json()["employee_no"] == "E00001"

    admin_view = app_client.get(
        f"/api/attendance/employee/{actors['hr_employee'].id}",
        headers=_auth(actors["admin"]),
    )
    assert admin_view.status_code == 200

    non_subject = app_client.get(
        f"/api/attendance/employee/{actors['admin'].id}",
        headers=_auth(actors["admin"]),
    )
    assert non_subject.status_code == 400

    assert (
        app_client.get(
            "/api/attendance/employee/999999", headers=_auth(actors["admin"])
        ).status_code
        == 404
    )


def test_service_computes_status_and_working_minutes(db_session):
    tech = Department(name="技术部")
    db_session.add(tech)
    db_session.commit()
    db_session.refresh(tech)
    _make_shift(db_session, tech.id)

    late = _make_user(
        db_session,
        employee_no="E00001",
        username="late",
        role="employee",
        department_id=tech.id,
    )
    early = _make_user(
        db_session,
        employee_no="E00002",
        username="early",
        role="employee",
        department_id=tech.id,
    )
    on_time = _make_user(
        db_session,
        employee_no="E00003",
        username="on_time",
        role="employee",
        department_id=tech.id,
    )

    workday = date(2026, 5, 6)  # 周三
    attendance_service.punch(
        db_session, late, "in", now=datetime(2026, 5, 6, 9, 30)
    )
    late_record = attendance_service.punch(
        db_session, late, "out", now=datetime(2026, 5, 6, 18, 5)
    )
    assert late_record.status == "late"
    assert late_record.is_workday is True
    assert late_record.working_minutes == 455  # 8h35m - 1h 午休

    attendance_service.punch(
        db_session, early, "in", now=datetime(2026, 5, 6, 8, 55)
    )
    early_record = attendance_service.punch(
        db_session, early, "out", now=datetime(2026, 5, 6, 17, 0)
    )
    assert early_record.status == "early_leave"
    assert early_record.working_minutes == 425  # 8h05m - 1h 午休

    attendance_service.punch(
        db_session, on_time, "in", now=datetime(2026, 5, 6, 9, 0)
    )
    present_record = attendance_service.punch(
        db_session, on_time, "out", now=datetime(2026, 5, 6, 18, 0)
    )
    assert present_record.status == "present"
    assert present_record.working_minutes == 480

    weekend_record = attendance_service.punch(
        db_session, on_time, "in", now=datetime(2026, 5, 9, 10, 0)
    )
    assert weekend_record.is_workday is False
    assert weekend_record.work_date == date(2026, 5, 9)


def test_summary_treats_late_day_as_attended(db_session):
    tech = Department(name="技术部")
    db_session.add(tech)
    db_session.commit()
    db_session.refresh(tech)
    shift = _make_shift(db_session, tech.id)
    employee = _make_user(
        db_session,
        employee_no="E00001",
        username="late",
        role="employee",
        department_id=tech.id,
    )

    attendance_service.punch(
        db_session, employee, "in", now=datetime(2026, 5, 6, 9, 30)
    )
    attendance_service.punch(
        db_session, employee, "out", now=datetime(2026, 5, 6, 18, 5)
    )

    start, end = date(2026, 5, 1), date(2026, 5, 31)
    records = attendance_service.month_records(db_session, employee.id, start, end)
    summary = attendance_service.summarize(records, shift, start, end)

    assert summary["attended_days"] == 1
    assert summary["late_count"] == 1
    assert summary["early_leave_count"] == 0
    assert summary["present_days"] == 0
    assert summary["work_days"] > 0
    assert summary["absent_days"] == summary["work_days"] - 1
    assert summary["attendance_rate"] == round(1 / summary["work_days"] * 100, 1)
