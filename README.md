# portfolio-system
# MIRAE-PORTFOLIO

**AI 기반 한국 주식 맞춤 포트폴리오 추천 시스템**

---

## 🧠 프로젝트 개요

본 시스템은 한국 주식시장(KRX/KOSPI/KOSDAQ)의 가격 및 재무 데이터를 기반으로 고객 맞춤형 장기 포트폴리오를 추천하고, HyperCLOVA X API를 통해 설명까지 제공하는 AI 기반 투자 어드바이저입니다.

- **ETL 파이프라인:** PyKRX, Open DART, yFinance 데이터를 수집하고 PostgreSQL에 적재
- **API 서버:** FastAPI 기반 포트폴리오 추천 API
- **AI 설명:** HyperCLOVA X를 사용한 포트폴리오 설명 생성
- **모니터링:** ETL 품질 지표 및 yfinance 병합 검사 수행

---

## 📁 프로젝트 구조

```bash
portfolio-system/
├── airflow/dags/etl_pipeline.py       # Airflow DAG 정의 (BashOperator 기반)
├── app/
│   ├── services/
│   │   ├── models.py                  # Pydantic 데이터 모델
│   │   └── portfolio.py               # LLM 기반 설명 생성 로직
│   └── main.py                        # FastAPI 엔트리포인트
├── db/
│   ├── models.py                      # SQLAlchemy 모델 정의
│   └── __init__.py                    # 모델 일괄 임포트
├── etl/
│   ├── load_pykrx.py                  # KRX 가격 데이터 수집
│   ├── load_dart.py                  # DART 재무제표 수집
│   ├── load_yf.py                    # yfinance 데이터 수집
│   └── merge_quality.py             # 품질 검사 및 병합
├── .env                               # 환경 변수 설정
├── environment.yml                    # Conda 의존성 파일
└── README.md

  설치 방법
conda env create -f environment.yml
conda activate portfolio

  환경 변수 설정
DB_URL=postgresql+psycopg2://pguser:pgpass@localhost:5432/portfolio
DART_API_KEY=your_dart_api_key
NCP_CLOVASTUDIO_API_KEY=your_hyperclova_api_key
NCP_CLOVASTUDIO_API_URL=https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions/HCX-005
NCP_CLOVASTUDIO_REQUEST_ID=your_request_id

  API 테스트 (예시):
POST http://localhost:8000/portfolio/recommend
{
  "tickers": ["005930", "000660"],
  "age": 35,
  "experience": "초보",
  "risk_profile": "중립형",
  "investment_goal": "은퇴준비",
  "investment_period": "10년"
}