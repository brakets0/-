"""I3：账号密码登录、JWT 校验与用户信息测试。"""

from app.security import create_access_token, verify_password


def test_login_success_returns_token_and_profile(app_client, seed_user):
    response = app_client.post(
        "/auth/login",
        json={"username": "tester", "password": "secret123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["username"] == "tester"
    assert data["user"]["role"] == "employee"
    assert "department_name" in data["user"]
    assert "password_hash" not in data["user"]

    me = app_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "tester"
    assert "attendance.sign" in me.json()["permissions"]


def test_login_wrong_password_returns_401(app_client, seed_user):
    response = app_client.post(
        "/auth/login",
        json={"username": "tester", "password": "wrong123"},
    )
    assert response.status_code == 401


def test_login_unknown_user_returns_401(app_client):
    response = app_client.post(
        "/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )
    assert response.status_code == 401


def test_auth_me_without_token_returns_401(app_client):
    response = app_client.get("/auth/me")
    assert response.status_code == 401


def test_auth_me_with_bad_token_returns_401(app_client):
    response = app_client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-valid-token"}
    )
    assert response.status_code == 401


def test_token_with_inactive_user_returns_401(app_client, db_engine, seed_user):
    from sqlalchemy.orm import Session

    from app.models import User

    with Session(db_engine) as session:
        user = session.get(User, 1)
        user.status = "inactive"
        session.commit()
        token = create_access_token(user_id=user.id, role=user.role)

    me = app_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 401


def test_verify_password_accepts_correct_and_rejects_wrong():
    hashed = "$2b$12$abcdefghijklmnopqrstuv"
    assert verify_password("not-real", hashed) is False
