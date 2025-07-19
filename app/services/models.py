"""Enhanced Pydantic models for AI agent service."""
from __future__ import annotations

from typing import Dict, List, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, Field, constr, RootModel

# 기존 모델들 (하위 호환성)
class PortfolioRequest(BaseModel):
    """Request payload for creating a portfolio."""
    tickers: List[constr(strip_whitespace=True, min_length=1)] = Field(
        ...,
        example=["005930.KS", "035420.KS"],
        description="종목 티커 리스트 (KRX 코드 또는 yfinance 코드)",
    )
    age: int = Field(..., ge=0, le=120, example=35, description="고객 나이")
    experience: str = Field(..., example="초보", description="투자 경험")
    risk_profile: str = Field(..., example="중립형", description="리스크 성향")
    investment_goal: str = Field(..., example="은퇴준비", description="투자 목표")
    investment_period: str = Field(..., example="10년", description="투자 기간")

class PortfolioWeights(RootModel[Dict[str, float]]):
    """자산별 비중 딕셔너리 (ticker → weight)."""
    pass

class PortfolioPerformance(BaseModel):
    """최적화 결과 성과 지표"""
    expected_annual_return: float = Field(..., example=0.08)
    annual_volatility: float = Field(..., example=0.15)
    sharpe_ratio: float = Field(..., example=0.53)

class PortfolioResponse(BaseModel):
    """Response payload with explanation."""
    weights: PortfolioWeights
    performance: PortfolioPerformance
    explanation: str

# 새로운 AI 에이전트 모델들
class UserProfile(BaseModel):
    """사용자 프로필 정보."""
    age: Optional[int] = Field(None, ge=18, le=100, description="나이")
    monthly_income: Optional[int] = Field(None, ge=0, description="월 소득 (만원)")
    investment_amount: Optional[int] = Field(None, ge=0, description="투자 가능 금액 (만원)")
    experience_level: Optional[str] = Field(None, description="투자 경험 (초보/중급/고급)")
    risk_tolerance: Optional[str] = Field(None, description="위험 성향 (안전형/중립형/공격형)")
    investment_goal: Optional[str] = Field(None, description="투자 목표 (단기수익/장기투자/은퇴준비 등)")
    investment_period: Optional[str] = Field(None, description="투자 기간 (1년/3년/5년/10년 이상)")
    preferred_sectors: Optional[List[str]] = Field(default=[], description="선호 업종")
    excluded_sectors: Optional[List[str]] = Field(default=[], description="제외 업종")

class ConversationMessage(BaseModel):
    """대화 메시지."""
    role: Literal["user", "assistant"] = Field(..., description="메시지 역할")
    content: str = Field(..., description="메시지 내용")
    timestamp: datetime = Field(default_factory=datetime.now, description="메시지 시간")

class ChatRequest(BaseModel):
    """AI 채팅 요청."""
    message: str = Field(
        ..., 
        min_length=1, 
        max_length=1000,
        example="월 100만원 투자 가능하고 초보자인데 추천해주세요",
        description="사용자 질문/요청"
    )
    user_profile: Optional[UserProfile] = Field(None, description="사용자 프로필")
    conversation_history: Optional[List[ConversationMessage]] = Field(
        default=[], 
        description="이전 대화 내역"
    )

class StockRecommendation(BaseModel):
    """종목 추천 정보."""
    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    sector: str = Field(..., description="업종")
    reason: str = Field(..., description="추천 이유")
    target_weight: float = Field(..., ge=0, le=1, description="추천 비중")
    risk_level: str = Field(..., description="위험도 (낮음/보통/높음)")
    expected_return: Optional[float] = Field(None, description="예상 수익률")

class ChatResponse(BaseModel):
    """AI 채팅 응답."""
    message: str = Field(..., description="AI 응답 메시지")
    recommendations: Optional[List[StockRecommendation]] = Field(
        default=[], 
        description="종목 추천 목록"
    )
    suggested_portfolio: Optional[Dict[str, float]] = Field(
        None, 
        description="제안된 포트폴리오 비중"
    )
    market_insights: Optional[str] = Field(None, description="시장 인사이트")
    next_questions: Optional[List[str]] = Field(
        default=[],
        description="추천 질문들"
    )
    confidence_score: Optional[float] = Field(
        None, 
        ge=0, 
        le=1, 
        description="응답 신뢰도"
    )

class MarketAnalysisRequest(BaseModel):
    """시장 분석 요청."""
    analysis_type: Literal["sector", "stock", "market", "theme"] = Field(
        ..., 
        description="분석 유형"
    )
    target: str = Field(
        ..., 
        example="반도체",
        description="분석 대상 (섹터명, 종목코드, 테마 등)"
    )
    time_period: Optional[str] = Field(
        default="3M",
        description="분석 기간 (1M/3M/6M/1Y)"
    )

class MarketTrend(BaseModel):
    """시장 트렌드 정보."""
    trend_direction: str = Field(..., description="트렌드 방향 (상승/하락/횡보)")
    strength: float = Field(..., ge=0, le=1, description="트렌드 강도")
    key_drivers: List[str] = Field(..., description="주요 동력")
    risk_factors: List[str] = Field(..., description="위험 요소")

class MarketAnalysisResponse(BaseModel):
    """시장 분석 응답."""
    analysis_summary: str = Field(..., description="분석 요약")
    current_trend: MarketTrend = Field(..., description="현재 트렌드")
    key_metrics: Dict[str, float] = Field(..., description="주요 지표")
    recommendations: List[str] = Field(..., description="투자 권고사항")
    outlook: str = Field(..., description="전망")
    related_stocks: Optional[List[StockRecommendation]] = Field(
        default=[],
        description="관련 종목"
    )

class FinancialMetric(BaseModel):
    """재무 지표."""
    metric_name: str = Field(..., description="지표명")
    current_value: Optional[float] = Field(None, description="현재 값")
    industry_average: Optional[float] = Field(None, description="업종 평균")
    evaluation: str = Field(..., description="평가 (좋음/보통/나쁨)")
    explanation: str = Field(..., description="지표 설명")

class FinancialAnalysisResponse(BaseModel):
    """재무 분석 응답."""
    ticker: str = Field(..., description="종목 코드")
    company_name: str = Field(..., description="회사명")
    analysis_summary: str = Field(..., description="종합 분석")
    financial_metrics: List[FinancialMetric] = Field(..., description="재무 지표들")
    strengths: List[str] = Field(..., description="강점")
    weaknesses: List[str] = Field(..., description="약점")
    investment_rating: str = Field(..., description="투자 등급")
    target_price: Optional[float] = Field(None, description="목표가")

# RAG 시스템용 모델들
class StockInfo(BaseModel):
    """종목 기본 정보."""
    ticker: str
    name: str
    sector: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    description: Optional[str] = None

class SectorInfo(BaseModel):
    """섹터 정보."""
    sector_name: str
    description: str
    key_companies: List[str]
    market_outlook: str
    risk_factors: List[str]