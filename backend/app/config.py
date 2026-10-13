"""应用配置：优先读取环境变量，支持 backend/.env 文件。"""

import os
from pathlib import Path

from dotenv import load_dotenv


# 加载 backend/.env（存在时），再加载项目根目录 .env
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")


class Settings:
    """集中管理运行配置，I2 开始会接入 SQLAlchemy 与 JWT。"""

    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "employee_attendance")
        self.debug = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}

        # 百度 AI 人脸 API
        self.baidu_face_ak = os.getenv("BAIDU_FACE_AK", "")
        self.baidu_face_sk = os.getenv("BAIDU_FACE_SK", "")
        self.baidu_face_app_id = os.getenv("BAIDU_FACE_APP_ID", "")
        self.baidu_face_group = os.getenv(
            "BAIDU_FACE_GROUP", "employee_attendance"
        )
        self.baidu_face_score_threshold = int(
            os.getenv("BAIDU_FACE_SCORE_THRESHOLD", "80")
        )

        # JWT（I3 使用）
        self.secret_key = os.getenv(
            "SECRET_KEY", "dev-secret-change-me-please-use-a-random-key-0123456789"
        )
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

        # MySQL 直接连接本机 MySQL 服务
        self.mysql_host = os.getenv("MYSQL_HOST", "127.0.0.1")
        self.mysql_port = os.getenv("MYSQL_PORT", "3306")
        self.mysql_database = os.getenv("MYSQL_DATABASE", "employee_attendance")
        self.mysql_user = os.getenv("MYSQL_USER", "employee")
        self.mysql_password = os.getenv("MYSQL_PASSWORD", "employee123")
        # 仅创建数据库/初始化账号时使用的管理员连接
        self.mysql_root_user = os.getenv("MYSQL_ROOT_USER", "root")
        self.mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD", "root")
        # 测试或本地开发可通过 DATABASE_URL 覆盖；默认连接本机 MySQL
        self.database_url = os.getenv("DATABASE_URL") or (
            "mysql+pymysql://"
            f"{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def mysql_root_url(self) -> str:
        """root 连接 URL，不含库名，用于创建数据库与账号。"""
        return (
            "mysql+pymysql://"
            f"{self.mysql_root_user}:{self.mysql_root_password}"
            f"@{self.mysql_host}:{self.mysql_port}/?charset=utf8mb4"
        )


settings = Settings()
