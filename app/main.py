"""Enhanced FastAPI 엔트리포인트 - AI 에이전트 기능 추가."""
from __future__ import annotations

import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

from app.services.models import (
    PortfolioRequest, 
    PortfolioResponse,
    ChatRequest,
    ChatResponse,
    MarketAnalysisRequest,
    MarketAnalysisResponse
)
from app.services.portfolio import create_portfolio_with_explanation
from app.services.portfolio_enhanced import enhanced_explainer
from app.services.ai_agent import (
    chat_with_agent,
    analyze_market_trends,
    get_stock_recommendations,
    analyze_financial_metrics
)
from app.services.financial_comparison import financial_comparison_service
from app.services.news_analysis import news_analysis_service

app = FastAPI(
    title="Intelligent Portfolio AI Agent",
    description="HyperCLOVA 기반 지능형 포트폴리오 추천 및 투자 상담 AI",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기존 포트폴리오 추천 API (하위 호환성)
@app.post("/portfolio/recommend", response_model=PortfolioResponse)
async def recommend_portfolio(payload: PortfolioRequest):
    """
    포트폴리오 추천 + HyperCLOVA 설명 API (기존).
    """
    result = await create_portfolio_with_explanation(
        tickers=payload.tickers,
        age=payload.age,
        experience=payload.experience,
        risk_profile=payload.risk_profile,
        investment_goal=payload.investment_goal,
        investment_period=payload.investment_period,
    )
    return result

# 새로운 강화된 포트폴리오 추천 API
@app.post("/portfolio/enhanced-recommend")
async def enhanced_portfolio_recommendation(payload: PortfolioRequest):
    """
    강화된 포트폴리오 추천 + 상세 근거 설명.
    
    기존 API보다 더 상세한 근거와 분석을 제공합니다:
    - 각 종목별 선정 이유와 재무 분석
    - 기술적 분석 지표
    - 밸류에이션 평가
    - 위험 요소 분석
    """
    try:
        # 기본 포트폴리오 최적화
        basic_result = await create_portfolio_with_explanation(
            tickers=payload.tickers,
            age=payload.age,
            experience=payload.experience,
            risk_profile=payload.risk_profile,
            investment_goal=payload.investment_goal,
            investment_period=payload.investment_period,
        )
        
        # 상세 근거 생성
        user_profile = {
            "age": payload.age,
            "experience_level": payload.experience,
            "risk_tolerance": payload.risk_profile,
            "investment_goal": payload.investment_goal,
            "investment_period": payload.investment_period
        }
        
        detailed_explanation = await enhanced_explainer.generate_detailed_explanation(
            weights=basic_result["weights"],
            performance=(
                basic_result["performance"]["expected_annual_return"],
                basic_result["performance"]["annual_volatility"],
                basic_result["performance"]["sharpe_ratio"]
            ),
            user_profile=user_profile,
            user_message="포트폴리오 추천 요청"
        )
        
        return {
            **basic_result,
            "detailed_explanation": detailed_explanation,
            "analysis_type": "enhanced"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 새로운 AI 에이전트 API들
@app.post("/ai/chat", response_model=ChatResponse)
async def chat_with_ai_agent(payload: ChatRequest):
    """
    자연어 대화형 투자 상담 AI.
    
    사용자가 자연어로 질문하면 AI가 적절한 종목 추천, 
    포트폴리오 구성, 투자 조언을 제공합니다.
    
    예시:
    - "월 100만원 투자 가능하고 초보자인데 추천해주세요"
    - "삼성전자 재무상태 어떤가요?"
    - "현재 반도체 섹터 전망은?"
    """
    try:
        response = await chat_with_agent(
            user_message=payload.message,
            user_profile=payload.user_profile,
            conversation_history=payload.conversation_history
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/recommendations")
async def get_ai_stock_recommendations(payload: ChatRequest):
    """
    AI 기반 개인화 종목 추천.
    
    사용자 프로필과 질문을 바탕으로 KOSPI/KOSDAQ 전체 종목에서
    최적의 종목들을 추천하고 포트폴리오를 구성합니다.
    """
    try:
        recommendations = await get_stock_recommendations(
            user_message=payload.message,
            user_profile=payload.user_profile
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/market-analysis", response_model=MarketAnalysisResponse)
async def analyze_market(payload: MarketAnalysisRequest):
    """
    AI 기반 시장 동향 분석.
    
    특정 섹터, 종목, 또는 전체 시장에 대한 
    심층 분석과 투자 인사이트를 제공합니다.
    """
    try:
        analysis = await analyze_market_trends(
            analysis_type=payload.analysis_type,
            target=payload.target,
            time_period=payload.time_period
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/financial-analysis")
async def analyze_financials(ticker: str, user_question: str = None):
    """
    특정 종목의 재무지표 AI 분석.
    
    재무제표, 성장성, 수익성, 안정성 등을 
    AI가 분석하여 쉽게 설명해드립니다.
    """
    try:
        analysis = await analyze_financial_metrics(
            ticker=ticker,
            user_question=user_question
        )
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 재무제표 비교 API
@app.post("/ai/compare-financials")
async def compare_company_financials(
    tickers: List[str] = Query(..., description="비교할 종목 코드들"),
    years: int = Query(3, description="분석할 연도 수"),
    user_question: str = Query(None, description="사용자 질문")
):
    """
    기업간 재무제표 비교 분석 + 도표/그래프 제공.
    
    예시: "삼성전자와 SK하이닉스의 최근 3년간 재무제표를 비교해 줘"
    
    제공 기능:
    - 📊 매출액, 영업이익, 순이익 비교 차트
    - 📈 수익성 지표 시각화
    - 📉 성장률 분석 그래프
    - 🎯 레이더 차트로 종합 경쟁력 비교
    - 🤖 HyperCLOVA 기반 상세 분석
    """
    try:
        if len(tickers) < 2:
            raise HTTPException(status_code=400, detail="최소 2개 이상의 종목이 필요합니다")
        
        if len(tickers) > 5:
            raise HTTPException(status_code=400, detail="최대 5개까지 비교 가능합니다")
        
        comparison_result = await financial_comparison_service.compare_companies_financial(
            company_codes=tickers,
            years=years,
            user_question=user_question
        )
        
        return comparison_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 뉴스 감성 분석 API
@app.post("/ai/news-analysis")
async def analyze_stock_news(
    ticker: str = Query(..., description="분석할 종목 코드"),
    days: int = Query(7, description="분석할 기간 (일)"),
    max_articles: int = Query(50, description="최대 뉴스 수")
):
    """
    종목별 뉴스 호재/악재 자동 분류 및 감성 분석.
    
    예시: "삼성전자 관련 최근 뉴스의 호재/악재 여부를 분석해 줘"
    
    제공 기능:
    - 📰 관련 뉴스 자동 수집
    - 🤖 HyperCLOVA 기반 호재/악재 자동 분류
    - 📊 감성 점수 (-100 ~ +100) 계산
    - 📈 시간별 감성 추이 분석
    - 💡 투자 영향도 평가 및 추천
    """
    try:
        news_analysis = await news_analysis_service.analyze_stock_news(
            ticker=ticker,
            days=days,
            max_articles=max_articles
        )
        
        return news_analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai/market-news-analysis")
async def analyze_market_news(
    sector: Optional[str] = Query(None, description="분석할 섹터 (없으면 전체 시장)"),
    days: int = Query(3, description="분석할 기간 (일)"),
    max_articles: int = Query(100, description="최대 뉴스 수")
):
    """
    시장/섹터별 뉴스 동향 분석.
    
    예시: "반도체 업종의 최근 뉴스 동향과 투자 전망을 분석해 줘"
    
    제공 기능:
    - 🌐 시장 전체 또는 특정 섹터 뉴스 분석
    - 📊 섹터별 감성 분포
    - 📈 시장 트렌드 및 모멘텀 분석
    - ⚠️ 리스크 요인 자동 식별
    - 🎯 주요 테마 및 이슈 추출
    """
    try:
        market_news_analysis = await news_analysis_service.analyze_market_news(
            sector=sector,
            days=days,
            max_articles=max_articles
        )
        
        return market_news_analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 종합 투자 분석 API
@app.post("/ai/comprehensive-analysis")
async def comprehensive_investment_analysis(
    ticker: str = Query(..., description="분석할 종목 코드"),
    include_news: bool = Query(True, description="뉴스 분석 포함 여부"),
    include_comparison: bool = Query(False, description="동종업계 비교 포함 여부"),
    comparison_tickers: Optional[List[str]] = Query(None, description="비교할 종목들")
):
    """
    종목별 종합 투자 분석 (All-in-One).
    
    하나의 API로 다음을 모두 제공:
    - 📊 재무제표 분석
    - 📰 최근 뉴스 감성 분석  
    - 📈 기술적 분석 지표
    - 💰 밸류에이션 평가
    - 🎯 투자 추천 의견
    - 📋 동종업계 비교 (선택)
    """
    try:
        analysis_result = {
            "ticker": ticker,
            "analysis_timestamp": datetime.now().isoformat(),
            "components": {}
        }
        
        # 1. 기본 재무 분석
        financial_analysis = await analyze_financial_metrics(
            ticker=ticker,
            user_question="이 종목의 투자 가치를 종합 분석해주세요"
        )
        analysis_result["components"]["financial_analysis"] = financial_analysis
        
        # 2. 뉴스 분석 (선택)
        if include_news:
            news_analysis = await news_analysis_service.analyze_stock_news(
                ticker=ticker,
                days=7,
                max_articles=30
            )
            analysis_result["components"]["news_analysis"] = news_analysis
        
        # 3. 동종업계 비교 (선택)
        if include_comparison and comparison_tickers:
            all_tickers = [ticker] + comparison_tickers
            comparison_analysis = await financial_comparison_service.compare_companies_financial(
                company_codes=all_tickers,
                years=3,
                user_question=f"{ticker} 종목의 경쟁력을 동종업계와 비교해주세요"
            )
            analysis_result["components"]["comparison_analysis"] = comparison_analysis
        
        # 4. 종합 투자 의견 생성
        comprehensive_opinion = await _generate_comprehensive_investment_opinion(
            analysis_result, ticker
        )
        analysis_result["comprehensive_opinion"] = comprehensive_opinion
        
        return analysis_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 헬퍼 함수
async def _generate_comprehensive_investment_opinion(analysis_data: dict, ticker: str) -> str:
    """종합 투자 의견 생성."""
    
    context = f"""
종목 코드: {ticker}
분석 일시: {analysis_data['analysis_timestamp']}

수집된 분석 데이터:
{json.dumps(analysis_data['components'], ensure_ascii=False, indent=2)}

위 모든 분석 결과를 종합하여 다음 관점에서 최종 투자 의견을 제시해주세요:

1. **종합 투자 등급** (매수/보유/매도)
2. **핵심 투자 포인트** (3가지)
3. **주요 리스크 요인** (3가지)
4. **목표 주가 및 투자 기간**
5. **포트폴리오 비중 권장안**

전문적이고 객관적인 분석을 바탕으로 명확한 결론을 제시해주세요.
"""
    
    system_prompt = """
당신은 20년 경력의 투자 애널리스트입니다.
모든 분석 데이터를 종합하여 최종 투자 의견을 제시하세요.

의견 제시 원칙:
1. 데이터 기반의 객관적 판단
2. 리스크와 기회요인 균형적 평가  
3. 명확한 투자 등급과 근거 제시
4. 실행 가능한 구체적 조언
5. 투자 위험성 명시

모든 의견은 참고용이며 투자 책임은 개인에게 있음을 명시하세요.
"""
    
    from app.services.portfolio import _call_hcx_async
    import logging
    
    logger = logging.getLogger(__name__)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]
    
    try:
        comprehensive_opinion = await _call_hcx_async(messages)
        return comprehensive_opinion
    except Exception as e:
        logger.error(f"종합 투자 의견 생성 실패: {e}")
        return f"분석은 완료되었으나 종합 의견 생성에 실패했습니다. 오류: {str(e)}"

@app.get("/health")
async def health_check():
    """서비스 상태 확인."""
    return {"status": "healthy", "service": "Portfolio AI Agent"}

@app.get("/")
async def root():
    """API 소개."""
    return {
        "message": "Portfolio AI Agent API v2.0",
        "version": "2.0.0",
        "description": "HyperCLOVA 기반 지능형 투자 상담 AI",
        "features": [
            "🤖 자연어 대화형 투자 상담",
            "📊 AI 기반 개인화 종목 추천",
            "📈 시장 동향 분석",
            "💰 재무지표 분석",
            "📋 기업간 재무제표 비교 + 차트",
            "📰 뉴스 호재/악재 자동 분류",
            "🎯 종합 투자 분석"
        ],
        "endpoints": {
            "/ai/chat": "자연어 대화형 투자 상담",
            "/ai/recommendations": "개인화 종목 추천", 
            "/ai/market-analysis": "시장 동향 분석",
            "/ai/financial-analysis": "재무지표 분석",
            "/ai/compare-financials": "🆕 재무제표 비교 + 차트",
            "/ai/news-analysis": "🆕 뉴스 감성 분석",
            "/ai/market-news-analysis": "🆕 시장 뉴스 동향",
            "/ai/comprehensive-analysis": "🆕 종합 투자 분석",
            "/portfolio/recommend": "포트폴리오 최적화 (기존)",
            "/portfolio/enhanced-recommend": "🆕 강화된 포트폴리오 추천"
        },
        "data_sources": [
            "yfinance (주가 데이터)",
            "전체 KOSPI/KOSDAQ 종목", 
            "실시간 뉴스 수집",
            "HyperCLOVA X AI 분석"
        ]
    }