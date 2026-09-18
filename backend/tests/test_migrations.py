"""I2：Alembic 迁移文件存在且能生成离线 SQL。"""

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import settings


BACKEND_DIR = Path(__file__).resolve().parent.parent


def _config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def test_initial_migration_exists():
    versions = Path(BACKEND_DIR / "alembic" / "versions")
    assert list(versions.glob("*.py")), "缺少初始迁移脚本"


def test_migration_offline_sql_generates():
    cfg = _config()
    command.upgrade(cfg, "head", sql=True)

