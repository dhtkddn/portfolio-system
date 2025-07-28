# app/services/portfolio_enhanced.py - PostgreSQL 데이터 활용 및 금융소비자보호법 준수 버전

import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from enum import Enum
from sqlalchemy import text

from app.schemas import PortfolioInput
from app.services.stock_database import StockDatabase
# from app.services.financial_comparison import financial_comparison_service  # matplotlib 의존성으로 인해 주석처리
from app.services.investor_protection import (
    InvestorProtectionService, 
    InvestorProfile, 
    InvestorType,
    RiskLevel
)
from optimizer.optimize import PortfolioOptimizer, OptimizationMode
from utils.db import SessionLocal

logger = logging.getLogger(__name__)

class MarketFilter(Enum):
    """시장 필터 타입"""
    KOSPI_ONLY = "kospi_only"
    KOSDAQ_ONLY = "kosdaq_only"
    MIXED = "mixed"
    AUTO = "auto"

class RiskProfileType(Enum):
    """5단계 위험성향 분류"""
    STABLE = "안정형"  # 20점 이하
    STABILITY_SEEKING = "안정추구형"  # 20-40점
    RISK_NEUTRAL = "위험중립형"  # 40-60점
    ACTIVE_INVESTMENT = "적극투자형"  # 60-80점
    AGGRESSIVE = "공격투자형"  # 80점 이상
    
    @classmethod
    def from_score(cls, score: int):
        """점수 기반 위험성향 결정"""
        if score <= 20:
            return cls.STABLE
        elif score <= 40:
            return cls.STABILITY_SEEKING
        elif score <= 60:
            return cls.RISK_NEUTRAL
        elif score <= 80:
            return cls.ACTIVE_INVESTMENT
        else:
            return cls.AGGRESSIVE
    
    @classmethod
    def from_simple_profile(cls, simple_profile: str):
        """기존 3단계 프로필을 5단계로 매핑"""
        mapping = {
            "안전형": cls.STABILITY_SEEKING,
            "중립형": cls.RISK_NEUTRAL,
            "공격형": cls.ACTIVE_INVESTMENT
        }
        return mapping.get(simple_profile, cls.RISK_NEUTRAL)

