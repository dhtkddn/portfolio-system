# utils/config.py

import os
from dotenv import load_dotenv
from pathlib import Path

# .env 파일의 절대 경로를 명시적으로 지정하여 확실하게 로드합니다.
project_root = Path(__file__).resolve().parents[1]
env_path = project_root / '.env'
load_dotenv(dotenv_path=env_path)

# API 키 및 설정을 변수로 정의
DART_API_KEY = os.getenv("DART_API_KEY")
NCP_CLOVASTUDIO_API_KEY_ID = os.getenv("NCP_CLOVASTUDIO_API_KEY_ID")  
NCP_CLOVASTUDIO_API_KEY = os.getenv("NCP_CLOVASTUDIO_API_KEY")
NCP_CLOVASTUDIO_API_URL = os.getenv("NCP_CLOVASTUDIO_API_URL")
NCP_CLOVASTUDIO_REQUEST_ID = os.getenv("NCP_CLOVASTUDIO_REQUEST_ID")

# ✨ 숫자 타입 변환 추가
try:
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "32000"))
except (ValueError, TypeError):
    MAX_TOKENS = 32000

try:
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))
except (ValueError, TypeError):
    REQUEST_TIMEOUT = 180

# 🔧 기존 DB_URL을 그대로 사용하도록 수정
DATABASE_URL = os.getenv("DB_URL")  # 기존 변수명 DB_URL 사용

if not DATABASE_URL:
    # DB_URL이 없으면 개별 변수들로 구성 (fallback)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
    DB_NAME = os.getenv("DB_NAME", "portfolio")
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    # DB_URL에서 개별 변수들 추출 (필요한 경우를 위해)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        DB_HOST = parsed.hostname or "localhost"
        DB_PORT = str(parsed.port) if parsed.port else "5432"
        DB_USER = parsed.username or "postgres"
        DB_PASSWORD = parsed.password or "password"
        DB_NAME = parsed.path.lstrip('/') if parsed.path else "portfolio"
    except Exception:
        # URL 파싱 실패 시 기본값 사용
        DB_HOST = "localhost"
        DB_PORT = "5432"
        DB_USER = "postgres"
        DB_PASSWORD = "password"
        DB_NAME = "portfolio"

# 설정 클래스 (backward compatibility)
class Settings:
    def __init__(self):
        self.database_url = DATABASE_URL
        self.dart_api_key = DART_API_KEY
        self.db_host = DB_HOST
        self.db_port = DB_PORT
        self.db_user = DB_USER
        self.db_password = DB_PASSWORD
        self.db_name = DB_NAME

def get_settings():
    return Settings()