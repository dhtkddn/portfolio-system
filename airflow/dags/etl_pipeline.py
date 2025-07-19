"""Enhanced Airflow DAG: yfinance 중심의 지능형 ETL 파이프라인."""

from __future__ import annotations

from datetime import timedelta, datetime
from pathlib import Path
import pendulum

import sys
PYTHON_BIN = sys.executable

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.sensors.filesystem import FileSensor
from airflow.operators.email import EmailOperator

# 프로젝트 설정
local_tz = pendulum.timezone("Asia/Seoul")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ETL_DIR = PROJECT_ROOT / "etl"
ENV = {"PYTHONPATH": str(PROJECT_ROOT)}

# DAG 기본 설정
default_args = {
    "owner": "portfolio-ai-team",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

# 메인 ETL DAG
with DAG(
    dag_id="enhanced_portfolio_etl",
    default_args=default_args,
    description="yfinance 중심의 지능형 포트폴리오 ETL 파이프라인",
    schedule_interval="0 18 * * 1-5",  # 평일 18:00 KST
    catchup=False,
    max_active_runs=1,
    tags=["portfolio", "yfinance", "ai", "stocks"],
) as main_dag:

    # 1. 데이터 수집 태스크들
    collect_company_info = BashOperator(
        task_id="collect_company_info",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_yf_enhanced.py'} company",
        env=ENV,
        doc_md="""
        ## 기업 정보 수집
        
        yfinance API를 사용하여 KOSPI/KOSDAQ 전체 기업의 기본 정보를 수집합니다:
        - 회사명, 섹터, 업종
        - 시가총액, 직원 수
        - 웹사이트, 사업 개요
        """
    )

    collect_price_data = BashOperator(
        task_id="collect_price_data",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_yf_enhanced.py'} prices",
        env=ENV,
        doc_md="""
        ## 가격 데이터 수집
        
        yfinance를 통해 주식 가격 데이터를 수집합니다:
        - OHLCV 데이터 (최근 30일)
        - 실시간 업데이트
        - 데이터 품질 검증
        """
    )

    collect_financial_data = BashOperator(
        task_id="collect_financial_data", 
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_yf_enhanced.py'} financials",
        env=ENV,
        doc_md="""
        ## 재무 데이터 수집
        
        기업의 재무제표 데이터를 수집합니다:
        - 매출액, 영업이익, 당기순이익
        - 최근 3개년 데이터
        - 성장률 계산
        """
    )

    # 2. 데이터 품질 검사
    quality_check = BashOperator(
        task_id="quality_check",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_yf_enhanced.py'} quality",
        env=ENV,
        doc_md="""
        ## 데이터 품질 검사
        
        수집된 데이터의 품질을 검증합니다:
        - 결측값 비율 확인
        - 데이터 범위 검증
        - 품질 점수 산출
        """
    )

    # 3. AI 모델 준비 (Python 함수)
    def prepare_ai_models():
        """AI 모델 및 RAG 시스템 준비."""
        import asyncio
        from app.services.stock_database import stock_database
        
        # 종목 데이터베이스 캐시 갱신
        asyncio.run(stock_database.get_all_stocks(force_refresh=True))
        
        # HyperCLOVA 연결 테스트
        from app.services.portfolio import test_hyperclova
        test_result = asyncio.run(test_hyperclova())
        
        if not test_result:
            raise Exception("HyperCLOVA 연결 실패")
        
        print("✅ AI 모델 준비 완료")

    prepare_ai = PythonOperator(
        task_id="prepare_ai_models",
        python_callable=prepare_ai_models,
        doc_md="""
        ## AI 모델 준비
        
        AI 에이전트 시스템을 준비합니다:
        - RAG 데이터베이스 캐시 갱신
        - HyperCLOVA 연결 테스트
        - 종목 정보 인덱싱
        """
    )

    # 4. 알림 태스크
    def send_completion_notification():
        """ETL 완료 알림."""
        from datetime import datetime
        
        completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""
        🎉 Portfolio AI ETL 파이프라인 완료!
        
        완료 시간: {completion_time}
        처리된 태스크:
        ✅ 기업 정보 수집
        ✅ 가격 데이터 수집  
        ✅ 재무 데이터 수집
        ✅ 데이터 품질 검사
        ✅ AI 모델 준비
        
        시스템이 사용자 요청을 받을 준비가 되었습니다.
        """
        
        print(message)
        return message

    completion_notification = PythonOperator(
        task_id="completion_notification",
        python_callable=send_completion_notification
    )

    # 태스크 의존성 설정
    collect_company_info >> [collect_price_data, collect_financial_data]
    [collect_price_data, collect_financial_data] >> quality_check
    quality_check >> prepare_ai >> completion_notification


# 일일 업데이트 DAG (가벼운 버전)
with DAG(
    dag_id="daily_price_update",
    default_args=default_args,
    description="일일 주식 가격 데이터 업데이트",
    schedule_interval="0 9 * * 1-5",  # 평일 09:00 KST (장 시작 전)
    catchup=False,
    tags=["portfolio", "daily", "price"],
) as daily_dag:

    daily_price_update = BashOperator(
        task_id="daily_price_update",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_yf_enhanced.py'} daily",
        env=ENV,
    )

    # 시장 개장 전 준비
    def prepare_trading_day():
        """거래일 시작 전 준비 작업."""
        import asyncio
        from app.services.stock_database import stock_database
        
        # 캐시 갱신
        asyncio.run(stock_database.get_all_stocks(force_refresh=True))
        
        print("📈 오늘의 거래 준비 완료")

    prepare_trading = PythonOperator(
        task_id="prepare_trading_day",
        python_callable=prepare_trading_day
    )

    daily_price_update >> prepare_trading


# 주간 전체 업데이트 DAG
with DAG(
    dag_id="weekly_full_update", 
    default_args=default_args,
    description="주간 전체 데이터 업데이트 및 모델 재학습",
    schedule_interval="0 20 * * 0",  # 일요일 20:00 KST
    catchup=False,
    tags=["portfolio", "weekly", "full"],
) as weekly_dag:

    weekly_full_etl = BashOperator(
        task_id="weekly_full_etl",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_yf_enhanced.py'} full",
        env=ENV,
        execution_timeout=timedelta(hours=3),
    )

    # 포트폴리오 최적화 엔진 테스트
    def test_portfolio_optimizer():
        """포트폴리오 최적화 엔진 테스트."""
        from optimizer.optimize import test_optimizer
        
        if not test_optimizer():
            raise Exception("포트폴리오 최적화 엔진 테스트 실패")
        
        print("✅ 포트폴리오 최적화 엔진 정상")

    test_optimizer_task = PythonOperator(
        task_id="test_portfolio_optimizer",
        python_callable=test_portfolio_optimizer
    )

    # AI 에이전트 성능 테스트
    def test_ai_agent():
        """AI 에이전트 성능 테스트."""
        import asyncio
        from app.services.ai_agent import chat_with_agent
        from app.services.models import UserProfile
        
        # 테스트 케이스
        test_profile = UserProfile(
            age=35,
            investment_amount=1000,
            experience_level="초보",
            risk_tolerance="중립형"
        )
        
        test_message = "월 100만원 투자 가능한 초보자에게 포트폴리오 추천해주세요"
        
        try:
            response = asyncio.run(chat_with_agent(test_message, test_profile))
            
            if not response.message or len(response.message) < 100:
                raise Exception("AI 응답이 너무 짧습니다")
            
            print("✅ AI 에이전트 테스트 통과")
            print(f"응답 길이: {len(response.message)}자")
            
        except Exception as e:
            raise Exception(f"AI 에이전트 테스트 실패: {e}")

    test_ai_task = PythonOperator(
        task_id="test_ai_agent",
        python_callable=test_ai_agent
    )

    # 시스템 성능 리포트
    def generate_performance_report():
        """시스템 성능 리포트 생성."""
        from utils.db import SessionLocal
        from sqlalchemy import text
        from datetime import datetime, timedelta
        
        session = SessionLocal()
        
        try:
            # 데이터 통계
            stats = {}
            
            # 종목 수
            result = session.execute(text("SELECT COUNT(*) FROM company_info"))
            stats['total_companies'] = result.scalar()
            
            # 가격 데이터 수
            result = session.execute(text("SELECT COUNT(*) FROM prices_merged"))
            stats['total_price_records'] = result.scalar()
            
            # 최근 1주일 데이터
            week_ago = datetime.now() - timedelta(days=7)
            result = session.execute(
                text("SELECT COUNT(*) FROM prices_merged WHERE date >= :date"),
                {"date": week_ago.date()}
            )
            stats['recent_price_records'] = result.scalar()
            
            # 재무 데이터
            result = session.execute(text("SELECT COUNT(*) FROM financials"))
            stats['financial_records'] = result.scalar()
            
            # 리포트 출력
            print("📊 시스템 성능 리포트")
            print(f"총 기업 수: {stats['total_companies']:,}")
            print(f"총 가격 레코드: {stats['total_price_records']:,}")
            print(f"최근 1주일 데이터: {stats['recent_price_records']:,}")
            print(f"재무 데이터: {stats['financial_records']:,}")
            
            # 데이터 커버리지 계산
            coverage = (stats['recent_price_records'] / (stats['total_companies'] * 5)) * 100
            print(f"데이터 커버리지: {coverage:.1f}%")
            
            if coverage < 80:
                print("⚠️ 데이터 커버리지가 낮습니다")
            else:
                print("✅ 데이터 커버리지 양호")
                
        finally:
            session.close()

    performance_report = PythonOperator(
        task_id="generate_performance_report",
        python_callable=generate_performance_report
    )

    # 태스크 체인
    weekly_full_etl >> [test_optimizer_task, test_ai_task] >> performance_report


# 모니터링 DAG
with DAG(
    dag_id="system_monitoring",
    default_args=default_args,
    description="시스템 상태 모니터링",
    schedule_interval="0 * * * *",  # 매시간
    catchup=False,
    tags=["monitoring", "health"],
) as monitoring_dag:

    def check_system_health():
        """시스템 상태 확인."""
        from utils.db import SessionLocal
        from sqlalchemy import text
        import requests
        
        health_status = {"status": "healthy", "issues": []}
        
        # 1. 데이터베이스 연결 확인
        try:
            session = SessionLocal()
            session.execute(text("SELECT 1"))
            session.close()
        except Exception as e:
            health_status["issues"].append(f"DB 연결 실패: {e}")
        
        # 2. 최신 데이터 확인
        try:
            session = SessionLocal()
            result = session.execute(text("""
                SELECT MAX(date) FROM prices_merged
            """))
            latest_date = result.scalar()
            
            if latest_date:
                from datetime import datetime, timedelta
                if datetime.now().date() - latest_date > timedelta(days=3):
                    health_status["issues"].append(f"데이터가 오래됨: {latest_date}")
            
            session.close()
        except Exception as e:
            health_status["issues"].append(f"데이터 확인 실패: {e}")
        
        # 3. API 응답 확인 (FastAPI가 실행 중인 경우)
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code != 200:
                health_status["issues"].append("API 서버 응답 이상")
        except:
            health_status["issues"].append("API 서버 연결 불가")
        
        # 결과 출력
        if health_status["issues"]:
            health_status["status"] = "unhealthy"
            print(f"⚠️ 시스템 이상 감지: {health_status['issues']}")
        else:
            print("✅ 시스템 정상 동작")
        
        return health_status

    health_check = PythonOperator(
        task_id="system_health_check",
        python_callable=check_system_health
    )