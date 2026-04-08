import hashlib
import secrets
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from config import SECRET_KEY
from sqlalchemy.orm import Session

from web.models import User, UserRole
from web.schemas import UserCreate, UserLogin

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    salt, stored_hash = hashed_password.split(":")
    hash_obj = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode(), salt.encode(), 100000
    )
    return hash_obj.hex() == stored_hash


def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"{salt}:{hash_obj.hex()}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def register_user(db: Session, user_data: UserCreate) -> tuple[Optional[User], str]:
    existing = (
        db.query(User)
        .filter((User.username == user_data.username) | (User.email == user_data.email))
        .first()
    )

    if existing:
        if existing.username == user_data.username:
            return None, "Имя пользователя уже занято"
        return None, "Email уже зарегистрирован"

    hashed_password = get_password_hash(user_data.password)

    role = UserRole.admin if user_data.role == "admin" else UserRole.player

    db_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        role=role,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user, ""


def authenticate_user(db: Session, login_data: UserLogin) -> tuple[Optional[User], str]:
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user:
        return None, "Пользователь не найден"

    if not verify_password(login_data.password, user.password_hash):
        return None, "Неверный пароль"

    user.role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return user, ""


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
