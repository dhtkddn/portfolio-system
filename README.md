# 🚀 MIRAE-PORTFOLIO SYSTEM

**AI 기반 한국 주식 맞춤 포트폴리오 추천 시스템**

> HyperCLOVA X와 PostgreSQL을 활용한 지능형 투자 자문 플랫폼

**MIRAE-PORTFOLIO**는 한국 주식시장(KOSPI/KOSDAQ)의 실시간 데이터를 기반으로 개인 맞춤형 포트폴리오를 추천하는 AI 기반 투자 자문 시스템입니다.

### 🌟 핵심 가치

* **🎯 개인화**: 투자자의 나이, 경험, 위험성향에 맞춤형 포트폴리오 제공
* **🧠 AI 분석**: HyperCLOVA X를 활용한 지능형 재무분석 및 투자 설명
* **📊 실시간 데이터**: PyKRX, Yahoo Finance를 통한 최신 시장 데이터 수집
* **🔍 포괄적 분석**: 기술적 분석부터 재무제표 비교까지 원스톱 서비스

### 🎯 대상 사용자

* 📈 **개인 투자자**: 체계적인 포트폴리오 구성을 원하는 투자자
* 💼 **금융 자문사**: 고객 상담용 도구로 활용
* 🎓 **투자 학습자**: 투자 원리와 포트폴리오 이론 학습
* 🏢 **핀테크 기업**: 투자 서비스 개발을 위한 기반 시스템

---

## ✨ 주요 기능

### 🤖 AI 기반 대화형 투자 상담

사용자의 자연어 질문을 이해하고, 투자 성향을 파악하여 맞춤형 투자 포트폴리오를 추천합니다.

* **자연어 처리**: 한국어 투자 질문 자동 이해
* **의도 분석**: 포트폴리오/재무분석/시장분석 자동 분류
* **맞춤형 응답**: 사용자 프로필 기반 개인화된 투자 조언

### 📊 지능형 포트폴리오 최적화

PyPortfolioOpt 라이브러리를 기반으로 수학적 최적화와 실무적 제약조건을 결합한 3가지 포트폴리오 최적화 전략을 제공합니다.

* **Mathematical**: 샤프비율 최대화 (고급 투자자)
* **Practical**: 실용적 분산투자 (중급 투자자)
* **Conservative**: 안전 중심 분산 (초보 투자자)

### 💰 종합 재무제표 분석

DART API와 yfinance를 통해 수집된 재무 데이터를 기반으로 AI가 기업의 재무 상태를 다각도로 비교 분석하고, 시각화 자료와 함께 투자 인사이트를 제공합니다.

* **동적 기업명 매핑**: DB 기반 실시간 기업명 인식
* **다차원 비교**: 매출/영업이익/ROE 등 주요 지표 분석
* **트렌드 분석**: 연도별 성장성 및 안정성 평가

### 📈 실시간 시장 데이터 수집

PyKRX, Yahoo Finance, DART API 등 다중 소스로부터 데이터를 수집하여 PostgreSQL 데이터베이스에 저장하고, 데이터 품질을 지속적으로 관리합니다.

* **다중 소스 통합**: PyKRX + Yahoo Finance + DART API
* **배치 처리**: 대용량 데이터 안정적 수집 (100종목/배치)
* **품질 관리**: 데이터 무결성 검증 및 오류 처리
* **증분 업데이트**: 기존 데이터 보존하며 신규 데이터 추가

---

## 🛠️ 시스템 아키텍처

