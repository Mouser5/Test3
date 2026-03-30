import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://gnomes:gnomes_secret@localhost:5432/gnomes_game"
)


def create_tables():
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bots (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_results (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            bot_id INTEGER REFERENCES bots(id) ON DELETE SET NULL,
            opponent_type VARCHAR(20) NOT NULL,
            opponent_id INTEGER REFERENCES bots(id) ON DELETE SET NULL,
            result VARCHAR(10) NOT NULL,
            user_score INTEGER NOT NULL,
            opponent_score INTEGER NOT NULL,
            turns INTEGER NOT NULL,
            played_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bots_user_id ON bots(user_id);")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_game_results_user_id ON game_results(user_id);"
    )

    cursor.close()
    conn.close()
    print("Database tables created successfully!")


if __name__ == "__main__":
    create_tables()
