"""SQLAlchemy 엔진 · 세션 · Base 유틸리티."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from utils.config import get_settings
# ──────────────────────────────────────────────────────────────────────────────
# 엔진 & 세션 설정
# ──────────────────────────────────────────────────────────────────────────────
settings = get_settings()

# SQLAlchemy expects a string URL; convert PostgresDsn → str
SQLALCHEMY_DATABASE_URL: str = str(settings.db_url)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Declarative Base (모든 모델이 상속)
Base = declarative_base()

# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 컨텍스트 매니저
# ──────────────────────────────────────────────────────────────────────────────
@contextmanager
def get_db() -> Iterator:
    """Yield SQLAlchemy session & ensure close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# FastAPI dependency (generator alias)
def get_db_dep() -> Generator:
    """FastAPI Depends 용 래퍼."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



from db import models            # SQLAlchemy 모델 재노출
__all__ = ["engine", "SessionLocal", "Base", "get_db", "get_db_dep"]
__all__.append("models")