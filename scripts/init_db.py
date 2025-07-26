
import sys, pathlib
sys.path.append(pathlib.Path(__file__).resolve().parents[1].as_posix())


"""Database initialization script.

이 스크립트는 SQLAlchemy `Base` 메타데이터를 사용해
모든 테이블을 DB에 생성합니다. (DDL 실행)
"""

from utils.db import Base, engine          # ← Base & engine 정의
import app.services.models  # noqa: F401  (테이블 메타데이터 로드용)


def main() -> None:
    """Create all tables defined in db.models."""
    Base.metadata.create_all(bind=engine)
    print("All tables created (if not exist).")


if __name__ == "__main__":
    main()