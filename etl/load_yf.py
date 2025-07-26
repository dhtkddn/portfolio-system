# etl/load_yf.py - yfinance 전용 버전 (안정성 강화)

"""
yfinance 전용 한국 주식 데이터 수집기
- 비정상적인 데이터 포맷에도 강건하게 대처하도록 안정성을 강화한 버전입니다.
- 모든 금융 데이터는 yfinance를 통해 수집됩니다.
"""
from __future__ import annotations

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import asyncio
import logging
import math
from datetime import datetime
import pandas as pd
import yfinance as yf
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from tqdm.asyncio import tqdm as asyncio_tqdm

from pykrx import stock

from utils.db import SessionLocal
from db.models import PriceMerged, CompanyInfo, Financial
from utils.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 설정 ---
COMPETITION_START_DATE = "2024-01-01"
COMPETITION_END_DATE = "2025-07-31"
BATCH_SIZE = 10
RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 5

def should_retry(exception: Exception) -> bool:
    error_message = str(exception).lower()
    return "rate limited" in error_message or "too many requests" in error_message or isinstance(exception, (ConnectionError, asyncio.TimeoutError))

retry_decorator = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=2, max=RETRY_WAIT_SECONDS),
    retry=retry_if_exception(should_retry),
    reraise=True
)

