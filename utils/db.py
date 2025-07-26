# utils/db.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ==================================================================
# get_settings 함수 대신 DATABASE_URL 변수를 직접 임포트합니다.
from utils.config import DATABASE_URL
# ==================================================================

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL)

# 데이터베이스 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy 모델의 베이스 클래스
Base = declarative_base()