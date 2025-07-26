# app/services/portfolio_enhanced.py - PostgreSQL 데이터 활용 완전 수정 버전

import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from enum import Enum
from sqlalchemy import text

from app.schemas import PortfolioInput
from app.services.stock_database import StockDatabase
from optimizer.optimize import PortfolioOptimizer, OptimizationMode
from utils.db import SessionLocal

logger = logging.getLogger(__name__)

class MarketFilter(Enum):
    """시장 필터 타입"""
    KOSPI_ONLY = "kospi_only"
    KOSDAQ_ONLY = "kosdaq_only"
    MIXED = "mixed"
    AUTO = "auto"

class EnhancedStockScreener:
    """PostgreSQL 데이터 기반 종목 스크리너"""
    
    def __init__(self):
        self.session = SessionLocal()
    
    def analyze_user_request(self, user_message: str) -> MarketFilter:
        """사용자 요청에서 시장 선호도 분석"""
        if not user_message:
            return MarketFilter.AUTO
        
        message_lower = user_message.lower()
        
        # 명시적 시장 요청 분석
        kospi_keywords = ['코스피', 'kospi', '대형주', '우량주']
        kosdaq_keywords = ['코스닥', 'kosdaq', '성장주', '중소형']
        
        # 코스피 키워드 확인
        for keyword in kospi_keywords:
            if keyword in message_lower:
                logger.info(f"✅ 코스피 키워드 감지: {keyword}")
                return MarketFilter.KOSPI_ONLY
        
        # 코스닥 키워드 확인
        for keyword in kosdaq_keywords:
            if keyword in message_lower:
                logger.info(f"✅ 코스닥 키워드 감지: {keyword}")
                return MarketFilter.KOSDAQ_ONLY
        
        logger.info("✅ 자동 혼합 모드 (키워드 미감지)")
        return MarketFilter.AUTO
    
    def get_filtered_stocks(self, market_filter: MarketFilter, user_profile: PortfolioInput) -> pd.DataFrame:
        """PostgreSQL에서 실제 데이터 조회"""
        
        try:
            # 기본 쿼리 - 실제 데이터가 있는 종목만
            base_query = """
            WITH stock_data AS (
                SELECT DISTINCT 
                    ci.ticker,
                    ci.corp_name as name,
                    ci.market,
                    ci.sector,
                    COUNT(DISTINCT pm.date) as price_days,
                    MAX(pm.date) as latest_price_date,
                    AVG(pm.close) as avg_price,
                    MAX(f.매출액) as revenue,
                    MAX(f.영업이익) as operating_profit
                FROM company_info ci
                INNER JOIN prices_merged pm ON ci.ticker = pm.ticker
                LEFT JOIN financials f ON ci.ticker = f.ticker
                WHERE pm.date >= CURRENT_DATE - INTERVAL '30 days'
            """
            
            # 시장 필터 적용
            if market_filter == MarketFilter.KOSPI_ONLY:
                base_query += " AND ci.market = 'KOSPI'"
            elif market_filter == MarketFilter.KOSDAQ_ONLY:
                base_query += " AND ci.market = 'KOSDAQ'"
            elif market_filter == MarketFilter.MIXED:
                base_query += " AND ci.market IN ('KOSPI', 'KOSDAQ')"
            
            base_query += """
                GROUP BY ci.ticker, ci.corp_name, ci.market, ci.sector
                HAVING COUNT(DISTINCT pm.date) >= 20
            )
            SELECT * FROM stock_data
            ORDER BY revenue DESC NULLS LAST, avg_price DESC
            """
            
            result = self.session.execute(text(base_query))
            rows = result.fetchall()
            
            if rows:
                df = pd.DataFrame(rows, columns=[
                    'ticker', 'name', 'market', 'sector', 
                    'price_days', 'latest_price_date', 'avg_price',
                    'revenue', 'operating_profit'
                ])
                
                logger.info(f"📊 DB에서 {len(df)}개 종목 조회 성공")
                logger.info(f"시장별: KOSPI {len(df[df['market']=='KOSPI'])}개, KOSDAQ {len(df[df['market']=='KOSDAQ'])}개")
                
                return df
            else:
                logger.warning("⚠️ 조건에 맞는 종목이 없음")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ DB 조회 실패: {e}")
            return pd.DataFrame()
    
    def apply_user_profile_filter(self, stocks_df: pd.DataFrame, user_profile: PortfolioInput) -> List[str]:
        """사용자 프로필과 섹터 기반 종목 필터링"""
        
        if stocks_df.empty:
            return []
        
        risk_appetite = user_profile.risk_appetite
        
        # 위험 성향별 필터링
        if risk_appetite == "공격형":
            # 성장 섹터 우선
            growth_sectors = ['반도체', '게임', '바이오', '이차전지', '인터넷', 'IT', '소프트웨어']
            sector_stocks = stocks_df[stocks_df['sector'].isin(growth_sectors)]
            other_stocks = stocks_df[~stocks_df['sector'].isin(growth_sectors)]
            filtered = pd.concat([sector_stocks, other_stocks])
            max_stocks = 15
            
        elif risk_appetite == "안전형":
            # 안정적 섹터 우선
            stable_sectors = ['전기전자', '자동차', '화학', '금융', '통신', '유틸리티']
            sector_stocks = stocks_df[stocks_df['sector'].isin(stable_sectors)]
            other_stocks = stocks_df[~stocks_df['sector'].isin(stable_sectors)]
            filtered = pd.concat([sector_stocks, other_stocks])
            max_stocks = 10
            
        else:  # 중립형
            filtered = stocks_df
            max_stocks = 12
        
        # 최종 선별
        selected_tickers = filtered.head(max_stocks)['ticker'].tolist()
        
        logger.info(f"🎯 최종 선별: {len(selected_tickers)}개 종목")
        if selected_tickers:
            logger.info(f"종목: {selected_tickers[:5]}...")
        
        return selected_tickers
    
    def close(self):
        if self.session:
            self.session.close()