class AssetAllocationGuideline:
    """위험성향별 자산배분 가이드라인"""
    GUIDELINES = {
        RiskProfileType.STABLE: {
            "stocks": {"min": 0, "max": 10, "target": 5},
            "bonds": {"min": 80, "max": 90, "target": 85},
            "cash": {"min": 10, "max": 20, "target": 10},
            "description": "원금보전을 최우선으로 하며, 안정적인 수익을 추구",
            "suitable_sectors": ["유틸리티", "통신", "필수소비재"],
            "max_single_stock": 5,  # 단일 종목 최대 비중
            "preferred_market": "KOSPI"  # 선호 시장
        },
        RiskProfileType.STABILITY_SEEKING: {
            "stocks": {"min": 10, "max": 30, "target": 20},
            "bonds": {"min": 60, "max": 80, "target": 70},
            "cash": {"min": 10, "max": 20, "target": 10},
            "description": "안정성을 중시하되 일정 수준의 수익률 추구",
            "suitable_sectors": ["금융", "보험", "전기전자", "화학"],
            "max_single_stock": 10,
            "preferred_market": "KOSPI"
        },
        RiskProfileType.RISK_NEUTRAL: {
            "stocks": {"min": 30, "max": 60, "target": 45},
            "bonds": {"min": 30, "max": 60, "target": 45},
            "cash": {"min": 10, "max": 10, "target": 10},
            "description": "위험과 수익의 균형을 추구하는 중도적 투자",
            "suitable_sectors": ["전기전자", "화학", "자동차", "기계", "건설"],
            "max_single_stock": 15,
            "preferred_market": "MIXED"
        },
        RiskProfileType.ACTIVE_INVESTMENT: {
            "stocks": {"min": 60, "max": 80, "target": 70},
            "bonds": {"min": 10, "max": 30, "target": 20},
            "cash": {"min": 10, "max": 10, "target": 10},
            "description": "적극적인 수익 추구, 단기 변동성 감수",
            "suitable_sectors": ["반도체", "이차전지", "바이오", "IT", "게임"],
            "max_single_stock": 20,
            "preferred_market": "MIXED"
        },
        RiskProfileType.AGGRESSIVE: {
            "stocks": {"min": 80, "max": 100, "target": 90},
            "bonds": {"min": 0, "max": 20, "target": 10},
            "cash": {"min": 0, "max": 10, "target": 0},
            "description": "높은 수익률 추구, 원금손실 위험 감수",
            "suitable_sectors": ["반도체", "바이오", "게임", "인터넷", "신재생에너지"],
            "max_single_stock": 25,
            "preferred_market": "KOSDAQ"
        }
    }

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
                WHERE pm.date >= CURRENT_DATE - INTERVAL '180 days'
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
                HAVING COUNT(DISTINCT pm.date) >= 10
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
    
    def apply_user_profile_filter(self, stocks_df: pd.DataFrame, user_profile: PortfolioInput, risk_profile_5: RiskProfileType = None) -> List[str]:
        """사용자 프로필과 섹터 기반 종목 필터링 + 재무제표 스크리닝"""
        
        if stocks_df.empty:
            return []
        
        # 5단계 위험성향 사용 (없으면 기존 3단계에서 변환)
        if risk_profile_5 is None:
            risk_profile_5 = RiskProfileType.from_simple_profile(user_profile.risk_appetite)
        
        # 가이드라인 가져오기
        guideline = AssetAllocationGuideline.GUIDELINES[risk_profile_5]
        suitable_sectors = guideline["suitable_sectors"]
        max_single_stock = guideline["max_single_stock"]
        preferred_market = guideline["preferred_market"]
        
        # 시장 필터링
        if preferred_market == "KOSPI":
            market_filtered = stocks_df[stocks_df['market'] == 'KOSPI']
        elif preferred_market == "KOSDAQ":
            market_filtered = stocks_df[stocks_df['market'] == 'KOSDAQ']
        else:
            market_filtered = stocks_df
        
        # 섹터 필터링
        sector_stocks = market_filtered[market_filtered['sector'].isin(suitable_sectors)]
        other_stocks = market_filtered[~market_filtered['sector'].isin(suitable_sectors)]
        
        # 섹터 우선순위로 정렬
        filtered = pd.concat([sector_stocks, other_stocks])
        
        # 재무제표 기반 추가 스크리닝
        financial_filtered = self._apply_financial_screening(filtered, risk_profile_5)
        
        # 종목 수 결정 (위험성향에 따라)
        if risk_profile_5 in [RiskProfileType.STABLE, RiskProfileType.STABILITY_SEEKING]:
            max_stocks = 8  # 집중도 낮춤
        elif risk_profile_5 == RiskProfileType.RISK_NEUTRAL:
            max_stocks = 12
        else:
            max_stocks = 15  # 더 많은 종목 허용
        
        # 최종 선별
        selected_tickers = financial_filtered.head(max_stocks)['ticker'].tolist()
        
        logger.info(f"🎯 5단계 위험성향 기반 선별: {risk_profile_5.value}")
        logger.info(f"📊 재무제표 스크리닝 후: {len(financial_filtered)}개 → 최종 선별: {len(selected_tickers)}개")
        if selected_tickers:
            logger.info(f"종목: {selected_tickers[:5]}...")
        
        return selected_tickers
    
    def _apply_financial_screening(self, stocks_df: pd.DataFrame, risk_profile_5: RiskProfileType) -> pd.DataFrame:
        """위험성향별 재무제표 기반 스크리닝"""
        
        try:
            # 재무 데이터 조회 쿼리
            financial_query = """
                SELECT DISTINCT
                    f.ticker,
                    f.매출액 / 100000000 as revenue_billions,
                    f.영업이익 / 100000000 as operating_profit_billions,
                    f.당기순이익 / 100000000 as net_profit_billions,
                    CASE 
                        WHEN f.매출액 > 0 THEN (f.영업이익 / f.매출액 * 100)
                        ELSE 0 
                    END as operating_margin,
                    CASE 
                        WHEN f.매출액 > 0 THEN (f.당기순이익 / f.매출액 * 100)
                        ELSE 0 
                    END as net_margin,
                    f.year
                FROM financials f
                WHERE f.ticker IN ({})
                AND f.year = (SELECT MAX(year) FROM financials WHERE ticker = f.ticker)
                AND f.매출액 IS NOT NULL
                AND f.영업이익 IS NOT NULL
                AND f.당기순이익 IS NOT NULL
            """.format(','.join([f"'{t}'" for t in stocks_df['ticker'].tolist()]))
            
            financial_df = pd.read_sql(financial_query, self.session.get_bind())
            
            if financial_df.empty:
                logger.warning("재무 데이터 없음 - 기본 필터링만 적용")
                return stocks_df
            
            # 위험성향별 재무 기준 적용
            if risk_profile_5 == RiskProfileType.STABLE:
                # 안정형: 매출 1000억 이상, 영업이익률 5% 이상, 적자 제외
                criteria = (
                    (financial_df['revenue_billions'] >= 10) &
                    (financial_df['operating_margin'] >= 5.0) &
                    (financial_df['net_profit_billions'] > 0)
                )
                
            elif risk_profile_5 == RiskProfileType.STABILITY_SEEKING:
                # 안정추구형: 매출 500억 이상, 영업이익률 3% 이상
                criteria = (
                    (financial_df['revenue_billions'] >= 5) &
                    (financial_df['operating_margin'] >= 3.0) &
                    (financial_df['net_profit_billions'] > 0)
                )
                
            elif risk_profile_5 == RiskProfileType.RISK_NEUTRAL:
                # 위험중립형: 매출 100억 이상, 영업이익률 0% 이상
                criteria = (
                    (financial_df['revenue_billions'] >= 1) &
                    (financial_df['operating_margin'] >= 0)
                )
                
            elif risk_profile_5 == RiskProfileType.ACTIVE_INVESTMENT:
                # 적극투자형: 성장성 중시, 영업이익률 -5% 이상
                criteria = (
                    (financial_df['revenue_billions'] >= 0.5) &
                    (financial_df['operating_margin'] >= -5.0)
                )
                
            else:  # AGGRESSIVE
                # 공격투자형: 모든 종목 허용 (혁신기업 포함)
                criteria = financial_df['ticker'].notna()
            
            # 기준을 만족하는 종목만 필터링
            qualified_tickers = financial_df[criteria]['ticker'].tolist()
            financial_filtered = stocks_df[stocks_df['ticker'].isin(qualified_tickers)]
            
            # 재무 지표별 점수화 및 정렬
            scored_df = self._score_financial_metrics(financial_filtered, financial_df, risk_profile_5)
            
            logger.info(f"💰 재무제표 스크리닝: {len(stocks_df)} → {len(scored_df)}개 종목")
            return scored_df
            
        except Exception as e:
            logger.error(f"재무제표 스크리닝 실패: {e}")
            return stocks_df
    
    def _score_financial_metrics(self, stocks_df: pd.DataFrame, financial_df: pd.DataFrame, risk_profile_5: RiskProfileType) -> pd.DataFrame:
        """재무 지표 기반 점수화 및 정렬"""
        
        try:
            # 재무 데이터를 stocks_df에 병합
            merged_df = stocks_df.merge(financial_df, on='ticker', how='left')
            
            # 위험성향별 가중치 설정
            if risk_profile_5 in [RiskProfileType.STABLE, RiskProfileType.STABILITY_SEEKING]:
                # 안전성 중시: 수익성 > 규모 > 성장성
                weights = {'profitability': 0.5, 'stability': 0.3, 'growth': 0.2}
            elif risk_profile_5 == RiskProfileType.RISK_NEUTRAL:
                # 균형: 모든 지표 균등
                weights = {'profitability': 0.4, 'stability': 0.3, 'growth': 0.3}
            else:
                # 성장성 중시: 성장성 > 수익성 > 안정성
                weights = {'profitability': 0.3, 'stability': 0.2, 'growth': 0.5}
            
            # 점수 계산 - 안전한 처리
            merged_df['profitability_score'] = (
                merged_df['operating_margin'].fillna(0).astype(float) * 0.6 +
                merged_df['net_margin'].fillna(0).astype(float) * 0.4
            ).clip(0, 100)
            
            merged_df['stability_score'] = (
                merged_df['revenue_billions'].fillna(0).astype(float).apply(lambda x: min(x/100, 1) * 100)
            )
            
            # 성장성 점수 (단순화: 영업이익률 기준)
            merged_df['growth_score'] = merged_df['operating_margin'].fillna(0).astype(float).clip(0, 50) * 2
            
            # 종합 점수
            merged_df['total_score'] = (
                merged_df['profitability_score'].fillna(0) * weights['profitability'] +
                merged_df['stability_score'].fillna(0) * weights['stability'] +
                merged_df['growth_score'].fillna(0) * weights['growth']
            )
            
            # 점수순 정렬
            result_df = merged_df.sort_values('total_score', ascending=False)
            
            # 원본 컬럼만 반환
            return result_df[stocks_df.columns]
            
        except Exception as e:
            logger.error(f"재무 점수화 실패: {e}")
            return stocks_df
    
    def close(self):
        if self.session:
            self.session.close()

