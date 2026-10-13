"""真实人脸链路演示：管理员代注册 → 员工刷脸签到。

用法（在 backend 目录，需后端已启动且百度服务可用）：
    .venv/Scripts/python -m scripts.e2e_face_demo D:\\path\\face.jpg E00001
"""

import base64
import sys
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8000/api"


def _data_url(path: str) -> str:
    raw = Path(path).read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def _login(username: str, password: str) -> dict:
    response = requests.post(
        f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=15
    )
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    image = _data_url(sys.argv[1])
    employee_no = sys.argv[2]

    admin = _login("admin", "admin123")
    employees = requests.get(f"{BASE}/employees", headers=admin, timeout=15).json()
    target = next((item for item in employees if item["employee_no"] == employee_no), None)
    if target is None:
        print(f"FAIL: 未找到员工 {employee_no}")
        return 1

    registered = requests.post(
        f"{BASE}/face/register",
        json={"employee_id": target["id"], "image": image},
        headers=admin,
        timeout=30,
    )
    print("register:", registered.status_code, registered.json())
    if registered.status_code != 200:
        return 1

    employee = _login("employee", "employee123")
    punched = requests.post(
        f"{BASE}/face/attendance",
        json={"punch_type": "in", "image": image},
        headers=employee,
        timeout=30,
    )
    print("attendance:", punched.status_code, punched.json())
    return 0 if punched.status_code in (200, 409) else 1


if __name__ == "__main__":
    sys.exit(main())
