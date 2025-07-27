# app/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class OptimizationMode(str, Enum):
    """포트폴리오 최적화 방식"""
    MATHEMATICAL = "mathematical"   # 순수 수학적 최적화
    PRACTICAL = "practical"         # 실무적 제약조건 적용
    CONSERVATIVE = "conservative"   # 보수적 분산투자


class AnalysisType(str, Enum):
    """분석 유형"""
    SINGLE = "single"           # 단일 방식
    COMPARISON = "comparison"   # 비교 분석
    RECOMMENDED = "recommended" # AI 추천


class PortfolioInput(BaseModel):
    """포트폴리오 추천을 위한 사용자 입력 데이터 모델"""
    initial_capital: float = Field(..., description="초기 투자 자본")
    risk_appetite: str = Field(..., description="위험 성향 (안전형/중립형/공격형)")
    target_yield: float = Field(default=8.0, description="목표 수익률 (%)")
    
    # 기본 사용자 정보
    investment_goal: str = Field(default="장기투자", description="투자 목표")
    investment_period: str = Field(default="5년", description="투자 기간")
    age: Optional[int] = Field(default=35, description="나이")
    experience_level: str = Field(default="초보", description="투자 경험")
    
    # 금융소비자보호법 준수를 위한 추가 필드
    investment_amount: Optional[float] = Field(default=None, description="투자 금액")
    total_assets: Optional[float] = Field(default=None, description="총 자산")
    income_level: Optional[float] = Field(default=None, description="연 소득")
    
    # 추가 옵션 필드들
    preferred_sectors: Optional[List[str]] = Field(default=[], description="선호 업종")
    excluded_sectors: Optional[List[str]] = Field(default=[], description="제외 업종")
    max_single_stock_weight: float = Field(default=0.3, description="개별 종목 최대 비중")
    min_diversification: int = Field(default=3, description="최소 분산 종목 수")
    
    # 새로운 최적화 옵션들
    optimization_mode: Optional[OptimizationMode] = Field(
        default=None, 
        description="최적화 방식 (None이면 자동 결정)"
    )
    analysis_type: AnalysisType = Field(
        default=AnalysisType.RECOMMENDED,
        description="분석 유형"
    )
    
    # 🔥 사용자 원본 메시지 필드 추가
    original_message: Optional[str] = Field(
        default="",
        description="사용자 원본 메시지 (시장/섹터 분석용)"
    )
    
    # 🔥 Pydantic 설정 - 동적 필드 할당 허용
    class Config:
        extra = "allow"  # 추가 필드 허용


class PortfolioRequest(BaseModel):
    """포트폴리오 요청 (기존 호환성 유지)"""
    user_input: PortfolioInput
    analysis_options: Optional[dict] = Field(default={}, description="추가 분석 옵션")


class OptimizationResult(BaseModel):
    """단일 최적화 결과"""
    weights: dict = Field(..., description="종목별 비중")
    performance: dict = Field(..., description="예상 성과 지표")
    portfolio_stats: dict = Field(..., description="포트폴리오 통계")
    mode_description: str = Field(..., description="최적화 방식 설명")


class ComparisonResult(BaseModel):
    """비교 분석 결과"""
    mathematical: Optional[OptimizationResult] = None
    practical: Optional[OptimizationResult] = None  
    conservative: Optional[OptimizationResult] = None
    recommendation: str = Field(..., description="추천 의견")


class PortfolioResponse(BaseModel):
    """포트폴리오 분석 응답"""
    analysis_type: str = Field(..., description="분석 유형")
    user_profile: dict = Field(..., description="사용자 프로필")
    
    # 단일 분석 결과 (SINGLE, RECOMMENDED)
    result: Optional[dict] = None
    alternative_option: Optional[dict] = None  # RECOMMENDED 모드에서 대안
    
    # 비교 분석 결과 (COMPARISON)
    comparison_results: Optional[dict] = None
    
    # 공통 필드들
    explanation: str = Field(..., description="AI 생성 설명")
    recommendations: List[str] = Field(default=[], description="투자 권고사항")


class ChatRequest(BaseModel):
    """AI 채팅 요청 (기존 유지)"""
    message: str = Field(..., description="사용자 메시지")
    user_profile: Optional[dict] = Field(default={}, description="사용자 프로필")
    conversation_history: Optional[List[dict]] = Field(default=[], description="대화 이력")


class EnhancedChatRequest(BaseModel):
    """향상된 AI 채팅 요청"""
    message: str = Field(..., description="사용자 메시지")
    user_profile: Optional[dict] = Field(default={}, description="사용자 프로필")
    
    # 포트폴리오 관련 옵션
    include_portfolio: bool = Field(default=True, description="포트폴리오 추천 포함 여부")
    optimization_preference: Optional[str] = Field(
        default=None, 
        description="선호하는 최적화 방식 (mathematical, practical, conservative, None)"
    )
    comparison_analysis: bool = Field(default=False, description="비교 분석 수행 여부")
    
    # 기타 옵션
    conversation_history: Optional[List[dict]] = Field(default=[], description="대화 이력")
    context_data: Optional[dict] = Field(default={}, description="추가 컨텍스트 데이터")


class QuickRecommendationRequest(BaseModel):
    """빠른 추천 요청"""
    investment_amount: float = Field(..., description="투자 금액 (만원)")
    risk_level: Literal["안전형", "중립형", "공격형"] = Field(..., description="위험 성향")
    experience: Literal["초보", "중급", "고급"] = Field(default="초보", description="투자 경험")
    
    # 선택적 옵션
    preferred_style: Optional[OptimizationMode] = Field(default=None, description="선호 스타일")
    include_comparison: bool = Field(default=False, description="비교 분석 포함")


class MarketAnalysisRequest(BaseModel):
    """시장 분석 요청 (기존 유지)"""
    analysis_type: Literal["sector", "stock", "market", "theme"] = Field(..., description="분석 유형")
    target: str = Field(..., description="분석 대상")
    time_period: Optional[str] = Field(default="3M", description="분석 기간")


# 응답 모델들 (기존 유지하되 확장)
class StockRecommendation(BaseModel):
    """종목 추천 정보"""
    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    sector: str = Field(..., description="업종")
    reason: str = Field(..., description="추천 이유")
    target_weight: float = Field(..., ge=0, le=1, description="추천 비중")
    risk_level: str = Field(..., description="위험도")
    expected_return: Optional[float] = Field(None, description="예상 수익률")
    
    # 추가 정보
    optimization_context: Optional[str] = Field(None, description="최적화 맥락")
    alternative_weight: Optional[float] = Field(None, description="대안 방식에서의 비중")


class ChatResponse(BaseModel):
    """AI 채팅 응답"""
    message: str = Field(..., description="AI 응답 메시지")
    
    # 포트폴리오 관련
    recommendations: Optional[List[StockRecommendation]] = Field(default=[], description="종목 추천")
    portfolio_analysis: Optional[dict] = Field(None, description="포트폴리오 분석 결과")
    
    # 비교 분석 (요청 시)
    comparison_summary: Optional[str] = Field(None, description="비교 분석 요약")
    optimization_options: Optional[List[dict]] = Field(None, description="최적화 옵션들")
    
    # 기타
    market_insights: Optional[str] = Field(None, description="시장 인사이트")
    next_questions: Optional[List[str]] = Field(default=[], description="추천 질문들")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="응답 신뢰도")


# 편의성을 위한 별칭들
PortfolioInputLegacy = PortfolioInput  # 기존 코드 호환성
OptimizationModeType = OptimizationMode
AnalysisTypeEnum = AnalysisType