class SmartPortfolioAnalysisService:
    """PostgreSQL 데이터 기반 포트폴리오 분석"""
    
    def __init__(self, user_input: PortfolioInput, db: StockDatabase, original_message: str = ""):
        self.user_input = user_input
        self.db = db
        self.original_message = original_message
        self.screener = EnhancedStockScreener()
    
    def run_analysis(self) -> Dict[str, Any]:
        """메인 분석 실행"""
        try:
            # 1. 사용자 요청 분석
            market_filter = self.screener.analyze_user_request(self.original_message)
            
            # 2. PostgreSQL에서 실제 데이터 조회
            stocks_df = self.screener.get_filtered_stocks(market_filter, self.user_input)
            
            if stocks_df.empty:
                return {
                    "error": "데이터베이스에서 조건에 맞는 종목을 찾을 수 없습니다.",
                    "market_filter": market_filter.value
                }
            
            # 3. 사용자 프로필 기반 종목 선별
            selected_tickers = self.screener.apply_user_profile_filter(stocks_df, self.user_input)
            
            if not selected_tickers:
                return {"error": "선별 조건에 맞는 종목이 없습니다."}
            
            # 4. 포트폴리오 최적화
            optimizer = PortfolioOptimizer(
                tickers=selected_tickers,
                optimization_mode=self._determine_optimization_mode(),
                risk_profile=self.user_input.risk_appetite
            )
            
            weights, performance = optimizer.optimize()
            
            # 5. 결과 구성
            return self._build_analysis_result(
                weights, performance, selected_tickers, stocks_df, market_filter
            )
            
        except Exception as e:
            logger.error(f"❌ 포트폴리오 분석 실패: {e}")
            return {"error": f"분석 중 오류: {str(e)}"}
        
        finally:
            self.screener.close()
    
    def _determine_optimization_mode(self) -> OptimizationMode:
        """최적화 모드 결정"""
        risk_appetite = self.user_input.risk_appetite
        
        if risk_appetite == "공격형":
            return OptimizationMode.MATHEMATICAL
        elif risk_appetite == "안전형":
            return OptimizationMode.CONSERVATIVE
        else:
            return OptimizationMode.PRACTICAL
    
    def _build_analysis_result(self, weights, performance, tickers, stocks_df, market_filter):
        """분석 결과 구성"""
        
        # 종목별 상세 정보
        detailed_weights = {}
        
        for ticker_yf, weight in weights.items():
            if weight > 0.001:
                ticker = ticker_yf.replace('.KS', '').replace('.KQ', '')
                
                # DB에서 조회한 실제 정보 사용
                stock_info = stocks_df[stocks_df['ticker'] == ticker]
                
                if not stock_info.empty:
                    stock_row = stock_info.iloc[0]
                    detailed_weights[ticker_yf] = {
                        "name": stock_row['name'],
                        "weight": weight,
                        "sector": stock_row['sector'],
                        "market": stock_row['market'],
                        "revenue": float(stock_row['revenue']) if pd.notna(stock_row['revenue']) else None,
                        "avg_price": float(stock_row['avg_price']) if pd.notna(stock_row['avg_price']) else None
                    }
        
        # 시장 분포 계산
        markets = [info["market"] for info in detailed_weights.values()]
        
        return {
            "market_filter": market_filter.value,
            "selected_tickers_count": len(tickers),
            "weights": detailed_weights,
            "performance": {
                "expected_annual_return": performance[0],
                "annual_volatility": performance[1], 
                "sharpe_ratio": performance[2]
            },
            "portfolio_stats": {
                "num_positions": len(detailed_weights),
                "market_distribution": {
                    "KOSPI": markets.count("KOSPI"),
                    "KOSDAQ": markets.count("KOSDAQ")
                },
                "sector_distribution": self._calculate_sector_distribution(detailed_weights),
                "max_single_weight": max([info["weight"] for info in detailed_weights.values()]) if detailed_weights else 0
            },
            "data_source": "PostgreSQL real data"
        }
    
    def _calculate_sector_distribution(self, detailed_weights):
        """섹터 분포 계산"""
        sectors = {}
        for ticker, info in detailed_weights.items():
            sector = info["sector"]
            if sector in sectors:
                sectors[sector] += info["weight"]
            else:
                sectors[sector] = info["weight"]
        return {k: round(v, 4) for k, v in sectors.items()}

# 메인 진입점
def create_smart_portfolio(user_input: PortfolioInput, db: StockDatabase, original_message: str = "") -> Dict[str, Any]:
    """스마트 포트폴리오 생성"""
    service = SmartPortfolioAnalysisService(user_input, db, original_message)
    return service.run_analysis()