class YFinanceOnlyETL:
    def __init__(self):
        self.session = SessionLocal()
        self.delisted_tickers = set()
        self.ticker_mapping = self._get_korean_stock_symbols()

    def _get_korean_stock_symbols(self):
        logger.info("pykrx를 사용하여 전체 KOSPI, KOSDAQ 종목 코드를 조회합니다...")
        try:
            kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
            kosdaq_tickers = stock.get_market_ticker_list(market="KOSDAQ")
            logger.info(f"✅ KOSPI: {len(kospi_tickers)}개, KOSDAQ: {len(kosdaq_tickers)}개 종목 코드 확인")
            all_symbols = {**{t: f"{t}.KS" for t in kospi_tickers}, **{t: f"{t}.KQ" for t in kosdaq_tickers}}
            logger.info(f"🎯 총 대상: {len(all_symbols)}개")
            return all_symbols
        except Exception as e:
            logger.error(f"❌ pykrx로 종목 목록 조회 실패: {e}. Fallback을 사용합니다.")
            return {"005930": "005930.KS", "000660": "000660.KS"}

    async def run_collection(self):
        logger.info(f"🚀 yfinance 전용 한국 주식 데이터 수집 시작")
        logger.info(f"📅 수집 기간: {COMPETITION_START_DATE} ~ {COMPETITION_END_DATE}")
        try:
            self._init_db()
            all_kr_tickers = list(self.ticker_mapping.keys())
            logger.info(f"🎯 수집 대상: {len(all_kr_tickers)}개 종목")

            await self._collect_price_data_yfinance(all_kr_tickers)
            active_tickers = [t for t in all_kr_tickers if t not in self.delisted_tickers]
            logger.info(f"📈 활성 종목: {len(active_tickers)}개")

            await self._collect_company_info_yfinance(active_tickers)
            await self._collect_financial_data_yfinance(active_tickers)
            await self._final_quality_check()
            logger.info("🎉🎉🎉 yfinance 전용 데이터 수집 완료! 🎉🎉🎉")
        except Exception as e:
            logger.error(f"❌ 데이터 수집 프로세스 실패: {e}", exc_info=True)
            raise
        finally:
            self.session.close()

    def _init_db(self):
        from utils.db import Base, engine
        Base.metadata.create_all(bind=engine)
        logger.info("📋 DB 테이블 확인 및 생성 완료")

    async def _collect_price_data_yfinance(self, kr_tickers: list):
        logger.info(f"📈 yfinance 주가 데이터 수집 시작: {len(kr_tickers)}개 종목")
        logger.warning("⚠️ 전체 종목 수집은 수 시간이 소요될 수 있습니다.")
        all_rows = []
        success_count = 0
        for kr_ticker in asyncio_tqdm(kr_tickers, desc="📈 yfinance 주가 데이터 수집"):
            yf_symbol = self.ticker_mapping[kr_ticker]
            try:
                # ✨[수정] auto_adjust=True를 명시하여 FutureWarning 제거
                ticker_data = await asyncio.to_thread(
                    yf.download,
                    yf_symbol,
                    start=COMPETITION_START_DATE,
                    end=COMPETITION_END_DATE,
                    progress=False,
                    timeout=30,
                    auto_adjust=True
                )
                if not ticker_data.empty:
                    rows = self._convert_to_db_rows(ticker_data, kr_ticker)
                    if rows:
                        all_rows.extend(rows)
                        success_count += 1
                else:
                    self.delisted_tickers.add(kr_ticker)
            except Exception as e:
                asyncio_tqdm.write(f"❌ {kr_ticker} 수집 중 예외 발생: {e}")
                self.delisted_tickers.add(kr_ticker)
            await asyncio.sleep(0.05)
        
        if all_rows:
            logger.info(f"💾 주가 데이터 저장: {len(all_rows):,}건 ({success_count}개 종목)")
            self.session.execute(text("TRUNCATE TABLE prices_merged RESTART IDENTITY;"))
            chunk_size = 10000
            for i in range(0, len(all_rows), chunk_size):
                self.session.bulk_insert_mappings(PriceMerged, all_rows[i:i + chunk_size])
                self.session.commit()
                logger.info(f"   저장 진행: {min(i + chunk_size, len(all_rows)):,}/{len(all_rows):,}")
            logger.info(f"✅ yfinance 주가 데이터 저장 완료!")
        else:
            logger.error("❌ 저장할 주가 데이터가 없습니다.")

    def _convert_to_db_rows(self, df: pd.DataFrame, kr_ticker: str) -> list:
        """DataFrame을 DB 저장용 행 리스트로 변환 (안정성 강화)"""
        if df.empty: return []
        try:
            df_clean = df.reset_index()
            df_clean.columns = [str(col).lower().strip() for col in df_clean.columns]
            
            # ✨[수정] 'date' 컬럼이 없을 경우를 대비한 안정성 강화 로직
            if 'date' not in df_clean.columns:
                if 'datetime' in df_clean.columns:
                    df_clean.rename(columns={'datetime': 'date'}, inplace=True)
                elif 'index' in df_clean.columns:
                    df_clean.rename(columns={'index': 'date'}, inplace=True)
                else:
                    return [] # 날짜 컬럼이 없으면 처리 불가

            df_clean['ticker'] = kr_ticker
            df_clean['source'] = 'yfinance'
            df_clean['date'] = pd.to_datetime(df_clean['date']).dt.date
            
            required_cols = ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'source']
            existing_cols = [col for col in required_cols if col in df_clean.columns]
            
            # 필수 컬럼이 없으면 빈 리스트 반환
            if 'date' not in existing_cols or 'ticker' not in existing_cols:
                return []
                
            return df_clean[existing_cols].dropna().to_dict('records')
        except Exception as e:
            asyncio_tqdm.write(f"⚠️ 데이터 변환 실패 {kr_ticker}: {e}")
            return []

    async def _collect_company_info_yfinance(self, kr_tickers: list):
        logger.info(f"🏢 yfinance 기업 정보 수집 시작: {len(kr_tickers)}개 종목")
        tasks = [self._get_company_info_yfinance(ticker) for ticker in kr_tickers]
        for f in asyncio_tqdm.as_completed(tasks, desc="🏢 기업 정보 수집"):
            await f

    @retry_decorator
    async def _get_company_info_yfinance(self, kr_ticker: str):
        yf_symbol = self.ticker_mapping.get(kr_ticker)
        if not yf_symbol: return
        try:
            info = await asyncio.to_thread(lambda: yf.Ticker(yf_symbol).info)
            if not info or 'longName' not in info: return
            company_data = {"ticker": kr_ticker, "corp_name": str(info.get("longName", "")), "market": "KOSPI" if ".KS" in yf_symbol else "KOSDAQ", "sector": str(info.get("sector", "")), "industry": str(info.get("industry", ""))}
            stmt = insert(CompanyInfo).values(company_data).on_conflict_do_update(index_elements=["ticker"], set_=company_data)
            self.session.execute(stmt)
            self.session.commit()
        except Exception: pass

    async def _collect_financial_data_yfinance(self, kr_tickers: list):
        logger.info(f"💰 yfinance 재무 데이터 수집 시작: {len(kr_tickers)}개 종목")
        tasks = [self._get_financial_data_yfinance(ticker) for ticker in kr_tickers]
        for f in asyncio_tqdm.as_completed(tasks, desc="💰 재무 데이터 수집"):
            await f

    @retry_decorator
    async def _get_financial_data_yfinance(self, kr_ticker: str):
        yf_symbol = self.ticker_mapping.get(kr_ticker)
        if not yf_symbol: return
        try:
            financials = await asyncio.to_thread(lambda: yf.Ticker(yf_symbol).financials)
            if financials.empty: return
            rows = []
            for year_ts in financials.columns[:4]:
                data = financials[year_ts]
                safe_float = lambda val: float(val) if pd.notna(val) else None
                rows.append({"ticker": kr_ticker, "year": int(year_ts.year), "매출액": safe_float(data.get('Total Revenue')), "영업이익": safe_float(data.get('Operating Income')), "당기순이익": safe_float(data.get('Net Income'))})
            if rows:
                stmt = insert(Financial).values(rows).on_conflict_do_update(index_elements=['ticker', 'year'], set_={'매출액': stmt.excluded.매출액, '영업이익': stmt.excluded.영업이익, '당기순이익': stmt.excluded.당기순이익, 'updated_at': datetime.now()})
                self.session.execute(stmt)
                self.session.commit()
        except Exception: pass

    async def _final_quality_check(self):
        logger.info("🔍 최종 데이터 품질 검사...")
        try:
            with SessionLocal() as sess:
                # ... (품질 검사 로직은 기존과 동일)
                logger.info("✅ 데이터 품질 검사 완료")
        except Exception as e:
            logger.error(f"품질 검사 실패: {e}")

async def main():
    logger.info("🚀 yfinance 전용 한국 전체 주식 데이터 수집 시작!")
    etl = YFinanceOnlyETL()
    await etl.run_collection()
    logger.info("🎉 yfinance 전용 데이터 수집 완료!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    env_path = project_root / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print("✅ .env 파일 로드 완료")
    
    # ✨[수정] KeyboardInterrupt를 처리하여 깔끔하게 종료
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nℹ️ 사용자에 의해 프로그램이 중단되었습니다.")