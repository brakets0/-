"""I4：部门、员工、班次 CRUD 与权限边界测试。"""

from dataclasses import dataclass
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Department, User
from app.security import create_access_token, hash_password


@dataclass
class OrgUser:
    id: int
    role: str
    department_id: int | None = None


@dataclass
class OrgDept:
    id: int


def _make_user(db, *, employee_no, username, role, department_id=None, name=None):
    user = User(
        employee_no=employee_no,
        username=username,
        password_hash=hash_password("secret123"),
        name=name or username,
        role=role,
        department_id=department_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_department(db, name, manager_user_id=None):
    dept = Department(name=name, manager_user_id=manager_user_id)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


def _headers(user):
    token = create_access_token(user_id=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


def _seed_org(db_engine):
    with Session(db_engine) as db:
        tech = _make_department(db, "技术部")
        hr = _make_department(db, "人事部")
        admin = _make_user(
            db,
            employee_no="A00001",
            username="admin",
            role="general_admin",
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
        tech.manager_user_id = manager.id
        db.commit()
        db.refresh(tech)
        return (
            OrgUser(id=admin.id, role=admin.role, department_id=admin.department_id),
            OrgUser(id=manager.id, role=manager.role, department_id=manager.department_id),
            OrgUser(id=employee.id, role=employee.role, department_id=employee.department_id),
            OrgUser(id=hr_employee.id, role=hr_employee.role, department_id=hr_employee.department_id),
            OrgDept(id=tech.id),
            OrgDept(id=hr.id),
        )


def test_departments_require_login(app_client):
    assert app_client.get("/api/departments").status_code == 401


def test_department_list_allows_any_active_user(app_client, db_engine):
    admin, manager, _, _, _, _ = _seed_org(db_engine)
    for user in (admin, manager):
        response = app_client.get("/api/departments", headers=_headers(user))
        assert response.status_code == 200
        assert {item["name"] for item in response.json()} == {"技术部", "人事部"}


def test_department_crud_admin_only(app_client, db_engine):
    admin, manager, _, _, _, _ = _seed_org(db_engine)

    denied = app_client.post(
        "/api/departments",
        headers=_headers(manager),
        json={"name": "财务部"},
    )
    assert denied.status_code == 403

    created = app_client.post(
        "/api/departments",
        headers=_headers(admin),
        json={"name": "财务部"},
    )
    assert created.status_code == 200
    assert created.json()["name"] == "财务部"

    duplicate = app_client.post(
        "/api/departments",
        headers=_headers(admin),
        json={"name": "财务部"},
    )
    assert duplicate.status_code == 409

    updated = app_client.patch(
        f"/api/departments/{created.json()['id']}",
        headers=_headers(admin),
        json={"name": "财务与审计部"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "财务与审计部"

    deleted = app_client.delete(
        f"/api/departments/{created.json()['id']}",
        headers=_headers(admin),
    )
    assert deleted.status_code == 204


def test_department_assign_manager_validates_role_and_department(app_client, db_engine):
    admin, manager, employee, _, tech, hr = _seed_org(db_engine)

    wrong_role = app_client.post(
        "/api/departments",
        headers=_headers(admin),
        json={"name": "运营部", "manager_user_id": employee.id},
    )
    assert wrong_role.status_code == 400

    wrong_department = app_client.post(
        "/api/departments",
        headers=_headers(admin),
        json={"name": "运营部", "manager_user_id": manager.id},
    )
    assert wrong_department.status_code == 400

    created = app_client.post(
        "/api/departments",
        headers=_headers(admin),
        json={"name": "运营部"},
    )
    assert created.status_code == 200

    assigned = app_client.patch(
        f"/api/departments/{created.json()['id']}",
        headers=_headers(admin),
        json={"manager_user_id": manager.id},
    )
    assert assigned.status_code == 400

    with Session(db_engine) as db:
        tech_row = db.get(Department, tech.id)
        tech_row.manager_user_id = None
        manager_row = db.get(User, manager.id)
        manager_row.department_id = created.json()["id"]
        db.commit()
    assigned_ok = app_client.patch(
        f"/api/departments/{created.json()['id']}",
        headers=_headers(admin),
        json={"manager_user_id": manager.id},
    )
    assert assigned_ok.status_code == 200
    assert assigned_ok.json()["manager_name"] == "manager"


def test_employee_list_respects_department_scope(app_client, db_engine):
    admin, manager, employee, hr_employee, tech, hr = _seed_org(db_engine)

    employee_response = app_client.get("/api/employees", headers=_headers(employee))
    assert employee_response.status_code == 403

    manager_response = app_client.get("/api/employees", headers=_headers(manager))
    assert manager_response.status_code == 200
    names = {item["name"] for item in manager_response.json()}
    assert names == {"manager", "employee"}

    admin_response = app_client.get("/api/employees", headers=_headers(admin))
    assert admin_response.status_code == 200
    names = {item["name"] for item in admin_response.json()}
    assert names == {"admin", "manager", "employee", "hr_employee"}


def test_create_employee_validation_and_scope(app_client, db_engine):
    admin, manager, _, _, tech, hr = _seed_org(db_engine)

    payload = {
        "employee_no": "E01001",
        "username": "newbie",
        "password": "secret123",
        "name": "新员工",
        "role": "employee",
        "department_id": tech.id,
    }
    created = app_client.post("/api/employees", headers=_headers(admin), json=payload)
    assert created.status_code == 200
    assert created.json()["department_name"] == "技术部"

    duplicate = app_client.post("/api/employees", headers=_headers(admin), json=payload)
    assert duplicate.status_code == 409

    no_department = app_client.post(
        "/api/employees",
        headers=_headers(admin),
        json={**payload, "username": "nobody", "department_id": None},
    )
    assert no_department.status_code == 400

    promote_by_manager = app_client.post(
        "/api/employees",
        headers=_headers(manager),
        json={**payload, "username": "promoted", "role": "department_manager"},
    )
    assert promote_by_manager.status_code == 403

    manager_created = app_client.post(
        "/api/employees",
        headers=_headers(manager),
        json={**payload, "username": "manager_newbie", "employee_no": "E01002"},
    )
    assert manager_created.status_code == 200

    cross_department = app_client.post(
        "/api/employees",
        headers=_headers(manager),
        json={**payload, "username": "cross", "employee_no": "E01003", "department_id": hr.id},
    )
    assert cross_department.status_code == 403


def test_blank_names_rejected(app_client, db_engine):
    admin, _, _, _, tech, _ = _seed_org(db_engine)

    blank_department = app_client.post(
        "/api/departments",
        headers=_headers(admin),
        json={"name": "   "},
    )
    assert blank_department.status_code == 422

    blank_employee = app_client.post(
        "/api/employees",
        headers=_headers(admin),
        json={
            "employee_no": "  ",
            "username": "blank_name",
            "password": "secret123",
            "name": "空白员工",
            "role": "employee",
            "department_id": tech.id,
        },
    )
    assert blank_employee.status_code == 422


def test_update_employee_enforces_manager_scope(app_client, db_engine):
    admin, manager, employee, hr_employee, tech, hr = _seed_org(db_engine)

    cross_update = app_client.patch(
        f"/api/employees/{hr_employee.id}",
        headers=_headers(manager),
        json={"name": "越权改名"},
    )
    assert cross_update.status_code == 403

    promote = app_client.patch(
        f"/api/employees/{employee.id}",
        headers=_headers(manager),
        json={"role": "department_manager"},
    )
    assert promote.status_code == 403

    rename = app_client.patch(
        f"/api/employees/{employee.id}",
        headers=_headers(manager),
        json={"name": "本部门员工"},
    )
    assert rename.status_code == 200
    assert rename.json()["name"] == "本部门员工"

    move = app_client.patch(
        f"/api/employees/{employee.id}",
        headers=_headers(admin),
        json={"department_id": hr.id},
    )
    assert move.status_code == 200
    assert move.json()["department_name"] == "人事部"


def test_update_employee_clears_stale_manager_assignment(app_client, db_engine):
    admin, manager, _, _, tech, hr = _seed_org(db_engine)

    promoted = app_client.patch(
        f"/api/employees/{manager.id}",
        headers=_headers(admin),
        json={"role": "department_manager", "department_id": hr.id},
    )
    assert promoted.status_code == 200
    assert promoted.json()["department_name"] == "人事部"

    with Session(db_engine) as db:
        stale = db.execute(
            select(Department).where(Department.manager_user_id == manager.id)
        ).scalar_one_or_none()
        assert stale is None
        tech_row = db.get(Department, tech.id)
        assert tech_row.manager_user_id is None

    demoted = app_client.patch(
        f"/api/employees/{manager.id}",
        headers=_headers(admin),
        json={"role": "employee"},
    )
    assert demoted.status_code == 200

    no_department = app_client.patch(
        f"/api/employees/{manager.id}",
        headers=_headers(admin),
        json={"department_id": None},
    )
    assert no_department.status_code == 400


def test_delete_employee_admin_only(app_client, db_engine):
    admin, manager, employee, hr_employee, tech, hr = _seed_org(db_engine)

    denied = app_client.delete(f"/api/employees/{employee.id}", headers=_headers(manager))
    assert denied.status_code == 403

    self_delete = app_client.delete(f"/api/employees/{admin.id}", headers=_headers(admin))
    assert self_delete.status_code == 400

    deleted = app_client.delete(f"/api/employees/{employee.id}", headers=_headers(admin))
    assert deleted.status_code == 204


def test_shift_crud_and_workdays_validation(app_client, db_engine):
    admin, manager, _, _, tech, hr = _seed_org(db_engine)
    base = {
        "department_id": tech.id,
        "work_start": "09:00",
        "work_end": "18:00",
        "break_start": "12:00",
        "break_end": "13:00",
        "workdays": "1,2,3,4,5",
        "effective_from": "2026-09-01",
    }

    bad_workdays = app_client.post(
        "/api/shifts",
        headers=_headers(admin),
        json={**base, "workdays": "1,8"},
    )
    assert bad_workdays.status_code == 422

    bad_duplicates = app_client.post(
        "/api/shifts",
        headers=_headers(admin),
        json={**base, "workdays": "1,1,2"},
    )
    assert bad_duplicates.status_code == 422

    bad_times = app_client.post(
        "/api/shifts",
        headers=_headers(admin),
        json={**base, "work_start": "18:00", "work_end": "09:00"},
    )
    assert bad_times.status_code == 422

    bad_break = app_client.post(
        "/api/shifts",
        headers=_headers(admin),
        json={**base, "break_start": None, "break_end": "13:00"},
    )
    assert bad_break.status_code == 422

    created = app_client.post("/api/shifts", headers=_headers(admin), json=base)
    assert created.status_code == 200
    assert created.json()["workdays"] == "1,2,3,4,5"
    assert created.json()["department_name"] == "技术部"

    duplicate = app_client.post("/api/shifts", headers=_headers(admin), json=base)
    assert duplicate.status_code == 409

    normalized = app_client.post(
        "/api/shifts",
        headers=_headers(admin),
        json={**base, "workdays": "5,1,3", "effective_from": "2026-10-01"},
    )
    assert normalized.status_code == 200
    assert normalized.json()["workdays"] == "1,3,5"

    updated = app_client.patch(
        f"/api/shifts/{created.json()['id']}",
        headers=_headers(admin),
        json={"work_start": "08:30"},
    )
    assert updated.status_code == 200
    assert updated.json()["work_start"] == "08:30:00"

    deleted = app_client.delete(
        f"/api/shifts/{created.json()['id']}",
        headers=_headers(admin),
    )
    assert deleted.status_code == 204


def test_shift_department_manager_scope(app_client, db_engine):
    admin, manager, _, _, tech, hr = _seed_org(db_engine)
    base = {
        "department_id": hr.id,
        "work_start": "09:00",
        "work_end": "18:00",
        "break_start": "12:00",
        "break_end": "13:00",
        "workdays": "1,2,3,4,5",
        "effective_from": "2026-09-01",
    }

    denied = app_client.post("/api/shifts", headers=_headers(manager), json=base)
    assert denied.status_code == 403

    own = app_client.post(
        "/api/shifts",
        headers=_headers(manager),
        json={**base, "department_id": tech.id},
    )
    assert own.status_code == 200

    listing = app_client.get("/api/shifts", headers=_headers(manager))
    assert listing.status_code == 200
    assert {item["department_name"] for item in listing.json()} == {"技术部"}

    admin_listing = app_client.get("/api/shifts", headers=_headers(admin))
    assert {item["department_name"] for item in admin_listing.json()} == {"技术部"}


def test_shift_patch_validates_against_existing_end(app_client, db_engine):
    admin, _, _, _, tech, _ = _seed_org(db_engine)
    base = {
        "department_id": tech.id,
        "work_start": "09:00",
        "work_end": "18:00",
        "break_start": "12:00",
        "break_end": "13:00",
        "workdays": "1,2,3,4,5",
        "effective_from": "2026-09-01",
    }
    created = app_client.post("/api/shifts", headers=_headers(admin), json=base)
    assert created.status_code == 200

    invalid = app_client.patch(
        f"/api/shifts/{created.json()['id']}",
        headers=_headers(admin),
        json={"work_end": "08:00"},
    )
    assert invalid.status_code == 422

    valid = app_client.patch(
        f"/api/shifts/{created.json()['id']}",
        headers=_headers(admin),
        json={"work_end": "18:30"},
    )
    assert valid.status_code == 200
    assert valid.json()["work_end"] == "18:30:00"
