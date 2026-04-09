import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://gnomes:gnomes_secret@localhost:5432/gnomes_game"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    code = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GameResult(Base):
    __tablename__ = "game_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    opponent_type = Column(String(20), nullable=False)
    opponent_id = Column(
        Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True
    )
    result = Column(String(10), nullable=False)
    user_score = Column(Integer, nullable=False)
    opponent_score = Column(Integer, nullable=False)
    turns = Column(Integer, nullable=False)
    played_at = Column(DateTime(timezone=True), server_default=func.now())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
