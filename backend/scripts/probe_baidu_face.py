"""百度云人脸 API 连通性探测：验证 access_token 与人脸检测接口。

用法：
    backend/.venv/Scripts/python -m scripts.probe_baidu_face

不打印密钥与完整 token，只报告成功/失败原因，可安全用于排查配置。
人脸检测使用内置的 1x1 占位图，预期返回「未检测到人脸」，以此确认接口可达。
"""

import base64
import sys
from io import BytesIO

import requests
from PIL import Image

from app.config import settings


TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
DETECT_URL = "https://aip.baidubce.com/rest/2.0/face/v3/detect"


def _placeholder_image() -> str:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), (200, 200, 200)).save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


def _get_token() -> tuple[str | None, int | None]:
    response = requests.post(
        TOKEN_URL,
        params={
            "grant_type": "client_credentials",
            "client_id": settings.baidu_face_ak,
            "client_secret": settings.baidu_face_sk,
        },
        timeout=10,
    )
    payload = response.json()
    if "access_token" not in payload:
        print(f"FAIL: 换取 token 失败 {payload.get('error')} - {payload.get('error_description')}")
        return None, None
    token = payload["access_token"]
    print(
        "OK: access_token 获取成功 "
        f"(长度 {len(token)}, 有效期 {payload.get('expires_in')}s, 前缀 {token[:6]}...)"
    )
    return token, 0


def main() -> int:
    if not settings.baidu_face_ak or not settings.baidu_face_sk:
        print("FAIL: BAIDU_FACE_AK / SK 未配置")
        return 2

    try:
        token, _ = _get_token()
    except requests.RequestException as exc:
        print(f"FAIL: 网络请求异常 {type(exc).__name__}: {exc}")
        return 3
    if token is None:
        return 1

    try:
        response = requests.post(
            DETECT_URL,
            params={"access_token": token},
            json={
                "image": _placeholder_image(),
                "image_type": "BASE64",
                "face_field": "quality",
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        print(f"FAIL: 人脸检测网络异常 {type(exc).__name__}: {exc}")
        return 3

    payload = response.json()
    error_code = payload.get("error_code")
    error_msg = payload.get("error_msg")
    # 222202/222207=未检测到人脸，属预期；其他非 0 视为异常。
    if error_code == 0:
        print(f"OK: 人脸检测接口可达（检测到 {payload.get('result', {}).get('face_num')} 张人脸）")
        return 0
    if error_code in (222202, 222207):
        print("OK: 人脸检测接口可达（占位图未检测到人脸，符合预期）")
        return 0
    print(f"FAIL: 人脸检测返回 error_code={error_code} error_msg={error_msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
