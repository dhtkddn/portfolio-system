"""향상된 yfinance ETL - 전체 KOSPI/KOSDAQ 데이터 수집."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text

from utils.db import SessionLocal
from db.models import PriceMerged, CompanyInfo, Financial

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedYFinanceETL:
    """yfinance 기반 향상된 ETL 시스템."""
    
    def __init__(self):
        self.session = SessionLocal()
        self.semaphore = asyncio.Semaphore(5)  # 동시 요청 제한
        
        # 한국 주식 티커 매핑
        self.ticker_mapping = self._load_ticker_mapping()
    
    def _load_ticker_mapping(self) -> Dict[str, str]:
        """KRX 코드 → yfinance 코드 매핑 로드."""
        mapping_file = "ticker_mapping.json"
        
        # 기본 매핑 (주요 종목들)
        default_mapping = {
            # KOSPI 대형주
            "005930": "005930.KS",  # 삼성전자
            "000660": "000660.KS",  # SK하이닉스
            "035420": "035420.KS",  # 네이버
            "005380": "005380.KS",  # 현대차
            "051910": "051910.KS",  # LG화학
            "006400": "006400.KS",  # 삼성SDI
            "035720": "035720.KS",  # 카카오
            "207940": "207940.KS",  # 삼성바이오로직스
            "068270": "068270.KS",  # 셀트리온
            "323410": "323410.KS",  # 카카오뱅크
            "003670": "003670.KS",  # 포스코홀딩스
            "028260": "028260.KS",  # 삼성물산
            "012330": "012330.KS",  # 현대모비스
            "096770": "096770.KS",  # SK이노베이션
            "017670": "017670.KS",  # SK텔레콤
            "030200": "030200.KS",  # KT
            "055550": "055550.KS",  # 신한지주
            "105560": "105560.KS",  # KB금융
            "086790": "086790.KS",  # 하나금융지주
            "316140": "316140.KS",  # 우리금융지주
            
            # KOSDAQ 주요종목  
            "293490": "293490.KQ",  # 카카오게임즈
            "086520": "086520.KQ",  # 에코프로
            "247540": "247540.KQ",  # 에코프로비엠
            "091990": "091990.KQ",  # 셀트리온헬스케어
            "058470": "058470.KQ",  # 리노공업
            "039030": "039030.KQ",  # 이오테크닉스
            "196170": "196170.KQ",  # 알테오젠
            "141080": "141080.KQ",  # 레고켐바이오
            "037370": "037370.KQ",  # 이노테라피
            "065350": "065350.KQ",  # 신성델타테크
        }
        
        try:
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    loaded_mapping = json.load(f)
                default_mapping.update(loaded_mapping)
                logger.info(f"📁 매핑 파일 로드: {len(loaded_mapping)}개 추가")
        except Exception as e:
            logger.warning(f"매핑 파일 로드 실패: {e}")
        
        logger.info(f"📊 총 {len(default_mapping)}개 종목 매핑 준비")
        return default_mapping
    
    async def run_full_collection(self, days: int = 365):
        """전체 데이터 수집 실행."""
        logger.info(f"🚀 전체 데이터 수집 시작 (최근 {days}일)")
        
        try:
            # 1. 기업 정보 수집
            await self._collect_company_info()
            
            # 2. 가격 데이터 수집
            await self._collect_price_data(days)
            
            # 3. 재무 데이터 수집
            await self._collect_financial_data()
            
            # 4. 데이터 품질 검사
            await self._quality_check()
            
            logger.info("✅ 전체 데이터 수집 완료")
            
        except Exception as e:
            logger.error(f"❌ 데이터 수집 실패: {e}")
            raise
        finally:
            self.session.close()
    
    async def _collect_company_info(self):
        """기업 기본 정보 수집."""
        logger.info("📊 기업 정보 수집 시작...")
        
        successful = 0
        failed = 0
        
        for kr_ticker, yf_ticker in self.ticker_mapping.items():
            try:
                async with self.semaphore:
                    company_data = await self._get_company_info(kr_ticker, yf_ticker)
                    
                    if company_data:
                        await self._save_company_info(company_data)
                        successful += 1
                        
                        if successful % 10 == 0:
                            logger.info(f"📈 진행률: {successful}/{len(self.ticker_mapping)}")
                    else:
                        failed += 1
                    
                    await asyncio.sleep(0.1)  # API 제한 고려
                    
            except Exception as e:
                logger.error(f"기업 정보 수집 실패 {kr_ticker}: {e}")
                failed += 1
        
        logger.info(f"📊 기업 정보 수집 완료: 성공 {successful}, 실패 {failed}")
    
    async def _get_company_info(self, kr_ticker: str, yf_ticker: str) -> Optional[Dict]:
        """개별 기업 정보 조회."""
        try:
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
            info = await loop.run_in_executor(None, lambda: ticker_obj.info)
            
            if not info:
                return None
            
            # 시장 구분 (KS=KOSPI, KQ=KOSDAQ)
            market = "KOSPI" if yf_ticker.endswith(".KS") else "KOSDAQ"
            
            return {
                "ticker": kr_ticker,
                "corp_name": info.get("longName") or info.get("shortName", ""),
                "market": market,
                "sector": info.get("sector", ""),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap"),
                "employees": info.get("fullTimeEmployees"),
                "website": info.get("website", ""),
                "description": info.get("longBusinessSummary", "")[:500] if info.get("longBusinessSummary") else ""
            }
            
        except Exception as e:
            logger.debug(f"기업 정보 조회 실패 {kr_ticker}: {e}")
            return None
    
    async def _save_company_info(self, company_data: Dict):
        """기업 정보 저장/업데이트."""
        try:
            stmt = insert(CompanyInfo).values(**company_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker"],
                set_={
                    "corp_name": stmt.excluded.corp_name,
                    "sector": stmt.excluded.sector,
                    "industry": stmt.excluded.industry,
                    "updated_at": datetime.now()
                }
            )
            
            self.session.execute(stmt)
            self.session.commit()
            
        except Exception as e:
            logger.error(f"기업 정보 저장 실패: {e}")
            self.session.rollback()
    
    async def _collect_price_data(self, days: int):
        """가격 데이터 수집."""
        logger.info(f"📈 가격 데이터 수집 시작 (최근 {days}일)...")
        
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
        
        successful = 0
        failed = 0
        
        # 배치 처리 (10개씩)
        ticker_items = list(self.ticker_mapping.items())
        batch_size = 10
        
        for i in range(0, len(ticker_items), batch_size):
            batch = ticker_items[i:i + batch_size]
            
            tasks = [
                self._collect_single_price_data(kr_ticker, yf_ticker, start_date, end_date)
                for kr_ticker, yf_ticker in batch
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    failed += 1
                elif result:
                    successful += 1
                else:
                    failed += 1
            
            logger.info(f"📊 가격 데이터 진행률: {successful + failed}/{len(self.ticker_mapping)}")
            await asyncio.sleep(1)  # 배치간 대기
        
        logger.info(f"📈 가격 데이터 수집 완료: 성공 {successful}, 실패 {failed}")
    
    async def _collect_single_price_data(
        self, 
        kr_ticker: str, 
        yf_ticker: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> bool:
        """개별 종목 가격 데이터 수집."""
        try:
            async with self.semaphore:
                loop = asyncio.get_event_loop()
                ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
                
                hist = await loop.run_in_executor(
                    None,
                    lambda: ticker_obj.history(
                        start=start_date.strftime('%Y-%m-%d'),
                        end=end_date.strftime('%Y-%m-%d'),
                        auto_adjust=True,
                        back_adjust=True
                    )
                )
                
                if hist.empty:
                    logger.debug(f"데이터 없음: {kr_ticker}")
                    return False
                
                # 데이터베이스 저장
                rows_saved = 0
                for date, row in hist.iterrows():
                    price_data = {
                        "ticker": kr_ticker,
                        "date": date.date(),
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": int(row['Volume']),
                        "source": "yfinance"
                    }
                    
                    stmt = insert(PriceMerged).values(**price_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["ticker", "date"],
                        set_=price_data
                    )
                    
                    self.session.execute(stmt)
                    rows_saved += 1
                
                self.session.commit()
                logger.debug(f"✅ {kr_ticker}: {rows_saved}일 데이터 저장")
                return True
                
        except Exception as e:
            logger.error(f"가격 데이터 수집 실패 {kr_ticker}: {e}")
            self.session.rollback()
            return False
    
    async def _collect_financial_data(self):
        """재무 데이터 수집."""
        logger.info("💰 재무 데이터 수집 시작...")
        
        successful = 0
        failed = 0
        
        for kr_ticker, yf_ticker in self.ticker_mapping.items():
            try:
                async with self.semaphore:
                    financial_data = await self._get_financial_data(kr_ticker, yf_ticker)
                    
                    if financial_data:
                        await self._save_financial_data(financial_data)
                        successful += 1
                    else:
                        failed += 1
                    
                    await asyncio.sleep(0.2)  # API 제한 고려
                    
            except Exception as e:
                logger.error(f"재무 데이터 수집 실패 {kr_ticker}: {e}")
                failed += 1
        
        logger.info(f"💰 재무 데이터 수집 완료: 성공 {successful}, 실패 {failed}")
    
    async def _get_financial_data(self, kr_ticker: str, yf_ticker: str) -> Optional[Dict]:
        """개별 기업 재무 데이터 조회."""
        try:
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
            
            # 재무제표 데이터
            financials = await loop.run_in_executor(None, lambda: ticker_obj.financials)
            
            if financials.empty or len(financials.columns) == 0:
                return None
            
            # 최신 연도 데이터 추출
            latest_year = financials.columns[0].year
            
            # 주요 재무 지표 추출
            revenue = self._safe_extract_value(financials, 'Total Revenue', 0)
            operating_income = self._safe_extract_value(financials, 'Operating Income', 0)
            net_income = self._safe_extract_value(financials, 'Net Income', 0)
            
            # 단위 조정 (원화 기준)
            if revenue:
                revenue = int(revenue)
            if operating_income:
                operating_income = int(operating_income)
            if net_income:
                net_income = int(net_income)
            
            return {
                "ticker": kr_ticker,
                "year": latest_year,
                "매출액": revenue,
                "영업이익": operating_income,
                "당기순이익": net_income
            }
            
        except Exception as e:
            logger.debug(f"재무 데이터 조회 실패 {kr_ticker}: {e}")
            return None
    
    def _safe_extract_value(self, financials: pd.DataFrame, key: str, col_index: int) -> Optional[float]:
        """안전한 재무 데이터 추출."""
        try:
            # 다양한 키 이름 시도
            possible_keys = [
                key,
                key.replace(' ', ''),
                key.lower(),
                key.upper()
            ]
            
            for k in possible_keys:
                if k in financials.index:
                    value = financials.loc[k].iloc[col_index]
                    if pd.notna(value):
                        return float(value)
            
            return None
            
        except Exception:
            return None
    
    async def _save_financial_data(self, financial_data: Dict):
        """재무 데이터 저장/업데이트."""
        try:
            stmt = insert(Financial).values(**financial_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "year"],
                set_={
                    "매출액": stmt.excluded.매출액,
                    "영업이익": stmt.excluded.영업이익,
                    "당기순이익": stmt.excluded.당기순이익,
                    "updated_at": datetime.now()
                }
            )
            
            self.session.execute(stmt)
            self.session.commit()
            
        except Exception as e:
            logger.error(f"재무 데이터 저장 실패: {e}")
            self.session.rollback()
    
    async def _quality_check(self):
        """데이터 품질 검사."""
        logger.info("🔍 데이터 품질 검사 시작...")
        
        try:
            # 가격 데이터 품질 검사
            price_stats = self.session.execute(text("""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT ticker) as unique_tickers,
                    COUNT(CASE WHEN close IS NULL THEN 1 END) as null_prices,
                    MIN(date) as min_date,
                    MAX(date) as max_date
                FROM prices_merged
            """)).fetchone()
            
            # 기업 정보 품질 검사
            company_stats = self.session.execute(text("""
                SELECT 
                    COUNT(*) as total_companies,
                    COUNT(CASE WHEN corp_name IS NULL OR corp_name = '' THEN 1 END) as missing_names,
                    COUNT(CASE WHEN sector IS NULL OR sector = '' THEN 1 END) as missing_sectors
                FROM company_info
            """)).fetchone()
            
            # 재무 데이터 품질 검사
            financial_stats = self.session.execute(text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ticker) as companies_with_financials,
                    COUNT(CASE WHEN 매출액 IS NULL THEN 1 END) as missing_revenue
                FROM financials
            """)).fetchone()
            
            # 품질 리포트 출력
            logger.info("📊 데이터 품질 리포트:")
            if price_stats and price_stats[0] > 0:
                logger.info(f"  가격 데이터: {price_stats[0]:,}행, {price_stats[1]}개 종목")
                logger.info(f"  날짜 범위: {price_stats[3]} ~ {price_stats[4]}")
                logger.info(f"  결측 가격: {price_stats[2]:,}개 ({price_stats[2]/price_stats[0]*100:.1f}%)")
            else:
                logger.warning("  가격 데이터: 데이터 없음")
            
            if company_stats and company_stats[0] > 0:
                logger.info(f"  기업 정보: {company_stats[0]}개 회사")
                logger.info(f"  이름 결측: {company_stats[1]}개, 섹터 결측: {company_stats[2]}개")
            else:
                logger.warning("  기업 정보: 데이터 없음")
            
            if financial_stats and financial_stats[0] > 0:
                logger.info(f"  재무 데이터: {financial_stats[0]}개 레코드, {financial_stats[1]}개 기업")
                logger.info(f"  매출 결측: {financial_stats[2]}개")
            else:
                logger.warning("  재무 데이터: 데이터 없음")
            
            # 품질 점수 계산
            if price_stats and price_stats[0] > 0:
                price_quality = max(0, 100 - (price_stats[2] / price_stats[0] * 100))
            else:
                price_quality = 0
            
            if company_stats and company_stats[0] > 0:
                company_quality = max(0, 100 - (company_stats[1] / company_stats[0] * 100))
            else:
                company_quality = 0
            
            if financial_stats and financial_stats[0] > 0:
                financial_quality = max(0, 100 - (financial_stats[2] / financial_stats[0] * 100))
            else:
                financial_quality = 0
            
            overall_quality = (price_quality + company_quality + financial_quality) / 3
            
            logger.info(f"📈 전체 데이터 품질 점수: {overall_quality:.1f}/100")
            
            if overall_quality < 70:
                logger.warning("⚠️ 데이터 품질이 낮습니다. 추가 수집이 필요할 수 있습니다.")
            else:
                logger.info("✅ 데이터 품질이 양호합니다.")
                
        except Exception as e:
            logger.error(f"품질 검사 실패: {e}")
    
    def close(self):
        """리소스 정리."""
        if self.session:
            self.session.close()


