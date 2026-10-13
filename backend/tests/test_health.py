"""I1/I4/P4：健康检查、Vue 构建产物托管与 SPA 兜底。"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import FRONTEND_DIST, app


client = TestClient(app)


def test_root_serves_built_frontend():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert '<div id="app">' in response.text


def test_built_asset_is_served():
    asset_dir = FRONTEND_DIST / "assets"
    files = sorted(asset_dir.glob("*.js")) if asset_dir.is_dir() else []
    if not files:
        raise AssertionError("未找到 frontend/dist 构建产物，请先执行 npm run build")
    response = client.get(f"/assets/{files[0].name}")
    assert response.status_code == 200


def test_spa_deep_link_falls_back_to_index():
    response = client.get("/reports")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_unknown_api_path_returns_json_404():
    response = client.get("/api/definitely-missing")
    assert response.status_code == 404
    assert response.headers.get("content-type", "").startswith("application/json")


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
