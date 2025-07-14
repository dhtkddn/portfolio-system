"""Airflow DAG: 한국 주식 포트폴리오용 ETL 파이프라인 (bash version)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import pendulum

import sys
PYTHON_BIN = sys.executable  # full path to the current Python interpreter

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

# ----------------------------------------------------------------------
local_tz = pendulum.timezone("Asia/Seoul")
# 환경 변수: 프로젝트 루트 경로 계산 (repo 최상위 디렉터리 기준)
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # …/portfolio-system
ETL_DIR = PROJECT_ROOT / "etl"
ENV = {"PYTHONPATH": str(PROJECT_ROOT)}

default_args = {
    "owner": "team5",
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="etl_pipeline",
    start_date=days_ago(1),
    schedule_interval="0 18 * * 1-5",  # 평일 18:00 KST
    catchup=False,
    default_args=default_args,
    tags=["krx", "dart", "yfinance"],
) as dag:

    load_pykrx = BashOperator(
        task_id="load_pykrx",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_pykrx.py'} ",
        env=ENV,
    )

    load_dart = BashOperator(
        task_id="load_dart",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_dart.py'} ",
        env=ENV,
    )

    load_yf = BashOperator(
        task_id="load_yf",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'load_yf.py'} ",
        env=ENV,
    )

    merge_qc = BashOperator(
        task_id="merge_qc",
        bash_command=f"{PYTHON_BIN} {ETL_DIR/'merge_quality.py'} ",
        env=ENV,
    )

    # 태스크 의존성
    load_pykrx >> load_dart >> load_yf >> merge_qc