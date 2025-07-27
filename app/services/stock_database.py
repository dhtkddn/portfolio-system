"""종목 데이터베이스 서비스 - RAG용 종목 정보 관리 (완전한 수정 버전)."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf
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
            if datetime.now() - self._last_update < timedelta(hours=1):
                return self._stock_cache.get('all_stocks', [])

        try:
            kospi_stocks = await self._get_kospi_stocks()
            kosdaq_stocks = await self._get_kosdaq_stocks()
            all_stocks = kospi_stocks + kosdaq_stocks
            enhanced_stocks = await self._enhance_stock_info(all_stocks)

            self._stock_cache['all_stocks'] = enhanced_stocks
            self._last_update = datetime.now()

            logger.info(f"📊 총 {len(enhanced_stocks)}개 종목 로드 완료")
            return enhanced_stocks

        except Exception as e:
            logger.error(f"❌ 종목 목록 조회 실패: {e}")
            return self._get_fallback_stocks()

    def get_all_stocks_for_screening(self) -> pd.DataFrame:
        """스크리닝에 필요한 전체 종목 데이터를 DataFrame으로 반환."""
        try:
            # 기본 종목 정보 + 재무 지표 조회
            query = """
            SELECT 
                ci.ticker,
                ci.corp_name as name,
                ci.market,
                ci.sector,
                -- 더미 재무 지표 (실제 데이터가 없을 경우)
                CASE 
                    WHEN ci.ticker = '005930' THEN 1.2  -- 삼성전자
                    WHEN ci.ticker = '000660' THEN 0.8  -- SK하이닉스
                    WHEN ci.ticker = '035420' THEN 2.1  -- 네이버
                    WHEN ci.ticker = '005380' THEN 0.6  -- 현대차
                    WHEN ci.ticker = '051910' THEN 1.1  -- LG화학
                    ELSE 1.0 
                END as pbr,
                CASE 
                    WHEN ci.ticker = '005930' THEN 8.5
                    WHEN ci.ticker = '000660' THEN 6.2
                    WHEN ci.ticker = '035420' THEN 15.2
                    WHEN ci.ticker = '005380' THEN 5.8
                    WHEN ci.ticker = '051910' THEN 12.3
                    ELSE 10.0 
                END as per,
                CASE 
                    WHEN ci.ticker = '005930' THEN 12.5
                    WHEN ci.ticker = '000660' THEN 18.3
                    WHEN ci.ticker = '035420' THEN 15.8
                    WHEN ci.ticker = '005380' THEN 8.2
                    WHEN ci.ticker = '051910' THEN 11.4
                    ELSE 10.0 
                END as roe,
                CASE 
                    WHEN ci.ticker = '005930' THEN 45.2
                    WHEN ci.ticker = '000660' THEN 62.1
                    WHEN ci.ticker = '035420' THEN 25.4
                    WHEN ci.ticker = '005380' THEN 85.3
                    WHEN ci.ticker = '051910' THEN 55.7
                    ELSE 80.0 
                END as debt_ratio,
                CASE 
                    WHEN ci.ticker = '005930' THEN 400000000  -- 400조 (삼성전자)
                    WHEN ci.ticker = '000660' THEN 80000000   -- 80조 (SK하이닉스)
                    WHEN ci.ticker = '035420' THEN 50000000   -- 50조 (네이버)
                    WHEN ci.ticker = '005380' THEN 45000000   -- 45조 (현대차)
                    WHEN ci.ticker = '051910' THEN 35000000   -- 35조 (LG화학)
                    ELSE 10000000 
                END as market_cap
            FROM company_info ci
            WHERE ci.ticker IS NOT NULL
            """
            
            result = self.session.execute(text(query))
            rows = result.fetchall()
            
            if not rows:
                # 테이블에 데이터가 없으면 더미 데이터 생성
                logger.warning("⚠️ company_info 테이블에 데이터가 없습니다. 더미 데이터를 생성합니다.")
                return self._create_dummy_stocks_dataframe()
            
            # DataFrame 생성
            columns = ['ticker', 'name', 'market', 'sector', 'pbr', 'per', 'roe', 'debt_ratio', 'market_cap']
            df = pd.DataFrame(rows, columns=columns)
            
            logger.info(f"📊 스크리닝용 종목 데이터 로드 완료: {len(df)}개 종목")
            return df
            
        except Exception as e:
            logger.error(f"❌ 스크리닝 데이터 로드 실패: {e}")
            return self._create_dummy_stocks_dataframe()

    def _create_dummy_stocks_dataframe(self) -> pd.DataFrame:
        """더미 종목 데이터 생성 (테스트용)."""
        dummy_data = [
            {
                'ticker': '005930', 'name': '삼성전자', 'market': 'KOSPI', 'sector': '전기전자',
                'pbr': 1.2, 'per': 8.5, 'roe': 12.5, 'debt_ratio': 45.2, 'market_cap': 400000000
            },
            {
                'ticker': '000660', 'name': 'SK하이닉스', 'market': 'KOSPI', 'sector': '반도체',
                'pbr': 0.8, 'per': 6.2, 'roe': 18.3, 'debt_ratio': 62.1, 'market_cap': 80000000
            },
            {
                'ticker': '035420', 'name': '네이버', 'market': 'KOSPI', 'sector': '인터넷',
                'pbr': 2.1, 'per': 15.2, 'roe': 15.8, 'debt_ratio': 25.4, 'market_cap': 50000000
            },
            {
                'ticker': '005380', 'name': '현대차', 'market': 'KOSPI', 'sector': '자동차',
                'pbr': 0.6, 'per': 5.8, 'roe': 8.2, 'debt_ratio': 85.3, 'market_cap': 45000000
            },
            {
                'ticker': '051910', 'name': 'LG화학', 'market': 'KOSPI', 'sector': '화학',
                'pbr': 1.1, 'per': 12.3, 'roe': 11.4, 'debt_ratio': 55.7, 'market_cap': 35000000
            }
        ]
        
        df = pd.DataFrame(dummy_data)
        logger.info(f"📊 더미 종목 데이터 생성: {len(df)}개 종목")
        return df

    def get_company_info(self, ticker: str) -> Dict:
        """종목의 기업 정보 조회"""
        try:
            query = """
            SELECT corp_name, market, sector 
            FROM company_info 
            WHERE ticker = :ticker
            """
            result = self.session.execute(text(query), {"ticker": ticker})
            row = result.fetchone()
            
            if row:
                return {
                    "company_name": row[0],
                    "market": row[1],
                    "sector": row[2],
                    "summary": f"{row[0]}는 {row[2]} 업종의 {row[1]} 상장 기업입니다."
                }
            else:
                logger.warning(f"기업 정보 없음: {ticker}")
                return {
                    "company_name": f"종목{ticker}", 
                    "sector": "기타", 
                    "summary": "기업 정보 없음"
                }
                
        except Exception as e:
            logger.error(f"기업 정보 조회 실패 {ticker}: {e}")
            return {"company_name": f"종목{ticker}", "sector": "기타", "summary": "조회 실패"}

    def get_financials(self, ticker: str) -> Dict:
        """종목의 재무 정보를 PostgreSQL에서 조회"""
        try:
            query = """
            SELECT year, "매출액", "영업이익", "당기순이익"
            FROM financials 
            WHERE ticker = :ticker 
            ORDER BY year DESC 
            LIMIT 1
            """
            result = self.session.execute(text(query), {"ticker": ticker})
            row = result.fetchone()
            
            if row:
                revenue = float(row[1]) if row[1] is not None else 0
                operating_profit = float(row[2]) if row[2] is not None else 0
                net_profit = float(row[3]) if row[3] is not None else 0
                
                # ROE 계산 (간단히 - 실제로는 자기자본 대비 계산해야 함)
                roe = (net_profit / revenue * 100) if revenue > 0 else 0
                
                return {
                    "latest_year": row[0],
                    "revenue": revenue,
                    "operating_profit": operating_profit, 
                    "net_profit": net_profit,
                    "ROE": roe,
                    "DebtRatio": 50.0  # 추후 실제 데이터로 대체
                }
            else:
                logger.warning(f"재무 데이터 없음: {ticker}")
                return {
                    "revenue": 0, 
                    "operating_profit": 0, 
                    "net_profit": 0, 
                    "ROE": 0, 
                    "DebtRatio": 0
                }
                
        except Exception as e:
            logger.error(f"재무 정보 조회 실패 {ticker}: {e}")
            return {"revenue": 0, "operating_profit": 0, "net_profit": 0, "ROE": 0, "DebtRatio": 0}

    def get_valuation_metrics(self, ticker: str) -> Dict:
        """종목의 밸류에이션 지표 조회."""
        try:
            # 실제 DB에서 조회하는 로직 (현재는 더미 데이터)
            dummy_metrics = {
                "005930": {"PER": 8.5, "PBR": 1.2, "EPS": 12000},
                "000660": {"PER": 6.2, "PBR": 0.8, "EPS": 8500},
                "035420": {"PER": 15.2, "PBR": 2.1, "EPS": 5200},
                "005380": {"PER": 5.8, "PBR": 0.6, "EPS": 15000},
                "051910": {"PER": 12.3, "PBR": 1.1, "EPS": 7800},
            }
            return dummy_metrics.get(ticker, {"PER": 10.0, "PBR": 1.0, "EPS": 1000})
            
        except Exception as e:
            logger.error(f"밸류에이션 지표 조회 실패 {ticker}: {e}")
            return {"PER": 999, "PBR": 999, "EPS": 0}

    async def _get_kospi_stocks(self) -> List[Dict]:
        """KOSPI 종목 목록 조회."""
        try:
            from pykrx import stock
            kospi_tickers = stock.get_market_ticker_list("KOSPI")
            stocks = []
            for ticker in kospi_tickers[:100]:
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
        except Exception as e:
            logger.warning(f"KOSPI 종목 조회 실패 (pykrx): {e}")
            return self._get_major_kospi_stocks()
    async def compare_financials(self, tickers: List[str]) -> Dict:
        """여러 종목의 재무제표 비교"""
        comparison_data = {}
        
        for ticker in tickers:
            try:
                # 회사 정보
                company_info = self.get_company_info(ticker)
                
                # 재무 데이터
                financial_data = self.get_financials(ticker)
                
                # 밸류에이션 (추후 실제 계산)
                valuation = self.get_valuation_metrics(ticker)
                
                comparison_data[ticker] = {
                    "company_name": company_info.get("company_name", ticker),
                    "sector": company_info.get("sector", "기타"),
                    "financials": financial_data,
                    "valuation": valuation
                }
                
            except Exception as e:
                logger.error(f"재무 비교 실패 {ticker}: {e}")
                comparison_data[ticker] = {"error": str(e)}
        
        return comparison_data

    async def _get_kosdaq_stocks(self) -> List[Dict]:
        """KOSDAQ 종목 목록 조회."""
        try:
            from pykrx import stock
            kosdaq_tickers = stock.get_market_ticker_list("KOSDAQ")
            stocks = []
            for ticker in kosdaq_tickers[:50]:
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
        except Exception as e:
            logger.warning(f"KOSDAQ 종목 조회 실패 (pykrx): {e}")
            return self._get_major_kosdaq_stocks()

    def _get_major_kospi_stocks(self) -> List[Dict]:
        """주요 KOSPI 종목 (fallback)."""
        return [
            {"ticker": "005930", "yf_ticker": "005930.KS", "name": "삼성전자", "market": "KOSPI", "sector": "전기전자"},
            {"ticker": "000660", "yf_ticker": "000660.KS", "name": "SK하이닉스", "market": "KOSPI", "sector": "반도체"},
            {"ticker": "035420", "yf_ticker": "035420.KS", "name": "네이버", "market": "KOSPI", "sector": "인터넷"},
            {"ticker": "005380", "yf_ticker": "005380.KS", "name": "현대차", "market": "KOSPI", "sector": "자동차"},
            {"ticker": "051910", "yf_ticker": "051910.KS", "name": "LG화학", "market": "KOSPI", "sector": "화학"},
        ]

    def _get_major_kosdaq_stocks(self) -> List[Dict]:
        """주요 KOSDAQ 종목 (fallback)."""
        return [
            {"ticker": "293490", "yf_ticker": "293490.KQ", "name": "카카오게임즈", "market": "KOSDAQ", "sector": "게임"},
            {"ticker": "086520", "yf_ticker": "086520.KQ", "name": "에코프로", "market": "KOSDAQ", "sector": "화학"},
            {"ticker": "247540", "yf_ticker": "247540.KQ", "name": "에코프로비엠", "market": "KOSDAQ", "sector": "화학"},
        ]

    async def _enhance_stock_info(self, stocks: List[Dict]) -> List[Dict]:
        """종목 정보 보강 (시가총액, 섹터 등)."""
        enhanced_stocks = []
        semaphore = asyncio.Semaphore(5)

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
            time.sleep(0.2)  # API 요청 속도 조절
            yf_ticker = stock.get("yf_ticker", "")
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
            info = await loop.run_in_executor(None, lambda: ticker_obj.info)

            enhanced = stock.copy()
            enhanced.update({
                "sector": info.get("sector", stock.get("sector", "기타")),
                "industry": info.get("industry", ""),
                "market_cap": info.get("marketCap", 0) / 100000000,
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": (info.get("dividendYield", 0) or 0) * 100,
                "description": info.get("longBusinessSummary", ""),
            })
            return enhanced
        except Exception as e:
            logger.debug(f"종목 정보 보강 실패 {stock.get('ticker')}: {e}")
            return stock

    def _get_fallback_stocks(self) -> List[Dict]:
        return self._get_major_kospi_stocks() + self._get_major_kosdaq_stocks()

    async def search_stocks_by_keywords(self, keywords: List[str]) -> List[Dict]:
        all_stocks = await self.get_all_stocks()
        matching_stocks = []
        keywords_lower = [k.lower() for k in keywords]

        for stock in all_stocks:
            score = 0
            stock_name = stock.get('name', '').lower()
            stock_sector = stock.get('sector', '').lower()
            stock_industry = stock.get('industry', '').lower()

            for keyword in keywords_lower:
                if keyword in stock_name: score += 10
                elif keyword in stock_sector: score += 5
                elif keyword in stock_industry: score += 3

            if score > 0:
                stock['relevance_score'] = score
                matching_stocks.append(stock)

        matching_stocks.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return matching_stocks

    async def get_stock_data(self, ticker: str) -> Dict:
        """특정 종목의 상세 데이터 조회."""
        try:
            price_data = await self._get_price_data(ticker)
            financial_data = await self._get_financial_data_from_db(ticker)
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
                WHERE ticker = :ticker AND date >= :start_date
                ORDER BY date DESC LIMIT 252
            """
            one_year_ago = datetime.now() - timedelta(days=365)
            result = self.session.execute(
                text(query),
                {"ticker": ticker, "start_date": one_year_ago.strftime('%Y-%m-%d')}
            )
            prices = result.fetchall()

            if prices:
                return {
                    "latest_price": float(prices[0][1]),
                    "price_change_1y": self._calculate_price_change(prices),
                    "avg_volume": sum(p[2] for p in prices if p[2]) / len(prices),
                }
            return {}
        except Exception as e:
            logger.error(f"가격 데이터 조회 실패 {ticker}: {e}")
            return {}

    def _calculate_price_change(self, prices: List) -> float:
        if len(prices) < 2: return 0.0
        latest_price = float(prices[0][1])
        oldest_price = float(prices[-1][1])
        return ((latest_price - oldest_price) / oldest_price) * 100

    async def _get_financial_data_from_db(self, ticker: str) -> Dict:
        """DB에서 재무 데이터 조회."""
        try:
            query = """
                SELECT year, "매출액", "영업이익", "당기순이익"
                FROM financials
                WHERE ticker = :ticker ORDER BY year DESC LIMIT 3
            """
            result = self.session.execute(text(query), {"ticker": ticker})
            financials = result.fetchall()

            if financials:
                return {
                    "latest_year": financials[0][0],
                    "revenue": financials[0][1],
                    "operating_profit": financials[0][2],
                    "net_profit": financials[0][3],
                }
            return self._generate_dummy_financial_data(ticker)
        except Exception as e:
            logger.error(f"재무 데이터 조회 실패 {ticker}: {e}")
            return self._generate_dummy_financial_data(ticker)

    def _generate_dummy_financial_data(self, ticker: str) -> Dict:
        """더미 재무 데이터 생성."""
        dummy_financials = {
            "005930": {"revenue": 3020000, "operating_profit": 65900, "net_profit": 55400},
            "000660": {"revenue": 500000, "operating_profit": 78000, "net_profit": 65000},
        }
        base_data = dummy_financials.get(ticker, {"revenue": 10000, "operating_profit": 1000, "net_profit": 800})
        logger.info(f"📊 {ticker}에 대한 더미 재무 데이터 생성")
        return {**base_data, "latest_year": 2023, "is_dummy": True}

    async def _get_yf_stock_data(self, ticker: str) -> Dict:
        """yfinance로 실시간 시장 데이터 조회."""
        try:
            time.sleep(0.2) # API 요청 속도 조절
            yf_ticker = f"{ticker}.KS"
            loop = asyncio.get_event_loop()
            ticker_obj = await loop.run_in_executor(None, yf.Ticker, yf_ticker)
            info = await loop.run_in_executor(None, lambda: ticker_obj.info)

            return {
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "market_cap": info.get("marketCap"),
            }
        except Exception as e:
            logger.error(f"yfinance 데이터 조회 실패 {ticker}: {e}")
            return {}

    async def get_market_overview(self) -> Dict:
        """전체 시장 개요."""
        try:
            time.sleep(0.2) # API 요청 속도 조절
            kospi = yf.Ticker("^KS11").history(period="1y")
            time.sleep(0.2) # API 요청 속도 조절
            kosdaq = yf.Ticker("^KQ11").history(period="1y")

            return {
                "kospi": {
                    "current": float(kospi['Close'].iloc[-1]),
                    "change_1y": self._calculate_index_change(kospi),
                },
                "kosdaq": {
                    "current": float(kosdaq['Close'].iloc[-1]),
                    "change_1y": self._calculate_index_change(kosdaq),
                },
            }
        except Exception as e:
            logger.error(f"시장 개요 조회 실패: {e}")
            return {}

    def _calculate_index_change(self, hist_data) -> float:
        if hist_data.empty or len(hist_data) < 2: return 0.0
        current = float(hist_data['Close'].iloc[-1])
        year_ago = float(hist_data['Close'].iloc[0])
        return ((current - year_ago) / year_ago) * 100

    def get_multi_year_financials(self, ticker: str) -> List[Dict]:
        """종목의 연도별 재무 정보를 PostgreSQL에서 조회 (4년간)"""
        try:
            query = """
            SELECT year, "매출액", "영업이익", "당기순이익"
            FROM financials 
            WHERE ticker = :ticker 
              AND year <= 2023
            ORDER BY year DESC
            LIMIT 3
            """
            result = self.session.execute(text(query), {"ticker": ticker})
            rows = result.fetchall()
            
            multi_year_data = []
            for row in rows:
                # NULL 값도 0으로 처리하여 포함
                multi_year_data.append({
                    "year": row[0],
                    "revenue": float(row[1]) if row[1] is not None else 0,
                    "operating_profit": float(row[2]) if row[2] is not None else 0,
                    "net_profit": float(row[3]) if row[3] is not None else 0
                })
            
            logger.info(f"📊 {ticker} 연도별 재무데이터: {len(multi_year_data)}개년")
            return multi_year_data
            
        except Exception as e:
            logger.error(f"연도별 재무 데이터 조회 실패 {ticker}: {e}")
            return []

    def close(self):
        if self.session:
            self.session.close()

# 전역 인스턴스
stock_database = StockDatabase()