class SmartPortfolioAnalysisService:
    """PostgreSQL 데이터 기반 포트폴리오 분석 (금융소비자보호법 준수)"""
    
    def __init__(self, user_input: PortfolioInput, db: StockDatabase, original_message: str = ""):
        self.user_input = user_input
        self.db = db
        self.original_message = original_message
        self.screener = EnhancedStockScreener()
        self.protection_service = InvestorProtectionService()
        self.risk_profile_5 = None  # 5단계 위험성향
    
    def run_analysis(self) -> Dict[str, Any]:
        """메인 분석 실행"""
        try:
            # 1. 사용자 요청 분석
            market_filter = self.screener.analyze_user_request(self.original_message)
            
            # 2. 5단계 위험성향 결정
            self.risk_profile_5 = RiskProfileType.from_simple_profile(self.user_input.risk_appetite)
            
            # 3. PostgreSQL에서 실제 데이터 조회
            stocks_df = self.screener.get_filtered_stocks(market_filter, self.user_input)
            
            if stocks_df.empty:
                return {
                    "error": "데이터베이스에서 조건에 맞는 종목을 찾을 수 없습니다.",
                    "market_filter": market_filter.value
                }
            
            # 4. 5단계 위험성향 기반 종목 선별
            selected_tickers = self.screener.apply_user_profile_filter(stocks_df, self.user_input, self.risk_profile_5)
            
            if not selected_tickers:
                return {"error": "선별 조건에 맞는 종목이 없습니다."}
            
            # 5. 포트폴리오 최적화
            optimizer = PortfolioOptimizer(
                tickers=selected_tickers,
                optimization_mode=self._determine_optimization_mode(),
                risk_profile=self.user_input.risk_appetite
            )
            
            weights, performance = optimizer.optimize()
            
            # 위험성향별 단일 종목 한도 강제 적용
            guideline = AssetAllocationGuideline.GUIDELINES[self.risk_profile_5]
            max_single_stock = (guideline["max_single_stock"] - 0.5) / 100.0  # 0.5% 여유분으로 확실하게
            
            # 한도 초과 종목 조정 - 더 강력한 방법
            adjusted_weights = {}
            excess_weight = 0
            
            # 1차: 한도 초과 종목을 한도까지 줄이고 초과분 계산
            for ticker, weight in weights.items():
                if weight > max_single_stock:
                    adjusted_weights[ticker] = max_single_stock
                    excess_weight += weight - max_single_stock
                else:
                    adjusted_weights[ticker] = weight
            
            # 2차: 초과분을 한도 미달 종목에 분배
            if excess_weight > 0:
                under_limit_tickers = [t for t, w in adjusted_weights.items() if w < max_single_stock]
                if under_limit_tickers:
                    additional_weight = excess_weight / len(under_limit_tickers)
                    for ticker in under_limit_tickers:
                        new_weight = adjusted_weights[ticker] + additional_weight
                        if new_weight > max_single_stock:
                            adjusted_weights[ticker] = max_single_stock
                        else:
                            adjusted_weights[ticker] = new_weight
            
            # 비중 재정규화
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                final_weights = {k: v/total_weight for k, v in adjusted_weights.items()}
            else:
                final_weights = weights
            
            # 성과 지표 안전 처리
            safe_performance = (
                performance[0] if performance[0] is not None else 0.0,
                performance[1] if performance[1] is not None else 0.0,
                performance[2] if performance[2] is not None else 0.0
            )
            
            # 6. 결과 구성
            return self._build_analysis_result(
                final_weights, safe_performance, selected_tickers, stocks_df, market_filter
            )
            
        except Exception as e:
            logger.error(f"❌ 포트폴리오 분석 실패: {e}")
            return {"error": f"분석 중 오류: {str(e)}"}
        
        finally:
            self.screener.close()
    
    def _determine_optimization_mode(self) -> OptimizationMode:
        """5단계 위험성향 기반 최적화 모드 결정"""
        
        if self.risk_profile_5 in [RiskProfileType.STABLE, RiskProfileType.STABILITY_SEEKING]:
            return OptimizationMode.CONSERVATIVE
        elif self.risk_profile_5 in [RiskProfileType.RISK_NEUTRAL, RiskProfileType.ACTIVE_INVESTMENT]:
            return OptimizationMode.PRACTICAL
        else:  # AGGRESSIVE
            return OptimizationMode.MATHEMATICAL
    
    def _build_analysis_result(self, weights, performance, tickers, stocks_df, market_filter):
        """분석 결과 구성 (금융소비자보호법 준수)"""
        
        # 5단계 위험성향 가이드라인
        guideline = AssetAllocationGuideline.GUIDELINES[self.risk_profile_5]
        
        # 종목별 상세 정보
        detailed_weights = {}
        
        for ticker_yf, weight in weights.items():
            # None 체크 및 안전한 처리
            if weight is not None and weight > 0.001:
                ticker = ticker_yf.replace('.KS', '').replace('.KQ', '')
                
                # DB에서 조회한 실제 정보 사용
                stock_info = stocks_df[stocks_df['ticker'] == ticker]
                
                if not stock_info.empty:
                    stock_row = stock_info.iloc[0]
                    detailed_weights[ticker_yf] = {
                        "name": stock_row['name'],
                        "weight": float(weight),  # 명시적 형변환
                        "sector": stock_row['sector'],
                        "market": stock_row['market'],
                        "revenue": float(stock_row['revenue']) if pd.notna(stock_row['revenue']) else None,
                        "avg_price": float(stock_row['avg_price']) if pd.notna(stock_row['avg_price']) else None
                    }
        
        # 시장 분포 계산
        markets = [info["market"] for info in detailed_weights.values()]
        
        # 포트폴리오 위험 등급 산정
        # performance가 튜플이므로 인덱스로 접근
        if isinstance(performance, (tuple, list)) and len(performance) >= 2:
            volatility = performance[1]
        else:
            volatility = 0.15  # 기본값
        risk_level = self.protection_service.calculate_portfolio_risk_level(volatility)
        
        # 투자자 프로필 생성 (실제로는 사용자 입력 받아야 함)
        # investment_amount가 None일 경우 initial_capital 사용
        investment_amount = self.user_input.investment_amount or self.user_input.initial_capital
        
        investor_profile = InvestorProfile(
            age=40,  # 예시값
            investment_experience="3-5년",
            investment_goal="장기성장",
            risk_tolerance=self.user_input.risk_appetite,
            investment_amount=investment_amount,
            total_assets=investment_amount * 3,  # 예시값
            income_level=100000000,  # 예시값
            investment_ratio=0.33
        )
        
        # 투자자 유형 평가
        investor_type = self.protection_service.assess_investor_type(investor_profile)
        
        # 적합성 검증
        is_suitable, suitability_warnings = self.protection_service.check_suitability(
            investor_type, risk_level
        )
        
        # 적정성 검증
        portfolio_complexity = "보통"  # 실제로는 포트폴리오 구성에 따라 판단
        is_appropriate, appropriateness_warnings = self.protection_service.check_appropriateness(
            investor_profile, portfolio_complexity
        )
        
        # 집중도 위험 체크
        concentration_warnings = self.protection_service.check_concentration_risk(weights)
        
        # 위험 경고 메시지
        risk_warnings = self.protection_service.generate_warning_messages(risk_level)
        
        # 투자 설명서 생성
        # performance를 딕셔너리 형태로 변환
        performance_dict = {
            "expected_annual_return": performance[0] if isinstance(performance, (tuple, list)) and len(performance) > 0 else 0,
            "annual_volatility": performance[1] if isinstance(performance, (tuple, list)) and len(performance) > 1 else 0,
            "sharpe_ratio": performance[2] if isinstance(performance, (tuple, list)) and len(performance) > 2 else 0
        }
        
        investment_explanation = self.protection_service.generate_investment_explanation({
            "weights": detailed_weights,
            "performance": performance_dict
        })
        
        return {
            "market_filter": market_filter.value,
            "selected_tickers_count": len(tickers),
            "weights": detailed_weights,
            "performance": performance_dict,
            "risk_profile_analysis": {
                "risk_profile_type": self.risk_profile_5.value,
                "asset_allocation_guideline": {
                    "stocks_target": guideline["stocks"]["target"],
                    "bonds_target": guideline["bonds"]["target"],
                    "description": guideline["description"],
                    "suitable_sectors": guideline["suitable_sectors"],
                    "max_single_stock_limit": guideline["max_single_stock"],
                    "preferred_market": guideline["preferred_market"]
                },
                "compliance_check": {
                    "within_sector_guidelines": self._check_sector_compliance(detailed_weights, guideline),
                    "single_stock_limit_compliance": max([info["weight"] for info in detailed_weights.values()]) <= (guideline.get("max_single_stock", 20)/100) if detailed_weights else True
                }
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
            "investor_protection": {
                "risk_level": risk_level.value,
                "investor_type": investor_type.value,
                "is_suitable": is_suitable,
                "is_appropriate": is_appropriate,
                "warnings": {
                    "risk_warnings": risk_warnings,
                    "suitability_warnings": suitability_warnings,
                    "appropriateness_warnings": appropriateness_warnings,
                    "concentration_warnings": concentration_warnings
                },
                "investment_explanation": investment_explanation
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
    
    def _check_sector_compliance(self, detailed_weights, guideline):
        """섹터 가이드라인 준수 여부 확인"""
        if not detailed_weights:
            return True
        
        suitable_sectors = guideline["suitable_sectors"]
        total_suitable_weight = 0
        
        for ticker, info in detailed_weights.items():
            if info["sector"] in suitable_sectors:
                total_suitable_weight += info["weight"]
        
        # 권장 섹터 비중이 50% 이상이면 준수
        return total_suitable_weight >= 0.5

# 메인 진입점
def create_smart_portfolio(user_input: PortfolioInput, db: StockDatabase, original_message: str = "") -> Dict[str, Any]:
    """스마트 포트폴리오 생성"""
    service = SmartPortfolioAnalysisService(user_input, db, original_message)
    return service.run_analysis()