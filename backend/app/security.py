"""安全工具：密码哈希校验与 JWT 签发/解码。

登录流程只使用账号密码，人脸识别仅用于考勤打卡，二者互不混用。
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings


JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """使用 bcrypt 生成密码哈希，数据库中只保存哈希值。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """校验明文密码与数据库中的哈希是否匹配。"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        # 哈希格式非法（例如手工改库）时按校验失败处理，不抛 500
        return False


def create_access_token(
    *,
    user_id: int,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """签发访问令牌；默认有效期取配置中的 ACCESS_TOKEN_EXPIRE_MINUTES。"""
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """解码并校验令牌；签名错误、过期等情况统一抛 jwt.PyJWTError。"""
    return jwt.decode(token, settings.secret_key, algorithms=[JWT_ALGORITHM])
