"""I5c：月度报表接口的鉴权、范围与聚合口径测试。"""

from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy.orm import Session

from app.models import Attendance, BusinessTrip, Department, LeaveRequest, Shift, User
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


def test_monthly_report_requires_login(app_client, db_engine):
    assert app_client.get("/api/reports/monthly?month=2026-10").status_code == 401


def test_monthly_report_scope_and_metrics(app_client, db_engine):
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

        tech_shift = Shift(
            department_id=tech.id,
            effective_from=date(2026, 1, 1),
            work_start=time(9, 0),
            work_end=time(18, 0),
            break_start=time(12, 0),
            break_end=time(13, 0),
            workdays="1,2,3,4,5",
        )
        hr_shift = Shift(
            department_id=hr.id,
            effective_from=date(2026, 1, 1),
            work_start=time(9, 0),
            work_end=time(18, 0),
            break_start=time(12, 0),
            break_end=time(13, 0),
            workdays="1,2,3,4,5",
        )
        db.add_all([tech_shift, hr_shift])
        db.commit()
        db.refresh(tech_shift)
        db.refresh(hr_shift)

        # 2026-10-12（周一）正常，2026-10-13（周二）迟到。
        db.add_all(
            [
                Attendance(
                    employee_id=worker.id,
                    shift_id=tech_shift.id,
                    work_date=date(2026, 10, 12),
                    is_workday=True,
                    status="present",
                    sign_in_at=datetime(2026, 10, 12, 8, 50),
                    sign_out_at=datetime(2026, 10, 12, 18, 0),
                    working_minutes=480,
                ),
                Attendance(
                    employee_id=worker.id,
                    shift_id=tech_shift.id,
                    work_date=date(2026, 10, 13),
                    is_workday=True,
                    status="late",
                    sign_in_at=datetime(2026, 10, 13, 9, 20),
                    sign_out_at=datetime(2026, 10, 13, 18, 0),
                    working_minutes=480,
                ),
                Attendance(
                    employee_id=outsider.id,
                    shift_id=hr_shift.id,
                    work_date=date(2026, 10, 12),
                    is_workday=True,
                    status="present",
                    sign_in_at=datetime(2026, 10, 12, 8, 55),
                    sign_out_at=datetime(2026, 10, 12, 18, 0),
                    working_minutes=480,
                ),
                LeaveRequest(
                    employee_id=worker.id,
                    leave_type="事假",
                    start_date=date(2026, 10, 12),
                    end_date=date(2026, 10, 13),
                    duration_days=2,
                    status="approved",
                ),
                BusinessTrip(
                    employee_id=worker.id,
                    start_date=date(2026, 10, 14),
                    end_date=date(2026, 10, 16),
                    duration_days=3,
                    status="approved",
                ),
            ]
        )
        db.commit()

        actors = {
            "admin": Actor(admin.id, admin.role),
            "manager": Actor(manager.id, manager.role, tech.id),
            "worker": Actor(worker.id, worker.role, tech.id),
        }

    # 员工角色没有部门级报表权限
    denied = app_client.get(
        "/api/reports/monthly?month=2026-10", headers=_headers(actors["worker"])
    )
    assert denied.status_code == 403

    # 部门管理员只看本部门
    scoped = app_client.get(
        "/api/reports/monthly?month=2026-10", headers=_headers(actors["manager"])
    )
    assert scoped.status_code == 200
    body = scoped.json()
    assert body["scope_label"] == "技术部"
    assert body["start_date"] == "2026-10-01"
    assert body["end_date"] == "2026-10-31"
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["department_name"] == "技术部"
    assert row["employee_count"] == 2
    assert row["work_days"] == 44
    assert row["attended_days"] == 2
    assert row["present_days"] == 1
    assert row["late_count"] == 1
    assert row["absent_days"] == 42
    assert row["average_working_minutes"] == 480
    assert row["attendance_rate"] == 4.5
    assert row["leave_days"] == 2.0
    assert row["trip_days"] == 3.0

    # 总管理员可按部门下钻，也可查看全公司
    company = app_client.get(
        "/api/reports/monthly?month=2026-10", headers=_headers(actors["admin"])
    )
    assert company.status_code == 200
    names = {item["department_name"] for item in company.json()["rows"]}
    assert names == {"技术部", "人事部"}

    single = app_client.get(
        f"/api/reports/monthly?month=2026-10&department_id={actors['manager'].department_id}",
        headers=_headers(actors["admin"]),
    )
    assert [item["department_name"] for item in single.json()["rows"]] == ["技术部"]

    missing = app_client.get(
        "/api/reports/monthly?month=2026-10&department_id=999999",
        headers=_headers(actors["admin"]),
    )
    assert missing.status_code == 404


def test_monthly_report_rejects_bad_month(app_client, db_engine):
    with Session(db_engine) as db:
        admin = _user(db, employee_no="A1", username="admin", role="general_admin")
        actor = Actor(admin.id, admin.role)

    response = app_client.get(
        "/api/reports/monthly?month=2026-13", headers=_headers(actor)
    )
    assert response.status_code == 400