```mermaid
graph TD
    subgraph User Interface
        UI[Streamlit Web App]
    end

    subgraph API Server
        API[FastAPI]
    end

    subgraph AI Engine
        AGENT[AI Agent]
        OPTIMIZER[Portfolio Optimizer]
        LLM[HyperCLOVA X]
    end

    subgraph Data Layer
        DB[(PostgreSQL)]
        ETL[ETL Pipeline]
    end

    subgraph Data Sources
        KRX[PyKRX]
        YF[Yahoo Finance]
        DART[DART API]
    end

    UI --> API
    API --> AGENT
    AGENT --> OPTIMIZER
    AGENT --> LLM
    AGENT --> DB
    OPTIMIZER --> DB
    ETL --> DB
    ETL --> KRX
    ETL --> YF
    ETL --> DART

    📁 파일 구조

    dhtkddn/portfolio-system/
├── airflow/
│   └── dags/
│       └── etl_pipeline.py       # Airflow DAGs for ETL automation
├── app/
│   ├── services/
│   │   ├── ai_agent.py           # Main AI agent logic
│   │   ├── hyperclova_client.py  # HyperCLOVA X API client
│   │   ├── models.py             # Pydantic models for API
│   │   ├── news_analysis.py      # News sentiment analysis
│   │   ├── portfolio.py          # Basic portfolio creation
│   │   ├── portfolio_enhanced.py # Enhanced portfolio with multi-optimization
│   │   └── stock_database.py     # Stock data management
│   ├── schemas.py                # Pydantic schemas for API I/O
│   └── main.py                   # FastAPI main application
├── db/
│   ├── __init__.py
│   └── models.py                 # SQLAlchemy DB models
├── etl/
│   ├── load_dart.py              # DART financial data ETL
│   ├── load_dart_simple.py       # Simplified DART ETL
│   ├── load_pykrx.py             # PyKRX stock price ETL
│   ├── load_yf.py                # Yahoo Finance data ETL
│   └── merge_quality.py          # Data merging and quality check
├── optimizer/
│   └── optimize.py               # Portfolio optimization engine
├── scripts/
│   └── init_db.py                # Database initialization script
├── utils/
│   ├── config.py                 # Configuration settings
│   └── db.py                     # Database session management
├── .env                          # Environment variables (API keys, DB URL)
├── .gitignore                    # Git ignore file
├── README.md                     # Project documentation
├── requirements.txt              # Python package requirements
├── portfolio_ui.py               # Streamlit UI application
└── test_*.py                     # Various test scripts

🚀 시작하기
1. 환경 설정

요구사항:

Python 3.11+

PostgreSQL

Conda (권장)

.env 파일 생성:

프로젝트 루트 디렉토리에 .env 파일을 생성하고 다음 내용을 채웁니다.

# .env

# Database
DB_URL="postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>"

# APIs
DART_API_KEY="<your_dart_api_key>"
NCP_CLOVASTUDIO_API_URL="<your_clova_api_url>"
NCP_CLOVASTUDIO_API_KEY="<your_clova_api_key>"
NCP_CLOVASTUDIO_REQUEST_ID="<your_clova_request_id>"

2. 설치

Conda를 사용하여 가상 환경을 생성하고 필요한 패키지를 설치합니다.
conda env create -f environment.yml
conda activate portfolio

3. 데이터베이스 초기화

PostgreSQL 데이터베이스에 테이블을 생성합니다.

python scripts/init_db.py

4. 데이터 수집 (ETL)

yfinance를 사용하여 주식 데이터를 수집합니다. (전체 수집은 몇 시간이 소요될 수 있습니다.)

python etl/load_yf.py

5. API 서버 실행

FastAPI 서버를 실행합니다.

uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload

6. Streamlit UI 실행

별도의 터미널에서 Streamlit UI를 실행합니다.

streamlit run portfolio_ui.py

🧪 테스트
프로젝트에는 다양한 기능 테스트를 위한 스크립트가 포함되어 있습니다.

API 응답 완성도 테스트: python test_changes.py

AI 에이전트 기능 테스트: python examples/test_ai_agent.py

재무 데이터 처리 과정 테스트: python test_detailed_financial.py

수정사항 종합 테스트: python test_fixes.py

각 테스트 스크립트는 프로젝트 루트 디렉토리에서 실행할 수 있습니다.
