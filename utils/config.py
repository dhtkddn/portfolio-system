"""환경 변수 로딩 · 설정 모듈."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import PostgresDsn

# ──────────────────────────────────────────────────────────────────────────────
# 경로 상수
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# ──────────────────────────────────────────────────────────────────────────────
# Settings 클래스 (Pydantic)
# ──────────────────────────────────────────────────────────────────────────────
class Settings(BaseSettings):
    """앱 전역 설정 (env → 속성 자동 매핑)."""

    # Database
    db_url: PostgresDsn = (
        "postgresql+psycopg2://user:pass@localhost:5432/portfolio"  # default
    )

    # API Keys
    dart_api_key: str | None = None            # .env: DART_API_KEY
    clova_api_key: str | None = None           # .env: NCP_CLOVASTUDIO_API_KEY

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"   # unknown .env keys are ignored


# ──────────────────────────────────────────────────────────────────────────────
# 캐싱된 싱글톤 제공 함수
# ──────────────────────────────────────────────────────────────────────────────
@lru_cache
def get_settings() -> Settings:
    """전역 Settings 인스턴스 (lru_cache 1)."""
    return Settings()