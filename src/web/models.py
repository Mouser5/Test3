import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
import enum

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://gnomes:gnomes_secret@localhost:5432/gnomes_game"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserRole(enum.Enum):
    player = "player"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.admin, nullable=False)
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


class TournamentStatus(enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    cancelled = "cancelled"


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    status = Column(Enum(TournamentStatus), default=TournamentStatus.pending)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class TournamentGame(Base):
    __tablename__ = "tournament_games"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(
        Integer,
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot1_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    bot2_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    bot1_name = Column(String(100), nullable=False)
    bot2_name = Column(String(100), nullable=False)
    game_order = Column(Integer, nullable=False)
    bot1_score = Column(Integer, nullable=False, default=0)
    bot2_score = Column(Integer, nullable=False, default=0)
    winner = Column(Integer, nullable=True)
    turns = Column(Integer, nullable=False, default=0)
    played_at = Column(DateTime(timezone=True), server_default=func.now())


class TournamentResult(Base):
    __tablename__ = "tournament_results"

    id = Column(Integer, primary_key=True, index=True)
    tournament_id = Column(
        Integer,
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bot_id = Column(Integer, ForeignKey("bots.id", ondelete="SET NULL"), nullable=True)
    bot_name = Column(String(100), nullable=False)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    draws = Column(Integer, nullable=False, default=0)
    total_score = Column(Integer, nullable=False, default=0)
    games_played = Column(Integer, nullable=False, default=0)


class GameLog(Base):
    __tablename__ = "game_logs"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(36), unique=True, nullable=False, index=True)
    bot1_code = Column(Text, nullable=True)
    bot2_code = Column(Text, nullable=True)
    dsl_log = Column(Text, nullable=False)
    scores_p0 = Column(Integer, nullable=False)
    scores_p1 = Column(Integer, nullable=False)
    winner = Column(Integer, nullable=True)
    turns = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
