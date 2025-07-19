"""강화된 포트폴리오 설명 및 근거 제공 서비스."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from app.services.portfolio import _call_hcx_async
from app.services.stock_database import StockDatabase
from utils.db import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

class EnhancedPortfolioExplainer:
    """강화된 포트폴리오 설명 생성 시스템."""
    
    def __init__(self):
        self.stock_db = StockDatabase()
        self.session = SessionLocal()
    
    async def generate_detailed_explanation(
        self,
        weights: Dict[str, float],
        performance: Tuple[float, float, float],
        user_profile: Dict,
        user_message: str
    ) -> str:
        """상세 근거가 포함된 포트폴리오 설명 생성."""
        
        # 1. 각 종목별 상세 분석 데이터 수집
        detailed_analysis = await self._collect_detailed_stock_analysis(list(weights.keys()))
        
        # 2. 시장 상황 및 섹터 분석
        market_context = await self._analyze_market_context(list(weights.keys()))
        
        # 3. 사용자 맞춤 근거 생성
        personalized_rationale = await self._generate_personalized_rationale(
            weights, user_profile, user_message
        )
        
        # 4. HyperCLOVA로 종합 설명 생성
        comprehensive_explanation = await self._generate_comprehensive_explanation(
            weights, performance, detailed_analysis, market_context, 
            personalized_rationale, user_profile
        )
        
        return comprehensive_explanation
    
    async def _collect_detailed_stock_analysis(self, tickers: List[str]) -> Dict:
        """각 종목별 상세 분석 데이터 수집."""
        analysis_data = {}
        
        for ticker in tickers:
            try:
                # yfinance 기반 상세 데이터
                stock_data = await self.stock_db.get_stock_data(ticker)
                
                # 재무 데이터
                financial_data = await self._get_detailed_financials(ticker)
                
                # 기술적 분석 지표
                technical_indicators = await self._calculate_technical_indicators(ticker)
                
                # 밸류에이션 분석
                valuation_metrics = await self._analyze_valuation(ticker)
                
                # 업종 내 위치 분석
                sector_position = await self._analyze_sector_position(ticker)
                
                analysis_data[ticker] = {
                    "basic_info": stock_data,
                    "financial_health": financial_data,
                    "technical_signals": technical_indicators,
                    "valuation": valuation_metrics,
                    "sector_position": sector_position,
                    "risk_assessment": await self._assess_stock_risk(ticker)
                }
                
            except Exception as e:
                logger.error(f"종목 분석 실패 {ticker}: {e}")
                analysis_data[ticker] = {"error": str(e)}
        
        return analysis_data
    
    async def _get_detailed_financials(self, ticker: str) -> Dict:
        """상세 재무 분석."""
        try:
            # 최근 3년 재무 데이터
            query = """
                SELECT year, 매출액, 영업이익, 당기순이익
                FROM financials
                WHERE ticker = %s
                ORDER BY year DESC
                LIMIT 3
            """
            
            result = self.session.execute(text(query), [ticker])
            financials = result.fetchall()
            
            if not financials:
                return {"status": "no_data"}
            
            # 성장률 계산
            revenue_growth = self._calculate_cagr([f[1] for f in financials if f[1]])
            profit_growth = self._calculate_cagr([f[3] for f in financials if f[3]])
            
            # 수익성 지표
            latest = financials[0]
            operating_margin = (latest[2] / latest[1] * 100) if latest[1] and latest[2] else 0
            net_margin = (latest[3] / latest[1] * 100) if latest[1] and latest[3] else 0
            
            return {
                "revenue_growth_3y": revenue_growth,
                "profit_growth_3y": profit_growth,
                "operating_margin": operating_margin,
                "net_margin": net_margin,
                "latest_revenue": latest[1],
                "latest_profit": latest[3],
                "financial_stability": self._assess_financial_stability(financials)
            }
            
        except Exception as e:
            logger.error(f"재무 분석 실패 {ticker}: {e}")
            return {"error": str(e)}
    
    def _calculate_cagr(self, values: List[float]) -> float:
        """연평균 성장률 계산."""
        if len(values) < 2 or not all(v > 0 for v in values):
            return 0.0
        
        start_value = values[-1]  # 가장 오래된 값
        end_value = values[0]     # 최신 값
        periods = len(values) - 1
        
        if start_value <= 0:
            return 0.0
        
        cagr = ((end_value / start_value) ** (1/periods) - 1) * 100
        return round(cagr, 2)
    
    def _assess_financial_stability(self, financials: List) -> str:
        """재무 안정성 평가."""
        if len(financials) < 2:
            return "데이터 부족"
        
        # 매출 안정성 (변동성 낮을수록 좋음)
        revenues = [f[1] for f in financials if f[1]]
        if len(revenues) < 2:
            return "분석 불가"
        
        revenue_volatility = self._calculate_volatility(revenues)
        
        # 수익성 추세
        profits = [f[3] for f in financials if f[3]]
        profit_trend = "개선" if len(profits) >= 2 and profits[0] > profits[-1] else "악화"
        
        if revenue_volatility < 15 and profit_trend == "개선":
            return "매우 안정"
        elif revenue_volatility < 25:
            return "안정"
        else:
            return "변동성 높음"
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """변동성 계산 (표준편차/평균)."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        return (std_dev / mean) * 100 if mean > 0 else 0.0
    
    async def _calculate_technical_indicators(self, ticker: str) -> Dict:
        """기술적 분석 지표 계산."""
        try:
            # 최근 60일 가격 데이터 조회
            query = """
                SELECT date, close, volume
                FROM prices_merged
                WHERE ticker = %s
                AND date >= %s
                ORDER BY date DESC
                LIMIT 60
            """
            
            start_date = datetime.now() - timedelta(days=90)
            result = self.session.execute(text(query), [ticker, start_date.date()])
            prices = result.fetchall()
            
            if len(prices) < 20:
                return {"status": "insufficient_data"}
            
            closes = [float(p[1]) for p in prices]
            
            # 이동평균
            ma_20 = sum(closes[:20]) / 20
            ma_60 = sum(closes) / len(closes) if len(closes) >= 60 else sum(closes) / len(closes)
            
            # 현재가 대비 이동평균 위치
            current_price = closes[0]
            ma_position = "상승추세" if current_price > ma_20 > ma_60 else "하락추세" if current_price < ma_20 < ma_60 else "횡보"
            
            # RSI 계산 (단순화)
            rsi = self._calculate_simple_rsi(closes[:14])
            
            # 거래량 분석
            volumes = [int(p[2]) for p in prices if p[2]]
            avg_volume = sum(volumes) / len(volumes) if volumes else 0
            recent_volume = volumes[0] if volumes else 0
            volume_signal = "거래량 증가" if recent_volume > avg_volume * 1.5 else "거래량 보통"
            
            return {
                "trend": ma_position,
                "ma20": ma_20,
                "ma60": ma_60,
                "rsi": rsi,
                "volume_signal": volume_signal,
                "price_momentum": "강세" if current_price > ma_20 else "약세"
            }
            
        except Exception as e:
            logger.error(f"기술적 분석 실패 {ticker}: {e}")
            return {"error": str(e)}
    
    def _calculate_simple_rsi(self, prices: List[float]) -> float:
        """단순 RSI 계산."""
        if len(prices) < 14:
            return 50.0  # 중립값
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i-1] - prices[i]  # 최근이 앞에 있음
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    async def _analyze_valuation(self, ticker: str) -> Dict:
        """밸류에이션 분석."""
        try:
            # yfinance 데이터로 PER, PBR 등 조회
            stock_data = await self.stock_db._get_yf_stock_data(ticker)
            
            pe_ratio = stock_data.get("pe_ratio", 0)
            pb_ratio = stock_data.get("pb_ratio", 0)
            
            # 업종 평균과 비교 (임시값 - 실제로는 DB에서 조회)
            sector_avg_pe = 15.0  # 실제로는 동적으로 계산
            sector_avg_pb = 1.2
            
            valuation_level = "저평가" if pe_ratio and pe_ratio < sector_avg_pe * 0.8 else \
                             "고평가" if pe_ratio and pe_ratio > sector_avg_pe * 1.2 else "적정평가"
            
            return {
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "sector_avg_pe": sector_avg_pe,
                "valuation_level": valuation_level,
                "dividend_yield": stock_data.get("dividend_yield", 0),
                "market_cap": stock_data.get("market_cap", 0)
            }
            
        except Exception as e:
            logger.error(f"밸류에이션 분석 실패 {ticker}: {e}")
            return {"error": str(e)}
    
    async def _analyze_sector_position(self, ticker: str) -> Dict:
        """업종 내 위치 분석."""
        try:
            # 해당 종목의 섹터 정보
            stock_info = await self.stock_db.get_stock_data(ticker)
            
            # 간단한 업종 내 위치 (실제로는 더 정교한 분석 필요)
            return {
                "sector": "기술",  # 실제로는 DB에서 조회
                "sector_rank": "상위 30%",  # 시가총액 기준
                "sector_outlook": "긍정적",
                "competitive_advantage": "기술력, 브랜드 파워"
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _assess_stock_risk(self, ticker: str) -> Dict:
        """종목별 리스크 평가."""
        try:
            # 가격 변동성 계산
            query = """
                SELECT close
                FROM prices_merged
                WHERE ticker = %s
                AND date >= %s
                ORDER BY date DESC
                LIMIT 252
            """
            
            one_year_ago = datetime.now() - timedelta(days=365)
            result = self.session.execute(text(query), [ticker, one_year_ago.date()])
            prices = [float(p[0]) for p in result.fetchall()]
            
            if len(prices) < 30:
                return {"risk_level": "분석불가"}
            
            # 일일 수익률 변동성
            returns = [(prices[i] / prices[i+1] - 1) for i in range(len(prices)-1)]
            volatility = self._calculate_volatility([abs(r) for r in returns])
            
            risk_level = "높음" if volatility > 3.0 else "보통" if volatility > 1.5 else "낮음"
            
            return {
                "risk_level": risk_level,
                "volatility": round(volatility, 2),
                "max_drawdown": self._calculate_max_drawdown(prices),
                "beta": 1.0  # 임시값
            }
            
        except Exception as e:
            return {"risk_level": "분석불가", "error": str(e)}
    
    def _calculate_max_drawdown(self, prices: List[float]) -> float:
        """최대 낙폭 계산."""
        if len(prices) < 2:
            return 0.0
        
        peak = prices[0]
        max_dd = 0.0
        
        for price in prices:
            if price > peak:
                peak = price
            
            drawdown = (peak - price) / peak
            max_dd = max(max_dd, drawdown)
        
        return round(max_dd * 100, 2)
    
    async def _analyze_market_context(self, tickers: List[str]) -> Dict:
        """시장 상황 및 섹터 분석."""
        try:
            # 전체 시장 상황
            market_overview = await self.stock_db.get_market_overview()
            
            # 포트폴리오 섹터 분포
            sector_distribution = {}
            for ticker in tickers:
                # 실제로는 DB에서 섹터 정보 조회
                sector = "기술"  # 임시값
                sector_distribution[sector] = sector_distribution.get(sector, 0) + 1
            
            return {
                "market_sentiment": market_overview.get("market_sentiment", "중립"),
                "kospi_trend": market_overview.get("kospi", {}).get("change_1y", 0),
                "sector_distribution": sector_distribution,
                "market_risk_factors": ["금리 상승", "환율 변동", "국제 정세"],
                "market_opportunities": ["AI 테마", "ESG 투자", "디지털 전환"]
            }
            
        except Exception as e:
            logger.error(f"시장 분석 실패: {e}")
            return {"error": str(e)}
    
    async def _generate_personalized_rationale(
        self,
        weights: Dict[str, float],
        user_profile: Dict,
        user_message: str
    ) -> str:
        """사용자 맞춤 근거 생성."""
        
        age = user_profile.get("age", 30)
        risk_tolerance = user_profile.get("risk_tolerance", "중립형")
        investment_goal = user_profile.get("investment_goal", "장기투자")
        experience = user_profile.get("experience_level", "초보")
        
        rationale_points = []
        
        # 나이대별 근거
        if age < 30:
            rationale_points.append("젊은 나이로 장기 투자 시간이 충분하여 성장주 비중을 높였습니다.")
        elif age < 50:
            rationale_points.append("중년층으로 안정성과 수익성의 균형을 맞춘 포트폴리오입니다.")
        else:
            rationale_points.append("안정적인 배당 수익과 원금 보존에 중점을 둔 구성입니다.")
        
        # 위험성향별 근거
        if risk_tolerance == "안전형":
            rationale_points.append("안전형 투자성향에 맞춰 대형우량주 중심으로 구성했습니다.")
        elif risk_tolerance == "공격형":
            rationale_points.append("공격적 투자성향에 맞춰 성장 가능성이 높은 종목들을 포함했습니다.")
        
        # 경험 수준별 근거
        if experience == "초보":
            rationale_points.append("투자 초보자가 이해하기 쉬운 대표적인 우량 기업들로 선별했습니다.")
        
        return " ".join(rationale_points)
    
    async def _generate_comprehensive_explanation(
        self,
        weights: Dict[str, float],
        performance: Tuple[float, float, float],
        detailed_analysis: Dict,
        market_context: Dict,
        personalized_rationale: str,
        user_profile: Dict
    ) -> str:
        """종합적인 포트폴리오 설명 생성."""
        
        # HyperCLOVA에 전달할 상세 컨텍스트 구성
        context = f"""
**포트폴리오 구성 및 성과**
- 종목별 비중: {weights}
- 예상 연수익률: {performance[0]:.1%}
- 연변동성: {performance[1]:.1%}
- 샤프비율: {performance[2]:.3f}

**사용자 맞춤 근거**
{personalized_rationale}

**각 종목별 상세 분석 근거**
{json.dumps(detailed_analysis, ensure_ascii=False, indent=2)}

**시장 상황 분석**
{json.dumps(market_context, ensure_ascii=False, indent=2)}

**사용자 프로필**
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

위 모든 분석 데이터를 바탕으로 다음 형식으로 상세한 포트폴리오 설명을 해주세요:

1. **포트폴리오 개요** (전체적인 투자 전략과 목표)
2. **종목별 선정 이유** (각 종목의 구체적 근거와 데이터)
3. **비중 배분 근거** (왜 이런 비중으로 배분했는지)
4. **리스크 분석** (예상되는 위험 요소와 대응 방안)
5. **투자 전략** (언제 매수/매도할지, 리밸런싱 시점)
6. **주의사항** (투자 시 반드시 고려해야 할 점들)

각 항목마다 구체적인 수치와 데이터를 인용하여 설득력 있는 설명을 제공해주세요.
특히 재무지표, 기술적 분석, 밸류에이션 수준 등을 구체적으로 언급해주세요.
"""
        
        # HyperCLOVA 시스템 프롬프트
        system_prompt = """
당신은 대한민국 최고 수준의 투자 전문가이자 포트폴리오 매니저입니다.
20년 이상의 경력을 가지고 있으며, CFA 자격을 보유하고 있습니다.

다음 원칙에 따라 포트폴리오를 설명해주세요:
1. 모든 주장은 구체적인 데이터와 수치로 뒷받침
2. 투자 위험을 명확히 고지
3. 사용자 수준에 맞는 쉬운 용어 사용
4. 실행 가능한 구체적 조언 제공
5. 감정적 판단이 아닌 객관적 분석 중심

절대 투자 수익을 보장하지 말고, 모든 투자의 원금 손실 가능성을 명시하세요.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            detailed_explanation = await _call_hcx_async(messages)
            return detailed_explanation
        except Exception as e:
            logger.error(f"HyperCLOVA 설명 생성 실패: {e}")
            return f"포트폴리오 분석을 완료했으나 상세 설명 생성에 실패했습니다. 오류: {str(e)}"
    
    def close(self):
        """리소스 정리."""
        if self.session:
            self.session.close()


# 전역 인스턴스
enhanced_explainer = EnhancedPortfolioExplainer()