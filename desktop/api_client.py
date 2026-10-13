"""桌面端 HTTP 客户端：只调用 FastAPI 后端，不直连数据库或百度云。"""

import requests


class ApiError(RuntimeError):
    """后端返回的错误，统一带可读 message。"""


class AttendanceApi:
    def __init__(self, base_url: str = "http://127.0.0.1:8000/api", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: str | None = None

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(
                method, url, timeout=self.timeout, headers=self._headers(), **kwargs
            )
        except requests.RequestException as exc:
            raise ApiError(f"无法连接后端：{exc}") from exc
        if response.status_code >= 400:
            detail = response.json().get("detail") if response.content else None
            if isinstance(detail, list):
                detail = "；".join(item.get("msg", "") for item in detail)
            raise ApiError(str(detail or f"请求失败（{response.status_code}）"))
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def login(self, username: str, password: str) -> dict:
        data = self._request(
            "POST", "/auth/login", json={"username": username, "password": password}
        )
        self.token = data["access_token"]
        return data["user"]

    def logout(self) -> None:
        self.token = None

    def profile(self) -> dict:
        return self._request("GET", "/auth/me")

    def face_status(self) -> dict:
        return self._request("GET", "/face/me")

    def register_face(self, image_data_url: str, employee_id: int | None = None) -> dict:
        payload = {"image": image_data_url}
        if employee_id is not None:
            payload["employee_id"] = employee_id
        return self._request("POST", "/face/register", json=payload)

    def face_attendance(self, punch_type: str, image_data_url: str) -> dict:
        return self._request(
            "POST",
            "/face/attendance",
            json={"punch_type": punch_type, "image": image_data_url},
        )

    def my_attendance(self, month: str) -> dict:
        return self._request("GET", "/attendance/me", params={"month": month})
