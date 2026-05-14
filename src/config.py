import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

GAME_API_URL = os.getenv("GAME_API_URL", "http://game-api:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "gnomes-secret-key-change-in-production")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://gnomes:gnomes_secret@localhost:5432/gnomes_game"
)
LOG_DIR = Path(os.getenv("LOG_DIR", "/app/logs"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme123")
