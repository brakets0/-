"""I3：三角色权限矩阵与 401/403 访问控制测试。"""

import pytest
from sqlalchemy.orm import Session

from app.models import User
from app.permissions import get_permissions, is_attendance_subject


@pytest.fixture
def role_user(db_engine):
    """为角色权限测试准备一份基础用户。"""

    def _make(role: str) -> User:
        with Session(db_engine) as session:
            user = User(
                employee_no=f"T-{role}",
                username=f"t-{role}",
                password_hash="x",
                name=role,
                role=role,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    return _make


def test_employee_has_basic_employee_permissions():
    perms = get_permissions("employee")
    assert "profile.view.self" in perms
    assert "attendance.sign" in perms
    assert "system.manage" not in perms


def test_department_manager_inherits_employee_and_department_permissions():
    perms = get_permissions("department_manager")
    assert "attendance.sign" in perms
    assert "leave.review.department" in perms
    assert "employee.view.department" in perms
    assert "employee.manage.department" in perms
    assert "employee.assign.department" in perms
    assert "attendance.view.department" in perms
    assert "employee.manage" not in perms
    assert "department.manage" not in perms
    assert "system.manage" not in perms


def test_department_manager_cannot_manage_employees_outside_department():
    perms = get_permissions("department_manager")
    assert "employee.manage.all" not in perms
    assert "attendance.view.all" not in perms
    assert "leave.review.all" not in perms
    assert "system.manage" not in perms


def test_general_admin_has_all_highest_permissions():
    perms = get_permissions("general_admin")
    assert "department.manage" in perms
    assert "employee.manage" in perms
    assert "employee.manage.department" in perms
    assert "employee.assign.department" in perms
    assert "system.manage" in perms


def test_unknown_role_has_no_permissions():
    assert get_permissions("unknown") == frozenset()


def test_general_admin_not_included_in_attendance_statistics():
    assert is_attendance_subject("general_admin") is False


def test_employee_and_department_manager_included_in_attendance_statistics():
    assert is_attendance_subject("employee") is True
    assert is_attendance_subject("department_manager") is True


def test_permission_matrix_requires_admin(app_client):
    assert app_client.get("/permissions/matrix").status_code == 401


def test_permission_matrix_allows_general_admin(app_client, role_user):
    user = role_user("general_admin")
    token = _token_for_user(user)
    response = app_client.get(
        "/permissions/matrix",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert set(response.json()) == {
        "employee",
        "department_manager",
        "general_admin",
    }


def test_employee_cannot_access_admin_probe(app_client, role_user):
    user = role_user("employee")
    token = _token_for_user(user)
    response = app_client.get(
        "/permissions/admin-check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_department_manager_cannot_access_admin_probe(app_client, role_user):
    user = role_user("department_manager")
    token = _token_for_user(user)
    response = app_client.get(
        "/permissions/admin-check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_general_admin_can_access_admin_probe(app_client, role_user):
    user = role_user("general_admin")
    token = _token_for_user(user)
    response = app_client.get(
        "/permissions/admin-check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_department_probe_allows_manager_and_admin(app_client, role_user):
    for role in ("department_manager", "general_admin"):
        user = role_user(role)
        token = _token_for_user(user)
        response = app_client.get(
            "/permissions/department-check",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


def test_employee_manage_probe_allows_manager_and_admin(app_client, role_user):
    for role in ("department_manager", "general_admin"):
        user = role_user(role)
        token = _token_for_user(user)
        response = app_client.get(
            "/permissions/employee-manage-check",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200


def test_employee_cannot_access_employee_manage_probe(app_client, role_user):
    user = role_user("employee")
    token = _token_for_user(user)
    response = app_client.get(
        "/permissions/employee-manage-check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def _token_for_user(user: User) -> str:
    from app.security import create_access_token

    return create_access_token(user_id=user.id, role=user.role)
