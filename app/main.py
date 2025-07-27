# app/main.py

import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    PortfolioInput, PortfolioRequest, OptimizationMode, AnalysisType,
    EnhancedChatRequest, QuickRecommendationRequest, ChatRequest
)
from app.services.ai_agent import (
    analyze_portfolio, 
    get_single_portfolio_analysis,
    get_comparison_portfolio_analysis, 
    get_recommended_portfolio_analysis,
    chat_with_agent,
    get_stock_recommendations
)
from app.services.stock_database import StockDatabase
from utils.db import Base, engine

# 설정 import
try:
    from utils.config import DART_API_KEY, NCP_CLOVASTUDIO_API_KEY
    NCP_CLOVA_API_KEY = NCP_CLOVASTUDIO_API_KEY
except ImportError as e:
    logging.warning(f"Config import 오류: {e}")
    DART_API_KEY = None
    NCP_CLOVA_API_KEY = None

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 인스턴스
app = FastAPI(
    title="Mirae Asset Portfolio Management API - Enhanced",
    description="API for providing advanced portfolio analysis with multiple optimization modes.",
    version="2.0.0"
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 의존성 주입용 함수
def get_stock_db():
    db = StockDatabase()
    try:
        yield db
    finally:
        pass

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup...")
    logger.info(f"DART API Key Loaded: {'✅' if DART_API_KEY else '❌'}")
    logger.info(f"NCP CLOVA API Key Loaded: {'✅' if NCP_CLOVA_API_KEY else '❌'}")

@app.get("/", tags=["Root"])
async def read_root():
    return {
        "message": "Welcome to the Enhanced Mirae Asset Portfolio Management API",
        "version": "2.0.0",
        "features": [
            "Multiple optimization modes",
            "Comparison analysis", 
            "AI-powered recommendations"
        ]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        from utils.db import SessionLocal
        from sqlalchemy import text
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "healthy",
        "message": "Enhanced Portfolio AI API is running",
        "database_status": db_status,
        "api_version": "2.0.0",
        "timestamp": "2024-07-25"
    }

# ===== 새로운 향상된 엔드포인트들 =====

@app.post("/api/v2/portfolio/analyze", response_model=dict, tags=["Portfolio V2"])
async def enhanced_portfolio_analysis(
    user_input: PortfolioInput,
    db: StockDatabase = Depends(get_stock_db)
):
    """
    향상된 포트폴리오 분석 - 다중 최적화 방식 지원
    
    - mathematical: 순수 수학적 최적화
    - practical: 실무적 균형
    - conservative: 보수적 분산투자
    - comparison: 여러 방식 비교
    """
    try:
        result = await analyze_portfolio(user_input, db)
        return result
    except Exception as e:
        logger.error(f"Enhanced portfolio analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="포트폴리오 분석 중 오류가 발생했습니다.")

@app.post("/api/v2/portfolio/single", response_model=dict, tags=["Portfolio V2"])
async def single_optimization_analysis(
    user_input: PortfolioInput,
    optimization_mode: OptimizationMode,
    db: StockDatabase = Depends(get_stock_db)
):
    """특정 최적화 방식으로 포트폴리오 분석"""
    try:
        result = await get_single_portfolio_analysis(user_input, db, optimization_mode)
        return result
    except Exception as e:
        logger.error(f"Single optimization analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="단일 최적화 분석 중 오류가 발생했습니다.")

@app.post("/api/v2/portfolio/comparison", response_model=dict, tags=["Portfolio V2"])
async def comparison_analysis(
    user_input: PortfolioInput,
    db: StockDatabase = Depends(get_stock_db)
):
    """여러 최적화 방식 비교 분석"""
    try:
        result = await get_comparison_portfolio_analysis(user_input, db)
        return result
    except Exception as e:
        logger.error(f"Comparison analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="비교 분석 중 오류가 발생했습니다.")

@app.post("/api/v2/chat/enhanced", response_model=dict, tags=["AI Chat V2"])
async def enhanced_ai_chat(
    request: EnhancedChatRequest,
    db: StockDatabase = Depends(get_stock_db)
):
    """
    5단계 위험성향 시스템이 적용된 향상된 AI 채팅
    """
    try:
        from app.services.portfolio_enhanced import create_smart_portfolio
        from app.services.portfolio_explanation import generate_enhanced_portfolio_explanation
        from app.schemas import PortfolioInput
        
        response = {"message": "", "portfolio_analysis": None, "comparison_summary": None}
        
        # 포트폴리오 관련 질문인지 확인
        portfolio_keywords = ["투자", "포트폴리오", "주식", "종목", "추천", "만원", "억원", "적극", "안전", "공격", "중립"]
        is_portfolio_request = any(keyword in request.message for keyword in portfolio_keywords)
        
        if is_portfolio_request and request.include_portfolio:
            # 5단계 위험성향 시스템 사용
            
            # 사용자 프로필에서 PortfolioInput 생성
            user_profile = request.user_profile or {}
            
            # 투자 금액 추출 (만원 단위로 변환)
            investment_amount = user_profile.get("investment_amount", 1000)  # 기본값 1000만원
            if investment_amount < 1000:  # 1000만원 미만이면 만원 단위로 가정
                investment_amount *= 10000
            
            # 위험성향 추출 및 매핑
            raw_risk = user_profile.get("risk_appetite", user_profile.get("risk_tolerance", "중립형"))
            
            # UI에서 오는 상세 위험성향을 기본 3단계로 매핑
            risk_mapping = {
                "안전형 (원금보전 우선)": "안전형",
                "안정추구형 (안정성+수익성)": "안전형", 
                "위험중립형 (균형투자)": "중립형",
                "적극투자형 (성장투자)": "공격형",
                "공격투자형 (고위험고수익)": "공격형"
            }
            
            # 공격적 투자 키워드 감지
            aggressive_keywords = ["적극", "공격", "고위험", "고수익", "변동성", "성장"]
            if any(keyword in request.message for keyword in aggressive_keywords):
                mapped_risk = "공격형"
            else:
                mapped_risk = risk_mapping.get(raw_risk, raw_risk)
                
            # 기본값이 없으면 중립형으로 설정
            if not mapped_risk:
                mapped_risk = "중립형"
            
            portfolio_input = PortfolioInput(
                initial_capital=investment_amount,
                risk_appetite=mapped_risk,
                investment_amount=investment_amount,
                investment_goal=user_profile.get("investment_goal", "자산증식"),
                investment_period=user_profile.get("investment_period", "3년"),
                age=user_profile.get("age", 35),
                experience_level=user_profile.get("experience_level", "중급")
            )
            
            # 5단계 위험성향 포트폴리오 생성
            portfolio_result = create_smart_portfolio(
                user_input=portfolio_input,
                db=db,
                original_message=request.message
            )
            
            if "error" not in portfolio_result:
                # 성공적으로 포트폴리오 생성됨
                response["portfolio_analysis"] = portfolio_result
                
                # AI 설명 생성
                try:
                    explanation = await generate_enhanced_portfolio_explanation(portfolio_result)
                    response["message"] = explanation
                except Exception as e:
                    logger.error(f"AI 설명 생성 실패: {e}")
                    response["message"] = "포트폴리오가 성공적으로 생성되었습니다. 5단계 위험성향 분석 결과를 확인해보세요."
            else:
                # 포트폴리오 생성 실패 시 기존 시스템 사용
                chat_result = await chat_with_agent(request.message, request.user_profile)
                response["message"] = chat_result.get("explanation", chat_result.get("message", ""))
                if chat_result.get("portfolio_analysis"):
                    response["portfolio_analysis"] = chat_result["portfolio_analysis"]
        else:
            # 포트폴리오 관련이 아닌 일반 질문은 기존 시스템 사용
            chat_result = await chat_with_agent(request.message, request.user_profile)
            response["message"] = chat_result.get("explanation", chat_result.get("message", ""))
            if chat_result.get("portfolio_analysis"):
                response["portfolio_analysis"] = chat_result["portfolio_analysis"]
            if chat_result.get("recommendations"):
                response["recommendations"] = chat_result["recommendations"]
        
        return response
        
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="AI 채팅 중 오류가 발생했습니다.")

@app.post("/api/v2/quick-recommendation", response_model=dict, tags=["Quick Recommendation"])
async def quick_portfolio_recommendation(
    request: QuickRecommendationRequest,
    db: StockDatabase = Depends(get_stock_db)
):
    """빠른 포트폴리오 추천"""
    try:
        # QuickRecommendationRequest를 PortfolioInput으로 변환
        portfolio_input = PortfolioInput(
            initial_capital=request.investment_amount * 10000,
            risk_appetite=request.risk_level,
            experience_level=request.experience,
            optimization_mode=request.preferred_style,
            analysis_type=AnalysisType.COMPARISON if request.include_comparison else AnalysisType.RECOMMENDED
        )
        
        # 분석 실행
        if request.include_comparison:
            result = await get_comparison_portfolio_analysis(portfolio_input, db)
        else:
            result = await get_recommended_portfolio_analysis(portfolio_input, db)
        
        # 빠른 추천 형태로 응답 구성
        quick_response = {
            "recommendation_type": "comparison" if request.include_comparison else "single",
            "portfolio_summary": _create_portfolio_summary(result),
            "key_recommendations": _extract_key_recommendations(result),
            "next_steps": [
                "제안된 포트폴리오를 검토해보세요",
                "분할 매수를 통해 점진적으로 투자하세요", 
                "월 1회 포트폴리오 성과를 점검하세요"
            ],
            "full_analysis": result
        }
        
        return quick_response
        
    except Exception as e:
        logger.error(f"Quick recommendation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="빠른 추천 생성 중 오류가 발생했습니다.")

# ===== 기존 엔드포인트들 (호환성 유지) =====

@app.post("/api/v1/portfolio/analyze", response_model=dict, tags=["Portfolio V1 (Legacy)"])
async def legacy_portfolio_analysis(
    user_input: PortfolioInput,
    db: StockDatabase = Depends(get_stock_db)
):
    """기존 포트폴리오 분석 엔드포인트 (호환성 유지)"""
    try:
        result = await analyze_portfolio(user_input, db)
        return result
    except Exception as e:
        logger.error(f"Legacy portfolio analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during portfolio analysis.")

@app.post("/ai/chat", tags=["AI Chat V1 (Legacy)"])
async def legacy_ai_chat(request: ChatRequest):
    """기존 AI 채팅 엔드포인트 (호환성 유지)"""
    try:
        result = await chat_with_agent(request.message, request.user_profile)
        return result
    except Exception as e:
        logger.error(f"Legacy AI chat error: {e}")
        return {
            "message": "죄송합니다. 일시적인 오류가 발생했습니다.",
            "error": str(e)
        }

@app.post("/ai/recommendations", tags=["AI Recommendations V1 (Legacy)"])
async def legacy_ai_recommendations(request: dict):
    """기존 AI 종목 추천 엔드포인트 (호환성 유지)"""
    try:
        message = request.get("message", "")
        user_profile = request.get("user_profile", {})
        
        result = await get_stock_recommendations(message, user_profile)
        return result
        
    except Exception as e:
        logger.error(f"Legacy AI recommendations error: {e}")
        return {
            "recommendations": [],
            "error": str(e),
            "message": "추천 생성 중 오류가 발생했습니다."
        }

# ===== 테스트 및 유틸리티 엔드포인트들 =====

@app.post("/test/optimizer", tags=["Testing"])
def test_optimizer_endpoint(tickers: list[str]):
    """포트폴리오 최적화 엔진을 직접 테스트합니다."""
    try:
        from optimizer.optimize import PortfolioOptimizer, OptimizationMode
        
        results = {}
        
        # 각 최적화 모드별 테스트
        for mode in OptimizationMode:
            try:
                optimizer = PortfolioOptimizer(tickers=tickers, optimization_mode=mode)
                weights, perf = optimizer.optimize()
                
                results[mode.value] = {
                    "status": "success",
                    "weights": weights,
                    "performance": {
                        "expected_annual_return": perf[0],
                        "annual_volatility": perf[1],
                        "sharpe_ratio": perf[2]
                    },
                    "num_positions": len([w for w in weights.values() if w > 0.01]),
                    "max_weight": max(weights.values()) if weights else 0
                }
                
            except Exception as e:
                results[mode.value] = {"status": "error", "detail": str(e)}
        
        return {
            "status": "completed",
            "results_by_mode": results,
            "comparison": _compare_optimization_results(results)
        }
        
    except Exception as e:
        logger.error(f"Optimizer test failed: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

@app.get("/test/hyperclova", tags=["Testing"])
async def test_hyperclova_endpoint():
    """HyperCLOVA API 연결을 테스트합니다."""
    try:
        from app.services.hyperclova_client import test_hyperclova
        is_connected = await test_hyperclova()
        
        if is_connected:
            return {"status": "success", "message": "HyperCLOVA API is connected."}
        else:
            return {"status": "warning", "message": "HyperCLOVA API connection failed. Running in mock mode."}
            
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/api/optimization-modes", tags=["Info"])
async def get_optimization_modes():
    """사용 가능한 최적화 방식들의 정보를 반환합니다."""
    return {
        "modes": [
            {
                "name": "mathematical",
                "display_name": "수학적 최적화",
                "description": "샤프 비율을 최대화하는 순수 수학적 접근법",
                "characteristics": [
                    "최고의 위험 대비 수익률",
                    "종목 집중 가능성",
                    "고급 투자자에게 적합"
                ],
                "risk_level": "높음",
                "complexity": "고급"
            },
            {
                "name": "practical", 
                "display_name": "실무적 균형",
                "description": "수익성과 리스크 관리의 균형을 추구하는 실무적 접근법",
                "characteristics": [
                    "균형잡힌 위험-수익 구조",
                    "적당한 분산투자",
                    "중급 투자자에게 적합"
                ],
                "risk_level": "보통",
                "complexity": "중급"
            },
            {
                "name": "conservative",
                "display_name": "보수적 분산투자", 
                "description": "안정성을 최우선으로 하는 보수적 접근법",
                "characteristics": [
                    "높은 분산 효과",
                    "낮은 집중도 위험",
                    "초보 투자자에게 적합"
                ],
                "risk_level": "낮음",
                "complexity": "초급"
            }
        ],
        "selection_guide": {
            "초보_안전형": "conservative",
            "초보_중립형": "conservative", 
            "중급_안전형": "practical",
            "중급_중립형": "practical",
            "중급_공격형": "practical",
            "고급_공격형": "mathematical",
            "고급_중립형": "practical"
        }
    }

@app.get("/api/portfolio-stats/{analysis_id}", tags=["Analytics"])
async def get_portfolio_statistics(analysis_id: str):
    """포트폴리오 분석 통계 (향후 구현용 엔드포인트)"""
    # 향후 분석 결과 저장 및 통계 기능을 위한 엔드포인트
    return {
        "message": "Portfolio statistics feature coming soon",
        "analysis_id": analysis_id
    }

# ===== 헬퍼 함수들 =====

def _create_portfolio_summary(analysis_result: dict) -> dict:
    """분석 결과에서 포트폴리오 요약 생성"""
    
    portfolio_details = analysis_result.get("portfolio_details", {})
    weights = portfolio_details.get("weights", {})
    performance = portfolio_details.get("performance", {})
    stats = portfolio_details.get("portfolio_stats", {})
    
    # 상위 3개 종목 추출
    top_holdings = []
    if weights:
        sorted_weights = sorted(weights.items(), key=lambda x: x[1].get("weight", 0), reverse=True)
        for ticker, data in sorted_weights[:3]:
            top_holdings.append({
                "name": data.get("name", ticker),
                "weight": data.get("weight", 0),
                "sector": data.get("sector", "기타")
            })
    
    return {
        "top_holdings": top_holdings,
        "total_positions": stats.get("num_positions", 0),
        "expected_return": performance.get("expected_annual_return", 0),
        "volatility": performance.get("annual_volatility", 0),
        "sharpe_ratio": performance.get("sharpe_ratio", 0),
        "diversification_level": stats.get("diversification_level", "보통"),
        "concentration_risk": stats.get("concentration_risk", "보통")
    }

def _extract_key_recommendations(analysis_result: dict) -> list:
    """분석 결과에서 핵심 추천사항 추출"""
    
    recommendations = []
    portfolio_details = analysis_result.get("portfolio_details", {})
    
    # 포트폴리오 특성 기반 추천
    stats = portfolio_details.get("portfolio_stats", {})
    
    if stats.get("num_positions", 0) >= 5:
        recommendations.append("✅ 잘 분산된 포트폴리오로 리스크가 효과적으로 관리됩니다")
    elif stats.get("num_positions", 0) >= 3:
        recommendations.append("⚠️ 적당한 분산이지만 추가 분산을 고려해보세요")
    else:
        recommendations.append("⚠️ 집중도가 높으니 분산투자를 고려해보세요")
    
    # 성과 기반 추천
    performance = portfolio_details.get("performance", {})
    sharpe_ratio = performance.get("sharpe_ratio", 0)
    
    if sharpe_ratio > 1.0:
        recommendations.append("🎯 우수한 위험 대비 수익률을 보여줍니다")
    elif sharpe_ratio > 0.5:
        recommendations.append("👍 양호한 위험 대비 수익률입니다")
    else:
        recommendations.append("📊 위험 대비 수익률 개선을 고려해보세요")
    
    # 일반적인 투자 조언
    recommendations.extend([
        "📅 월 1회 정기적인 포트폴리오 점검을 권장합니다",
        "💰 분할 매수를 통해 평균 단가 효과를 노려보세요",
        "📈 장기적 관점을 유지하며 단기 변동에 흔들리지 마세요"
    ])
    
    return recommendations

def _compare_optimization_results(results: dict) -> dict:
    """최적화 결과들 비교 분석"""
    
    comparison = {
        "best_sharpe": {"mode": None, "value": 0},
        "best_return": {"mode": None, "value": 0},
        "lowest_risk": {"mode": None, "value": float('inf')},
        "most_diversified": {"mode": None, "positions": 0},
        "summary": ""
    }
    
    for mode, result in results.items():
        if result.get("status") == "success":
            perf = result.get("performance", {})
            
            # 최고 샤프 비율
            sharpe = perf.get("sharpe_ratio", 0)
            if sharpe > comparison["best_sharpe"]["value"]:
                comparison["best_sharpe"] = {"mode": mode, "value": sharpe}
            
            # 최고 수익률
            ret = perf.get("expected_annual_return", 0)
            if ret > comparison["best_return"]["value"]:
                comparison["best_return"] = {"mode": mode, "value": ret}
            
            # 최저 리스크
            vol = perf.get("annual_volatility", float('inf'))
            if vol < comparison["lowest_risk"]["value"]:
                comparison["lowest_risk"] = {"mode": mode, "value": vol}
            
            # 최고 분산
            positions = result.get("num_positions", 0)
            if positions > comparison["most_diversified"]["positions"]:
                comparison["most_diversified"] = {"mode": mode, "positions": positions}
    
    # 요약 생성
    comparison["summary"] = (
        f"효율성: {comparison['best_sharpe']['mode']}, "
        f"수익성: {comparison['best_return']['mode']}, "
        f"안정성: {comparison['lowest_risk']['mode']}, "
        f"분산성: {comparison['most_diversified']['mode']}"
    )
    
    return comparison

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8008, reload=True)