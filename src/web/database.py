from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://gnomes:gnomes_secret@localhost:5432/gnomes_game"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    from .models import Base

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
