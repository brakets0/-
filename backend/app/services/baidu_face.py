"""百度云人脸识别 REST 客户端（face/v3）。

本模块是项目中唯一直接调用百度云的地方：登录换 token、人脸检测、人脸注册、
人脸搜索都封装在这里，上层业务与桌面端不感知百度接口细节。密钥来自
`BAIDU_FACE_AK` / `BAIDU_FACE_SK`，不写入代码或日志。
"""

import threading
import time

import requests

from app.config import settings


TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
DETECT_URL = "https://aip.baidubce.com/rest/2.0/face/v3/detect"
ADD_FACE_URL = "https://aip.baidubce.com/rest/2.0/face/v3/faceset/user/add"
DELETE_FACE_URL = "https://aip.baidubce.com/rest/2.0/face/v3/faceset/user/delete"
SEARCH_URL = "https://aip.baidubce.com/rest/2.0/face/v3/search"

MAX_IMAGE_BYTES = 2 * 1024 * 1024


def strip_data_url_prefix(image: str) -> str:
    """百度只接受纯 base64，这里把 `data:image/...;base64,` 前缀去掉。"""
    if image.startswith("data:") and "," in image:
        return image.split(",", 1)[1]
    return image


class FaceConfigError(RuntimeError):
    """百度密钥未配置。"""


class FaceServiceError(RuntimeError):
    """百度接口返回错误。"""

    def __init__(self, error_code: int | str | None, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class FaceNetworkError(RuntimeError):
    """调用百度接口时的网络异常。"""


class NoFaceDetected(FaceServiceError):
    """图片中未检测到人脸。"""


class BaiduFaceClient:
    """百度云人脸识别客户端，token 带缓存并支持注入 session 便于测试。"""

    def __init__(self, session: requests.Session | None = None, timeout: float = 10.0):
        self._session = session or requests.Session()
        self._timeout = timeout
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

    def _credentials(self) -> tuple[str, str]:
        if not settings.baidu_face_ak or not settings.baidu_face_sk:
            raise FaceConfigError("百度人脸识别密钥未配置")
        return settings.baidu_face_ak, settings.baidu_face_sk

    def get_access_token(self, *, force: bool = False) -> str:
        """获取 access_token，带 60s 提前刷新缓存。"""
        now = time.time()
        if not force and self._token and now < self._token_expires_at:
            return self._token

        ak, sk = self._credentials()
        with self._lock:
            now = time.time()
            if not force and self._token and now < self._token_expires_at:
                return self._token
            try:
                response = self._session.post(
                    TOKEN_URL,
                    params={
                        "grant_type": "client_credentials",
                        "client_id": ak,
                        "client_secret": sk,
                    },
                    timeout=self._timeout,
                )
            except requests.RequestException as exc:
                raise FaceNetworkError(f"无法连接百度云：{exc}") from exc
            payload = self._json(response)
            token = payload.get("access_token")
            if not token:
                detail = payload.get("error_description") or payload.get("error")
                raise FaceServiceError(payload.get("error"), f"获取百度访问令牌失败：{detail}")
            self._token = token
            self._token_expires_at = now + int(payload.get("expires_in", 0)) - 60
            return token

    def detect(self, image: str) -> dict:
        """人脸检测，返回第一个可用的 face_token 与质量信息。"""
        payload = self._post(
            DETECT_URL,
            {
                "image": strip_data_url_prefix(image),
                "image_type": "BASE64",
                "face_field": "quality",
            },
        )
        result = payload.get("result") or {}
        faces = result.get("face_list") or []
        if not faces:
            raise NoFaceDetected(222207, "图片中未检测到人脸")
        face = faces[0]
        return {
            "face_token": face.get("face_token"),
            "quality": face.get("quality"),
            "location": face.get("location"),
        }

    def add_face(self, user_id: str, image: str) -> str:
        """把人脸注册到人脸库，返回 face_token。"""
        payload = self._post(
            ADD_FACE_URL,
            {
                "image": strip_data_url_prefix(image),
                "image_type": "BASE64",
                "group_id": settings.baidu_face_group,
                "user_id": user_id,
                "action_type": "REPLACE",
            },
        )
        token = (payload.get("result") or {}).get("face_token")
        if not token:
            raise FaceServiceError(payload.get("error_code"), "百度未返回 face_token")
        return token

    def delete_face(self, user_id: str) -> None:
        """从人脸库删除指定用户的人脸。"""
        self._post(
            DELETE_FACE_URL,
            {"group_id": settings.baidu_face_group, "user_id": user_id},
        )

    def search(self, image: str, *, user_id: str | None = None) -> dict:
        """1:N 人脸搜索，可按 user_id 限定到某个员工。"""
        body = {
            "image": strip_data_url_prefix(image),
            "image_type": "BASE64",
            "group_id_list": settings.baidu_face_group,
        }
        if user_id:
            body["user_id"] = user_id
        payload = self._post(SEARCH_URL, body)
        result = payload.get("result") or {}
        matches = result.get("user_list") or []
        if not matches:
            raise FaceServiceError(222208, "人脸库中未匹配到该员工")
        match = matches[0]
        return {
            "user_id": match.get("user_id"),
            "score": float(match.get("score") or 0),
            "face_token": match.get("face_token"),
        }

    def _post(self, url: str, body: dict) -> dict:
        token = self.get_access_token()
        try:
            response = self._session.post(
                url,
                params={"access_token": token},
                json=body,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise FaceNetworkError(f"无法连接百度云：{exc}") from exc
        payload = self._json(response)
        error_code = payload.get("error_code")
        if error_code not in (0, None):
            message = payload.get("error_msg") or "百度人脸接口调用失败"
            if error_code == 222207:
                raise NoFaceDetected(error_code, message)
            raise FaceServiceError(error_code, message)
        return payload

    @staticmethod
    def _json(response: requests.Response) -> dict:
        try:
            return response.json()
        except ValueError as exc:
            raise FaceNetworkError("百度云返回了非 JSON 响应") from exc


_client: BaiduFaceClient | None = None


def get_face_client() -> BaiduFaceClient:
    """FastAPI 依赖：返回进程内复用的百度人脸客户端（token 有缓存）。"""
    global _client
    if _client is None:
        _client = BaiduFaceClient()
    return _client
