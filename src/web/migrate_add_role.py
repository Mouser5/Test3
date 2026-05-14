import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from web.database import engine


def migrate_add_role_column():
    with engine.connect() as conn:
        try:
            conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin' NOT NULL"
                )
            )
            conn.commit()
            print("✅ Колонка role добавлена в таблицу users")
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            conn.rollback()


if __name__ == "__main__":
    migrate_add_role_column()