# 스케줄링 및 모니터링
class ETLScheduler:
    """ETL 스케줄링 및 모니터링."""
    
    def __init__(self):
        self.etl = EnhancedYFinanceETL()
    
    async def run_daily_update(self):
        """일일 업데이트 (최근 5일 데이터)."""
        logger.info("🌅 일일 데이터 업데이트 시작...")
        
        try:
            # 최근 5일 가격 데이터만 업데이트
            await self.etl._collect_price_data(days=5)
            
            # 기업 정보는 주간 업데이트
            if datetime.now().weekday() == 0:  # 월요일
                await self.etl._collect_company_info()
            
            # 재무 데이터는 월간 업데이트
            if datetime.now().day == 1:  # 매월 1일
                await self.etl._collect_financial_data()
            
            logger.info("✅ 일일 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 일일 업데이트 실패: {e}")
            raise
        finally:
            self.etl.close()
    
    async def run_weekly_full_update(self):
        """주간 전체 업데이트."""
        logger.info("📅 주간 전체 업데이트 시작...")
        
        try:
            await self.etl.run_full_collection(days=30)  # 최근 1개월
            logger.info("✅ 주간 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 주간 업데이트 실패: {e}")
            raise
        finally:
            self.etl.close()
    
    async def run_monthly_full_update(self):
        """월간 전체 업데이트."""
        logger.info("📆 월간 전체 업데이트 시작...")
        
        try:
            await self.etl.run_full_collection(days=365)  # 최근 1년
            logger.info("✅ 월간 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 월간 업데이트 실패: {e}")
            raise
        finally:
            self.etl.close()


# CLI 인터페이스
async def main():
    """메인 실행 함수."""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python load_yf_enhanced.py [command]")
        print("Commands:")
        print("  full        - 전체 데이터 수집 (1년)")
        print("  quick       - 빠른 수집 (30일)")
        print("  daily       - 일일 업데이트 (5일)")
        print("  company     - 기업 정보만 수집")
        print("  prices      - 가격 데이터만 수집") 
        print("  financials  - 재무 데이터만 수집")
        print("  quality     - 품질 검사만 실행")
        return
    
    command = sys.argv[1].lower()
    etl = EnhancedYFinanceETL()
    
    try:
        if command == "full":
            await etl.run_full_collection(days=365)
        elif command == "quick":
            await etl.run_full_collection(days=30)
        elif command == "daily":
            await etl._collect_price_data(days=5)
        elif command == "company":
            await etl._collect_company_info()
        elif command == "prices":
            await etl._collect_price_data(days=30)
        elif command == "financials":
            await etl._collect_financial_data()
        elif command == "quality":
            await etl._quality_check()
        else:
            print(f"알 수 없는 명령어: {command}")
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"실행 실패: {e}")
        raise
    finally:
        etl.close()


if __name__ == "__main__":
    asyncio.run(main())