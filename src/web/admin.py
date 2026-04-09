import os
import logging
from typing import List, Optional, Tuple
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from web.models import User, Bot
from web.schemas import BotCreate, UserCreate
from web.auth import get_password_hash

logger = logging.getLogger(__name__)


def ensure_default_admin_exists(db: Session) -> None:
    # Ensure the admin user exists in DB. If the role column is missing, try to create it.
    try:
        admin_exists = db.query(User).filter(User.role == "admin").first()
    except (OperationalError, ProgrammingError) as e:
        admin_exists = None
        logger.debug(f"Admin check failed (likely missing column): {e}")
        # Try to add the role column if missing
        try:
            db.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(10) NOT NULL DEFAULT 'user';")
            db.commit()
            admin_exists = db.query(User).filter(User.role == "admin").first()
        except Exception as e2:
            logger.exception(f"Failed to alter users table to add role column: {e2}")
            return

    if admin_exists:
        logger.info("Default admin already exists.")
        return

    # Resolve admin credentials: env vars or defaults for development
    admin_username = os.getenv("ADMIN_USERNAME") or os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL") or os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.local")
    admin_password = os.getenv("ADMIN_PASSWORD") or os.getenv("DEFAULT_ADMIN_PASSWORD", "change_me_please")
    password_source = "ENV" if os.getenv("ADMIN_PASSWORD") else "DEFAULT/ENV"
    print(f"[BOOT] Admin credentials: username={admin_username}, email={admin_email}, password_source={password_source}")

    existing = db.query(User).filter((User.username == admin_username) | (User.email == admin_email)).first()
    if existing:
        existing.role = "admin"
        db.commit()
        logger.info("Promoted existing user to admin")
        print("Promoted existing user to admin:", admin_username, admin_email)
        return

    hashed = get_password_hash(admin_password)
    admin = User(username=admin_username, email=admin_email, password_hash=hashed, role="admin")
    db.add(admin)
    db.commit()
    logger.info(f"Default admin created: {admin_username} ({admin_email})")
    print("Default admin created:", admin_username, admin_email)


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user_with_role(db: Session, user_data: UserCreate, role: str = "user") -> Tuple[Optional[User], str]:
    existing = db.query(User).filter((User.username == user_data.username) | (User.email == user_data.email)).first()
    if existing:
        if existing.username == user_data.username:
            return None, "Имя пользователя уже занято"
        return None, "Email уже зарегистрирован"
    hashed_password = get_password_hash(user_data.password)
    user = User(username=user_data.username, email=user_data.email, password_hash=hashed_password, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, ""


def set_user_role(db: Session, user_id: int, role: str) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.role = role
    db.commit()
    return True


def create_bot_for_user(db: Session, user_id: int, bot_data: BotCreate):
    bot = Bot(user_id=user_id, name=bot_data.name, code=bot_data.code)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot