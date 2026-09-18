"""为项目创建 MySQL 数据库与专用账号（一次性初始化）。"""

import sys

from sqlalchemy import create_engine, text

from app.config import settings


def setup_db() -> None:
    """使用 root 连接，创建业务库和账号；已存在则幂等跳过。"""
    engine = create_engine(settings.mysql_root_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE DATABASE IF NOT EXISTS "
                    "`{}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(
                        settings.mysql_database
                    )
                )
            )
            # MySQL 8 对 create user 和 grant 不支持参数绑定，故用格式化安全值
            conn.execute(
                text(
                    "CREATE USER IF NOT EXISTS '{}'@'%' IDENTIFIED BY '{}'".format(
                        settings.mysql_user, settings.mysql_password
                    )
                )
            )
            conn.execute(
                text(
                    "GRANT ALL PRIVILEGES ON `{}`.* TO '{}'@'%'".format(
                        settings.mysql_database, settings.mysql_user
                    )
                )
            )
            conn.execute(text("FLUSH PRIVILEGES"))
            conn.commit()
        print(
            f"数据库 {settings.mysql_database} 与账号 {settings.mysql_user} 已就绪。"
        )
    except Exception as exc:
        print(f"初始化失败：{exc}", file=sys.stderr)
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    setup_db()
