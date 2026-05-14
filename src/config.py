import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GAME_API_URL = os.getenv("GAME_API_URL", "http://game-api:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "gnomes-secret-key-change-in-production")
POSTGRES_USER = os.getenv("POSTGRES_USER", "gnomes")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "gnomes_secret")
POSTGRES_DB = os.getenv("POSTGRES_DB", "gnomes_game")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)
LOG_DIR = Path(os.getenv("LOG_DIR", "/app/logs"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")
