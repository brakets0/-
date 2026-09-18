"""I1：后端健康检查接口测试（I4 后根路径返回 Web 管理台页面）。"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_returns_app_info():
    response = client.get("/")
    assert response.status_code == 200
    assert "员工考勤" in response.text
    assert "text/html" in response.headers.get("content-type", "")


def test_static_assets_are_served():
    css = client.get("/styles.css")
    js = client.get("/app.js")
    assert css.status_code == 200
    assert "backdrop-filter" in css.text
    assert js.status_code == 200
    assert "login" in js.text


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
