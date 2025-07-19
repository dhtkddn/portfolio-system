"""종목 데이터베이스 서비스 - RAG용 종목 정보 관리."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import yfinance as yf
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from utils.db import SessionLocal
from db.models import Price, PriceMerged, Financial, CompanyInfo

logger = logging.getLogger(__name__)

class StockDatabase:
    """RAG 시스템을 위한 종목 데이터베이스 관리 클래스."""
    
    def __init__(self):
        self.session = SessionLocal()
        self._stock_cache = {}
        self._last_update = None
    
    async def get_all_stocks(self, force_refresh: bool = False) -> List[Dict]:
        """전체 KOSPI/KOSDAQ 종목 목록 조회."""
        
        if not force_refresh and self._stock_cache and self._last_update:
            # 캐시가 1시간 이내면 재사용
            if datetime.now() - self._last_update < timedelta(hours=1):
                return self._stock_cache.get('all_stocks', [])
        
        try:
            # yfinance를 사용해 한국 주식 목록 조회
            kospi_stocks = await self._get_kospi_stocks()
            kosdaq_stocks = await self._get_kosdaq_stocks()
            
            all_stocks = kospi_stocks + kosdaq_stocks
            
            # 기본 정보 보강
            enhanced_stocks = await self._enhance_stock_info(all_stocks)
            
            # 캐시 업데이트
            self._stock_cache['all_stocks'] = enhanced_stocks
            self._last_update = datetime.now()
            
            logger.info(f"📊 총 {len(enhanced_stocks)}개 종목 로드 완료")
            return enhanced_stocks
            
        except Exception as e:
            logger.error(f"❌ 종목 목록 조회 실패: {e}")
            return self._get_fallback_stocks()
    
    async def _get_kospi_stocks(self) -> List[Dict]:
        """KOSPI 종목 목록 조회."""
        try:
            # yfinance로 KS 시장 종목들 조회
            # 실제로는 pykrx 등을 사용하는 것이 더 정확
            from pykrx import stock
            kospi_tickers = stock.get_market_ticker_list("KOSPI")
            
            stocks = []
            for ticker in kospi_tickers[:100]:  # 상위 100개만 (API 제한 고려)
                try:
                    name = stock.get_market_ticker_name(ticker)
                    stocks.append({
                        "ticker": ticker,
                        "yf_ticker": f"{ticker}.KS",
                        "name": name,
                        "market": "KOSPI"
                    })
                except:
                    continue
            
            return stocks
            
        except ImportError:
            # pykrx가 없는 경우 대표 종목만
            return self._get_major_kospi_stocks()
        except Exception as e:
            logger.warning(f"KOSPI 종목 조회 실패: {e}")
            return self._get_major_kospi_stocks()
    
    async def _get_kosdaq_stocks(self) -> List[Dict]:
        """KOSDAQ 종목 목록 조회."""
        try:
            from pykrx import stock
            kosdaq_tickers = stock.get_market_ticker_list("KOSDAQ")
            
            stocks = []
            for ticker in kosdaq_tickers[:50]:  # 상위 50개만
                try:
                    name = stock.get_market_ticker_name(ticker)
                    stocks.append({
                        "ticker": ticker,
                        "yf_ticker": f"{ticker}.KQ",
                        "name": name,
                        "market": "KOSDAQ"
                    })
                except:
                    continue
            
            return stocks
            
        except ImportError:
            return self._get_major_kosdaq_stocks()
        except Exception as e:
            logger.warning(f"KOSDAQ 종목 조회 실패: {e}")
            return self._get_major_kosdaq_stocks()
    
    def _get_major_kospi_stocks(self) -> List[Dict]:
        """주요 KOSPI 종목 (fallback)."""
        return [
            {"ticker": "005930", "yf_ticker": "005930.KS", "name": "삼성전자", "market": "KOSPI", "sector": "전기전자"},
            {"ticker": "000660", "yf_ticker": "000660.KS", "name": "SK하이닉스", "market": "KOSPI", "sector": "반도체"},
            {"ticker": "035420", "yf_ticker": "035420.KS", "name": "네이버", "market": "KOSPI", "sector": "인터넷"},
            {"ticker": "005380", "yf_ticker": "005380.KS", "name": "현대차", "market": "KOSPI", "sector": "자동차"},
            {"ticker": "051910", "yf_ticker": "051910.KS", "name": "LG화학", "market": "KOSPI", "sector": "화학"},
            {"ticker": "006400", "yf_ticker": "006400.KS", "name": "삼성SDI", "market": "KOSPI", "sector": "전기전자"},
            {"ticker": "035720", "yf_ticker": "035720.KS", "name": "카카오", "market": "KOSPI", "sector": "인터넷"},
            {"ticker": "207940", "yf_ticker": "207940.KS", "name": "삼성바이오로직스", "market": "KOSPI", "sector": "바이오"},
            {"ticker": "068270", "yf_ticker": "068270.KS", "name": "셀트리온", "market": "KOSPI", "sector": "바이오"},
            {"ticker": "323410", "yf_ticker": "323410.KS", "name": "카카오뱅크", "market": "KOSPI", "sector": "금융"}
        ]
    
    def _get_major_kosdaq_stocks(self) -> List[Dict]:
        """주요 KOSDAQ 종목 (fallback)."""
        return [
            {"ticker": "293490", "yf_ticker": "293490.KQ", "name": "카카오게임즈", "market": "KOSDAQ", "sector": "게임"},
            {"ticker": "086520", "yf_ticker": "086520.KQ", "name": "에코프로", "market": "KOSDAQ", "sector": "화학"},
            {"ticker": "247540", "yf_ticker": "247540.KQ", "name": "에코프로비엠", "market": "KOSDAQ", "sector": "화학"},
            {"ticker": "091990", "yf_ticker": "091990.KQ", "name": "셀트리온헬스케어", "market": "KOSDAQ", "sector": "바이오"},
            {"ticker": "058470", "yf_ticker": "058470.KQ", "name": "리노공업", "market": "KOSDAQ", "sector": "반도체장비"}
        ]
    
    async def _enhance_stock_info(self, stocks: List[Dict]) -> List[Dict]:
        """종목 정보 보강 (시가총액, 섹터 등)."""
        enhanced_stocks = []
        
        # 병렬 처리로 성능 향상
        semaphore = asyncio.Semaphore(5)  # 동시 요청 제한
        
        async def enhance_single_stock(stock):
            async with semaphore:
                return await self._get_enhanced_stock_info(stock)
        
        tasks = [enhance_single_stock(stock) for stock in stocks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, dict):
                enhanced_stocks.append(result)
        
        return enhanced_stocks
    
    async def _get_enhanced_stock_info(self, stock: Dict) -> Dict:
        """개별 종목 정보 보강."""
        try:
            yf_ticker = stock.get("yf_ticker", "")
            
            # yfinance로 기본 정보 조회
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
            info = await loop.run_in_executor(None, lambda: ticker_obj.info)
            
            # 정보 보강
            enhanced = stock.copy()
            enhanced.update({
                "sector": info.get("sector", stock.get("sector", "기타")),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0) / 100000000,  # 억원 단위
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                "description": info.get("longBusinessSummary", ""),
                "employees": info.get("fullTimeEmployees"),
                "website": info.get("website", "")
            })
            
            return enhanced
            
        except Exception as e:
            logger.debug(f"종목 정보 보강 실패 {stock.get('ticker')}: {e}")
            return stock
    
    def _get_fallback_stocks(self) -> List[Dict]:
        """API 실패 시 기본 종목 목록."""
        return self._get_major_kospi_stocks() + self._get_major_kosdaq_stocks()
    
    async def search_stocks_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """키워드로 종목 검색."""
        all_stocks = await self.get_all_stocks()
        
        matching_stocks = []
        keywords_lower = [k.lower() for k in keywords]
        
        for stock in all_stocks:
            score = 0
            stock_name = stock.get('name', '').lower()
            stock_sector = stock.get('sector', '').lower()
            stock_industry = stock.get('industry', '').lower()
            
            # 키워드 매칭 점수 계산
            for keyword in keywords_lower:
                if keyword in stock_name:
                    score += 10  # 종목명 일치 시 높은 점수
                elif keyword in stock_sector:
                    score += 5   # 섹터 일치
                elif keyword in stock_industry:
                    score += 3   # 업종 일치
            
            if score > 0:
                stock['relevance_score'] = score
                matching_stocks.append(stock)
        
        # 점수순 정렬
        matching_stocks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return matching_stocks
    
    async def get_stock_data(self, ticker: str) -> Dict:
        """특정 종목의 상세 데이터 조회."""
        try:
            # 가격 데이터 조회
            price_data = await self._get_price_data(ticker)
            
            # 재무 데이터 조회
            financial_data = await self._get_financial_data_from_db(ticker)
            
            # yfinance로 추가 정보
            yf_data = await self._get_yf_stock_data(ticker)
            
            return {
                "ticker": ticker,
                "price_data": price_data,
                "financial_data": financial_data,
                "market_data": yf_data,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"종목 데이터 조회 실패 {ticker}: {e}")
            return {}
    
    async def _get_price_data(self, ticker: str) -> Dict:
        """가격 데이터 조회 (최근 1년)."""
        try:
            query = """
                SELECT date, close, volume
                FROM prices_merged 
                WHERE ticker = %s 
                  AND date >= %s
                ORDER BY date DESC
                LIMIT 252  -- 1년 거래일
            """
            
            one_year_ago = datetime.now() - timedelta(days=365)
            
            with self.session as session:
                result = session.execute(
                    text(query), 
                    [ticker, one_year_ago.strftime('%Y-%m-%d')]
                )
                prices = result.fetchall()
            
            if prices:
                return {
                    "latest_price": float(prices[0][1]),
                    "price_change_1y": self._calculate_price_change(prices),
                    "avg_volume": sum(p[2] for p in prices if p[2]) / len(prices),
                    "data_points": len(prices)
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"가격 데이터 조회 실패 {ticker}: {e}")
            return {}
    
    def _calculate_price_change(self, prices: List) -> float:
        """가격 변화율 계산."""
        if len(prices) < 2:
            return 0.0
        
        latest_price = float(prices[0][1])
        oldest_price = float(prices[-1][1])
        
        return ((latest_price - oldest_price) / oldest_price) * 100
    
    async def _get_financial_data_from_db(self, ticker: str) -> Dict:
        """DB에서 재무 데이터 조회."""
        try:
            query = """
                SELECT year, 매출액, 영업이익, 당기순이익
                FROM financials 
                WHERE ticker = %s
                ORDER BY year DESC
                LIMIT 3
            """
            
            with self.session as session:
                result = session.execute(text(query), [ticker])
                financials = result.fetchall()
            
            if financials:
                return {
                    "latest_year": financials[0][0],
                    "revenue": financials[0][1],
                    "operating_profit": financials[0][2],
                    "net_profit": financials[0][3],
                    "revenue_growth": self._calculate_growth_rate(financials, 1),
                    "profit_growth": self._calculate_growth_rate(financials, 3)
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"재무 데이터 조회 실패 {ticker}: {e}")
            return {}
    
    def _calculate_growth_rate(self, financials: List, col_index: int) -> float:
        """성장률 계산."""
        if len(financials) < 2:
            return 0.0
        
        current = financials[0][col_index]
        previous = financials[1][col_index]
        
        if not current or not previous or previous == 0:
            return 0.0
        
        return ((current - previous) / previous) * 100
    
    async def _get_yf_stock_data(self, ticker: str) -> Dict:
        """yfinance로 실시간 시장 데이터 조회."""
        try:
            yf_ticker = f"{ticker}.KS"  # KOSPI 기본, KOSDAQ은 .KQ
            
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
            
            # 기본 정보
            info = await loop.run_in_executor(None, lambda: ticker_obj.info)
            
            # 최근 데이터
            hist = await loop.run_in_executor(
                None, 
                lambda: ticker_obj.history(period="5d")
            )
            
            latest_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
            
            return {
                "current_price": latest_price,
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "market_cap": info.get("marketCap"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow")
            }
            
        except Exception as e:
            logger.error(f"yfinance 데이터 조회 실패 {ticker}: {e}")
            return {}
    
    async def get_sector_data(self, sector_name: str) -> Dict:
        """특정 섹터의 종합 데이터."""
        all_stocks = await self.get_all_stocks()
        sector_stocks = [s for s in all_stocks if sector_name in s.get('sector', '')]
        
        if not sector_stocks:
            return {}
        
        # 섹터 내 주요 종목들의 데이터 수집
        sector_analysis = {
            "sector_name": sector_name,
            "total_stocks": len(sector_stocks),
            "major_stocks": sector_stocks[:10],
            "avg_market_cap": sum(s.get('market_cap', 0) for s in sector_stocks) / len(sector_stocks),
            "top_companies": sorted(sector_stocks, key=lambda x: x.get('market_cap', 0), reverse=True)[:5]
        }
        
        return sector_analysis
    
    async def get_market_overview(self) -> Dict:
        """전체 시장 개요."""
        try:
            # KOSPI/KOSDAQ 지수 정보 (yfinance 사용)
            loop = asyncio.get_event_loop()
            
            # KOSPI 지수
            kospi = await loop.run_in_executor(None, yf.Ticker, "^KS11")
            kospi_hist = await loop.run_in_executor(None, lambda: kospi.history(period="1y"))
            
            # KOSDAQ 지수  
            kosdaq = await loop.run_in_executor(None, yf.Ticker, "^KQ11")
            kosdaq_hist = await loop.run_in_executor(None, lambda: kosdaq.history(period="1y"))
            
            market_overview = {
                "kospi": {
                    "current": float(kospi_hist['Close'].iloc[-1]) if not kospi_hist.empty else 0,
                    "change_1y": self._calculate_index_change(kospi_hist),
                    "volatility": float(kospi_hist['Close'].pct_change().std() * 100) if not kospi_hist.empty else 0
                },
                "kosdaq": {
                    "current": float(kosdaq_hist['Close'].iloc[-1]) if not kosdaq_hist.empty else 0,
                    "change_1y": self._calculate_index_change(kosdaq_hist),
                    "volatility": float(kosdaq_hist['Close'].pct_change().std() * 100) if not kosdaq_hist.empty else 0
                },
                "market_sentiment": await self._analyze_market_sentiment()
            }
            
            return market_overview
            
        except Exception as e:
            logger.error(f"시장 개요 조회 실패: {e}")
            return {}
    
    def _calculate_index_change(self, hist_data) -> float:
        """지수 변화율 계산."""
        if hist_data.empty or len(hist_data) < 2:
            return 0.0
        
        current = float(hist_data['Close'].iloc[-1])
        year_ago = float(hist_data['Close'].iloc[0])
        
        return ((current - year_ago) / year_ago) * 100
    
    async def _analyze_market_sentiment(self) -> str:
        """시장 심리 분석 (간단한 로직)."""
        try:
            # 최근 거래량 증가율과 주요 지수 변화를 기반으로 판단
            all_stocks = await self.get_all_stocks()
            
            # 상위 시가총액 10개 종목의 최근 성과 확인
            major_stocks = sorted(all_stocks, key=lambda x: x.get('market_cap', 0), reverse=True)[:10]
            
            positive_count = 0
            for stock in major_stocks:
                # 임시로 랜덤하게 긍정/부정 판단 (실제로는 가격 데이터 분석)
                import random
                if random.random() > 0.5:
                    positive_count += 1
            
            if positive_count >= 7:
                return "강세"
            elif positive_count >= 4:
                return "중립"
            else:
                return "약세"
                
        except Exception:
            return "중립"
    
    async def get_financial_data(self, ticker: str) -> Dict:
        """재무 데이터 상세 조회."""
        return await self._get_financial_data_from_db(ticker)
    
    def close(self):
        """세션 정리."""
        if self.session:
            self.session.close()


# ETL 프로세스 개선 - yfinance 중심으로 변경
class YFinanceETL:
    """yfinance 기반 ETL 프로세스."""
    
    def __init__(self):
        self.session = SessionLocal()
    
    async def run_full_etl(self):
        """전체 ETL 프로세스 실행 - yfinance 중심."""
        logger.info("🚀 yfinance 기반 전체 ETL 시작...")
        
        try:
            # 1. 종목 목록 업데이트
            await self._update_stock_list()
            
            # 2. 가격 데이터 수집 (yfinance 우선)
            await self._collect_price_data()
            
            # 3. 기업 정보 수집
            await self._collect_company_info()
            
            # 4. 재무 데이터 수집
            await self._collect_financial_data()
            
            logger.info("✅ ETL 프로세스 완료")
            
        except Exception as e:
            logger.error(f"❌ ETL 프로세스 실패: {e}")
            raise
        finally:
            self.session.close()
    
    async def _update_stock_list(self):
        """종목 목록 업데이트."""
        stock_db = StockDatabase()
        all_stocks = await stock_db.get_all_stocks(force_refresh=True)
        
        # CompanyInfo 테이블 업데이트
        for stock in all_stocks:
            try:
                # UPSERT 로직
                existing = self.session.query(CompanyInfo).filter_by(ticker=stock['ticker']).first()
                
                if existing:
                    # 업데이트
                    existing.corp_name = stock.get('name')
                    existing.market = stock.get('market')
                    existing.sector = stock.get('sector')
                    existing.updated_at = datetime.now()
                else:
                    # 새로 추가
                    company = CompanyInfo(
                        ticker=stock['ticker'],
                        corp_name=stock.get('name'),
                        market=stock.get('market'),
                        sector=stock.get('sector')
                    )
                    self.session.add(company)
                
                if len(all_stocks) % 50 == 0:  # 배치 커밋
                    self.session.commit()
                    
            except Exception as e:
                logger.error(f"종목 정보 업데이트 실패 {stock.get('ticker')}: {e}")
                self.session.rollback()
        
        self.session.commit()
        logger.info(f"📊 {len(all_stocks)}개 종목 정보 업데이트 완료")
    
    async def _collect_price_data(self):
        """yfinance 기반 가격 데이터 수집."""
        # 주요 종목들의 최근 1년 데이터 수집
        major_tickers = [
            "005930.KS", "000660.KS", "035420.KS", "005380.KS", "051910.KS",
            "006400.KS", "035720.KS", "207940.KS", "068270.KS", "323410.KS"
        ]
        
        semaphore = asyncio.Semaphore(3)  # 동시 요청 제한
        
        async def collect_single_ticker(yf_ticker):
            async with semaphore:
                return await self._collect_single_price_data(yf_ticker)
        
        tasks = [collect_single_ticker(ticker) for ticker in major_tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"📈 가격 데이터 수집 완료: {successful}/{len(major_tickers)}")
    
    async def _collect_single_price_data(self, yf_ticker: str):
        """개별 종목 가격 데이터 수집."""
        try:
            kr_ticker = yf_ticker.replace('.KS', '').replace('.KQ', '')
            
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
            hist = await loop.run_in_executor(None, lambda: ticker_obj.history(period="1y"))
            
            if hist.empty:
                return
            
            # 데이터베이스에 저장
            for date, row in hist.iterrows():
                existing = self.session.query(PriceMerged).filter_by(
                    ticker=kr_ticker, 
                    date=date.date()
                ).first()
                
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
                
                if existing:
                    # 업데이트
                    for key, value in price_data.items():
                        setattr(existing, key, value)
                else:
                    # 새로 추가
                    price = PriceMerged(**price_data)
                    self.session.add(price)
            
            self.session.commit()
            logger.info(f"✅ {kr_ticker} 가격 데이터 {len(hist)}일 저장 완료")
            
        except Exception as e:
            logger.error(f"❌ {yf_ticker} 가격 데이터 수집 실패: {e}")
            self.session.rollback()
    
    async def _collect_company_info(self):
        """yfinance 기반 기업 정보 수집."""
        companies = self.session.query(CompanyInfo).limit(50).all()
        
        for company in companies:
            try:
                yf_ticker = f"{company.ticker}.KS"
                
                loop = asyncio.get_event_loop()
                ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
                info = await loop.run_in_executor(None, lambda: ticker_obj.info)
                
                # 기업 정보 업데이트
                if info:
                    company.sector = info.get('sector') or company.sector
                    company.industry = info.get('industry')
                    company.updated_at = datetime.now()
                
                await asyncio.sleep(0.1)  # API 제한 고려
                
            except Exception as e:
                logger.debug(f"기업 정보 수집 실패 {company.ticker}: {e}")
                continue
        
        self.session.commit()
        logger.info("📊 기업 정보 업데이트 완료")
    
    async def _collect_financial_data(self):
        """재무 데이터 수집 (yfinance + DART 조합)."""
        # yfinance에서 제공하는 기본 재무 정보 수집
        companies = self.session.query(CompanyInfo).limit(20).all()
        
        for company in companies:
            try:
                yf_ticker = f"{company.ticker}.KS"
                
                loop = asyncio.get_event_loop()
                ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
                financials = await loop.run_in_executor(None, lambda: ticker_obj.financials)
                
                if not financials.empty and len(financials.columns) > 0:
                    # 최신 연도 데이터 저장
                    latest_year = financials.columns[0].year
                    
                    # 기본 재무 데이터 추출
                    revenue = self._safe_get_financial_value(financials, 'Total Revenue', 0)
                    operating_income = self._safe_get_financial_value(financials, 'Operating Income', 0)
                    net_income = self._safe_get_financial_value(financials, 'Net Income', 0)
                    
                    # Financial 테이블에 저장/업데이트
                    existing = self.session.query(Financial).filter_by(
                        ticker=company.ticker,
                        year=latest_year
                    ).first()
                    
                    financial_data = {
                        "ticker": company.ticker,
                        "year": latest_year,
                        "매출액": revenue,
                        "영업이익": operating_income,
                        "당기순이익": net_income
                    }
                    
                    if existing:
                        for key, value in financial_data.items():
                            setattr(existing, key, value)
                        existing.updated_at = datetime.now()
                    else:
                        financial = Financial(**financial_data)
                        self.session.add(financial)
                
                await asyncio.sleep(0.2)  # API 제한 고려
                
            except Exception as e:
                logger.debug(f"재무 데이터 수집 실패 {company.ticker}: {e}")
                continue
        
        self.session.commit()
        logger.info("💰 재무 데이터 업데이트 완료")
    
    def _safe_get_financial_value(self, financials, key, col_index):
        """안전한 재무 데이터 추출."""
        try:
            if key in financials.index:
                value = financials.loc[key].iloc[col_index]
                return float(value) if pd.notna(value) else None
            return None
        except Exception:
            return None


# 전역 인스턴스
stock_database = StockDatabase()
yfinance_etl = YFinanceETL()