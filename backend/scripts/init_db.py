"""初始化数据库：执行 Alembic 迁移并写入演示数据。"""

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.database import SessionLocal
from app.seed import seed_data


BACKEND_DIR = Path(__file__).resolve().parent.parent


def init_db():
    """执行 Alembic 迁移并写入演示数据。"""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")

    session = SessionLocal()
    try:
        seed_data(session)
        print("数据库初始化完成：迁移已执行，演示数据已写入。")
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
