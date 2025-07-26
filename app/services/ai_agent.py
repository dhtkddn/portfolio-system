# app/services/ai_agent.py - 완전 수정 (메시지 의도 분석 추가)

import logging
import re
from typing import Dict, Any, Optional, List
from sqlalchemy import text

from app.schemas import PortfolioInput, AnalysisType, OptimizationMode
from app.services.stock_database import StockDatabase
from app.services.portfolio_enhanced import create_smart_portfolio
from app.services.hyperclova_client import get_hyperclova_response

logger = logging.getLogger(__name__)


class MessageIntentAnalyzer:
    """메시지 의도 분석기"""
    
    def __init__(self):
        # 포트폴리오 관련 키워드
        self.portfolio_keywords = [
            "포트폴리오", "추천", "종목", "투자", "매수", "매도", "비중", 
            "분산", "자산배분", "리밸런싱", "수익률", "위험", "배당",
            "코스피", "코스닥", "kospi", "kosdaq", "주식"
        ]
        
        # 재무제표 관련 키워드  
        self.financial_keywords = [
            "재무제표", "재무", "매출", "영업이익", "당기순이익", "부채비율", "ROE", "ROA",
            "PER", "PBR", "EPS", "재무분석", "실적", "손익계산서", "대차대조표",
            "비교", "분석", "실적비교", "재무비교", "vs", "대비", "알려달라", "제공해줘",
            "보여줘", "알려줘", "분석해줘", "어때", "어떤지"
        ]
        
        # 시장 분석 키워드
        self.market_keywords = [
            "시장분석", "업종", "섹터", "코스피", "코스닥", "증시", "주식시장",
            "트렌드", "전망", "뉴스", "호재", "악재"
        ]
        
        # 기본 대화 키워드 (기술적 분석 불필요)
        self.basic_keywords = [
            "안녕", "안녕하세요", "hello", "hi", "반가워", "감사", "고마워",
            "괜찮", "좋아", "나쁘", "미안", "죄송", "어떻게", "뭐야", "뭔가요"
        ]
    
    def analyze_intent(self, message: str) -> Dict[str, Any]:
        """메시지 의도 분석"""
        message_lower = message.lower().strip()
        
        # 점수 계산
        portfolio_score = self._calculate_keyword_score(message_lower, self.portfolio_keywords)
        financial_score = self._calculate_keyword_score(message_lower, self.financial_keywords) 
        market_score = self._calculate_keyword_score(message_lower, self.market_keywords)
        basic_score = self._calculate_keyword_score(message_lower, self.basic_keywords)
        
        # 기업명이 포함된 경우 재무제표 분석 가능성 높임
        company_keywords = ["삼성전자", "삼성", "sk하이닉스", "하이닉스", "네이버", "현대차", "lg화학", "셀트리온"]
        has_company = any(company in message_lower for company in company_keywords)
        if has_company and any(fin_keyword in message_lower for fin_keyword in ["재무", "실적", "분석"]):
            financial_score += 50  # 기업명 + 재무 키워드 조합에 높은 점수
        
        # 메시지 길이 고려 (긴 메시지일수록 기술적 분석 가능성 높음)
        length_factor = min(len(message) / 50, 2.0)  # 최대 2배
        
        # 질문 형태 확인
        is_question = any(q in message_lower for q in ["?", "？", "어떻", "뭐", "언제", "어디", "왜", "어떡", "알려달라", "제공해줘"])
        
        # 의도 결정
        intent_scores = {
            "portfolio": portfolio_score * length_factor,
            "financial": financial_score * length_factor, 
            "market": market_score * length_factor,
            "basic": basic_score + (2 if len(message) < 20 else 0)  # 짧은 메시지는 기본 대화 가능성 높음
        }
        
        max_score = max(intent_scores.values())
        primary_intent = max(intent_scores, key=intent_scores.get)
        
        # 임계값 설정 (재무제표 요청의 경우 더 낮은 임계값 사용)
        confidence = max_score / 10.0 if max_score > 0 else 0
        
        return {
            "primary_intent": primary_intent,
            "confidence": confidence,
            "scores": intent_scores,
            "is_question": is_question,
            "needs_technical_analysis": confidence > 0.2 and primary_intent != "basic",  # 임계값 낮춤
            "message_length": len(message)
        }
    
    def _calculate_keyword_score(self, message: str, keywords: List[str]) -> float:
        """키워드 점수 계산"""
        score = 0
        for keyword in keywords:
            if keyword in message:
                # 키워드 길이에 따른 가중치 (긴 키워드일수록 높은 점수)
                score += len(keyword) * 2
        return score

# 전역 인스턴스
intent_analyzer = MessageIntentAnalyzer()

async def chat_with_agent(message: str, user_profile: Optional[Dict] = None) -> Dict[str, Any]:
    """개선된 채팅 인터페이스 - 메시지 의도에 따른 분기 처리"""
    
    try:
        # 1. 메시지 의도 분석
        intent_analysis = intent_analyzer.analyze_intent(message)
        
        logger.info(f"🎯 메시지 의도 분석: {intent_analysis['primary_intent']} "
                   f"(신뢰도: {intent_analysis['confidence']:.2f})")
        
        # 2. 의도에 따른 처리 분기
        if not intent_analysis["needs_technical_analysis"]:
            # 기본 대화 - HyperCLOVA만 사용
            return await _handle_basic_conversation(message, user_profile, intent_analysis)
        
        elif intent_analysis["primary_intent"] == "portfolio":
            # 포트폴리오 분석 필요
            return await _handle_portfolio_request(message, user_profile)
            
        elif intent_analysis["primary_intent"] == "financial":
            # 재무제표 분석 필요
            return await _handle_financial_request(message, user_profile)
            
        elif intent_analysis["primary_intent"] == "market":
            # 시장 분석 필요
            return await _handle_market_request(message, user_profile)
            
        else:
            # 애매한 경우 기본 대화로 처리
            return await _handle_basic_conversation(message, user_profile, intent_analysis)
            
    except Exception as e:
        logger.error(f"채팅 처리 중 오류: {e}")
        return {
            "message": "죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요.",
            "data_source": "Error handling"
        }

async def _handle_basic_conversation(
    message: str, 
    user_profile: Optional[Dict], 
    intent_analysis: Dict
) -> Dict[str, Any]:
    """기본 대화 처리 (HyperCLOVA만 사용)"""
    
    logger.info(f"💬 기본 대화 모드로 처리")
    
    # 사용자 프로필이 있으면 맥락에 포함
    context_info = ""
    if user_profile:
        age = user_profile.get("age", "")
        experience = user_profile.get("experience_level", "")
        risk = user_profile.get("risk_tolerance", "")
        
        context_info = f"""
사용자 정보: {age}세, 투자경험 {experience}, 위험성향 {risk}
이 정보를 참고하되, 구체적인 투자 분석이 아닌 일반적인 대화로 응답하세요.
"""
    
    # HyperCLOVA 프롬프트 구성
    prompt = f"""
사용자 메시지: "{message}"

{context_info}

당신은 친근한 투자 상담 AI입니다. 사용자의 메시지에 자연스럽게 응답하세요.

다음 상황에 맞게 응답해주세요:
- 인사말이면 친근하게 인사하고 도움을 제공할 수 있음을 안내
- 간단한 질문이면 일반적인 정보 제공
- 투자 관련 기초 질문이면 교육적인 설명
- 구체적인 포트폴리오나 종목 분석은 별도로 요청하도록 안내

투자에는 위험이 따른다는 점을 적절히 언급하고, 따뜻하고 도움이 되는 톤으로 응답하세요.
"""
    
    try:
        response = await get_hyperclova_response(prompt)
        
        return {
            "message": response,
            "intent_analysis": intent_analysis,
            "data_source": "HyperCLOVA basic conversation"
        }
        
    except Exception as e:
        logger.error(f"기본 대화 처리 실패: {e}")
        
        # 폴백 응답
        fallback_messages = {
            "안녕": "안녕하세요! 투자 상담 AI입니다. 포트폴리오 추천, 종목 분석, 투자 상담 등을 도와드릴 수 있어요. 무엇을 도와드릴까요?",
            "감사": "천만에요! 더 궁금한 것이 있으시면 언제든 말씀해주세요.",
            "default": "안녕하세요! 저는 투자 상담을 도와드리는 AI입니다. 포트폴리오 추천이나 투자 관련 질문이 있으시면 말씀해주세요."
        }
        
        # 키워드 매칭으로 적절한 폴백 선택
        for keyword, response in fallback_messages.items():
            if keyword != "default" and keyword in message.lower():
                return {"message": response, "data_source": "Fallback response"}
        
        return {"message": fallback_messages["default"], "data_source": "Fallback response"}

async def _handle_portfolio_request(message: str, user_profile: Dict) -> Dict[str, Any]:
    """포트폴리오 요청 처리"""
    
    logger.info(f"📊 포트폴리오 분석 모드로 처리")
    logger.info(f"🎯 사용자 요청: {message}")
    
    if not user_profile:
        return {
            "message": "포트폴리오 추천을 위해서는 투자자 정보가 필요합니다. 나이, 투자 가능 금액, 위험 성향 등을 알려주세요.",
            "data_source": "Portfolio request without profile"
        }
    
    try:
        # PortfolioInput 생성
        portfolio_input = PortfolioInput(
            initial_capital=user_profile.get("investment_amount", 1000) * 10000,
            risk_appetite=user_profile.get("risk_tolerance", "중립형"),
            experience_level=user_profile.get("experience_level", "초보"),
            age=user_profile.get("age", 35),
            original_message=message  # 원본 메시지 전달
        )
        
        from app.services.stock_database import stock_database
        result = await analyze_portfolio(portfolio_input, stock_database, original_message=message)
        
        # 종목 추천 형태로 변환
        recommendations = []
        weights = result.get("portfolio_details", {}).get("weights", {})
        
        for ticker, data in weights.items():
            recommendations.append({
                "ticker": ticker,
                "name": data.get("name", ticker),
                "target_weight": data.get("weight", 0),
                "reason": "PostgreSQL yfinance 데이터 기반 AI 포트폴리오 최적화 결과",
                "sector": data.get("sector", "기타"),
                "market": data.get("market", "Unknown"),
                "risk_level": "보통"
            })
        
        # 시장 필터 정보 추가
        market_filter = result.get("market_filter", "auto")
        market_info = ""
        if market_filter == "kospi_only":
            market_info = "코스피 종목으로만 구성된 "
        elif market_filter == "kosdaq_only":
            market_info = "코스닥 종목으로만 구성된 "
        
        return {
            "recommendations": recommendations,
            "explanation": result.get("explanation", ""),
            "message": f"PostgreSQL 기반 {market_info}포트폴리오 추천이 완료되었습니다.",
            "data_source": "PostgreSQL yfinance data",
            "portfolio_analysis": result.get("portfolio_details", {})
        }
        
    except Exception as e:
        logger.error(f"종목 추천 생성 실패: {e}")
        return {
            "recommendations": [],
            "error": str(e),
            "message": "추천 생성 중 오류가 발생했습니다.",
            "data_source": "PostgreSQL yfinance data"
        }


# ========================================================================
# 추가 API 호환성을 위한 누락된 함수들
# ========================================================================

async def get_single_portfolio_analysis(
    user_input: PortfolioInput, 
    db: StockDatabase, 
    optimization_mode: OptimizationMode
) -> Dict[str, Any]:
    """단일 포트폴리오 분석 (특정 최적화 방식) - PostgreSQL 기반"""
    
    # optimization_mode를 user_input에 설정하고 분석 실행
    user_input.optimization_mode = optimization_mode
    user_input.analysis_type = AnalysisType.SINGLE
    
    return await analyze_portfolio(user_input, db)

async def get_comparison_portfolio_analysis(
    user_input: PortfolioInput, 
    db: StockDatabase
) -> Dict[str, Any]:
    """비교 포트폴리오 분석 - PostgreSQL 기반"""
    
    user_input.analysis_type = AnalysisType.COMPARISON
    
    # 원본 메시지가 있으면 전달
    original_message = getattr(user_input, 'original_message', '')
    # 비교 분석은 현재 단일 분석으로 대체 (추후 확장 가능)
    result = await analyze_portfolio(user_input, db, force_comparison=True, original_message=original_message)
    
    # 비교 분석 형태로 결과 구성
    if "error" not in result:
        result["comparison_results"] = {
            "recommended": result.get("portfolio_details", {}),
        }
        result["recommendation"] = "PostgreSQL 데이터 기반으로 최적화된 포트폴리오입니다."
    
    return result

async def get_recommended_portfolio_analysis(
    user_input: PortfolioInput, 
    db: StockDatabase
) -> Dict[str, Any]:
    """추천 포트폴리오 분석 (AI 자동 결정) - PostgreSQL 기반"""
    
    user_input.analysis_type = AnalysisType.RECOMMENDED
    
    # 원본 메시지가 있으면 전달
    original_message = getattr(user_input, 'original_message', '')
    return await analyze_portfolio(user_input, db, original_message=original_message)


# ========================================================================
# 시장 분석 및 뉴스 분석 함수들 (main.py 호환성)
# ========================================================================

async def analyze_market_trends(
    sector: str = None, 
    time_period: str = "3M"
) -> Dict[str, Any]:
    """시장 트렌드 분석"""
    
    logger.info(f"📈 시장 트렌드 분석: {sector or '전체시장'} ({time_period})")
    
    try:
        # 기본 시장 분석 프롬프트
        if sector:
            prompt = f"""
{sector} 업종의 최근 {time_period} 시장 트렌드를 분석해주세요.

다음 내용을 포함해서 분석해주세요:
1. 업종 현황 및 주요 이슈
2. 성장 동력과 리스크 요인
3. 대표 기업들과 주가 동향
4. 향후 투자 전망

전문적이고 객관적인 분석을 제공해주세요.
"""
        else:
            prompt = f"""
최근 {time_period} 한국 주식시장(KOSPI/KOSDAQ) 전반의 트렌드를 분석해주세요.

다음 내용을 포함해서 분석해주세요:
1. 시장 지수 동향
2. 주요 섹터별 성과
3. 외국인/기관 투자 동향  
4. 주요 이슈 및 향후 전망

시장 데이터와 함께 전문적인 분석을 제공해주세요.
"""
        
        analysis = await get_hyperclova_response(prompt)
        
        return {
            "analysis_summary": analysis,
            "target_sector": sector,
            "time_period": time_period,
            "current_trend": "분석 완료",
            "key_metrics": {"status": "정상"},
            "recommendations": ["정기적인 시장 모니터링", "분산투자 유지"],
            "outlook": "시장 상황에 따른 신중한 투자 접근 권장",
            "data_source": "시장 트렌드 분석"
        }
        
    except Exception as e:
        logger.error(f"시장 트렌드 분석 실패: {e}")
        return {
            "analysis_summary": "시장 트렌드 분석 중 오류가 발생했습니다.",
            "error": str(e)
        }

async def analyze_stock_financials(
    ticker: str,
    user_question: str = None
) -> Dict[str, Any]:
    """개별 종목 재무 분석"""
    
    logger.info(f"💰 재무 분석: {ticker}")
    
    try:
        from app.services.stock_database import stock_database
        
        # 재무 데이터 조회
        financial_data = stock_database.get_financials(ticker)
        company_info = stock_database.get_company_info(ticker)
        valuation_metrics = stock_database.get_valuation_metrics(ticker)
        
        # AI 분석 생성
        prompt = f"""
종목 코드: {ticker}
회사명: {company_info.get('company_name', ticker)}
업종: {company_info.get('sector', '기타')}

재무 데이터:
- 매출액: {financial_data.get('revenue', 0):,}원
- 영업이익: {financial_data.get('operating_profit', 0):,}원  
- 당기순이익: {financial_data.get('net_profit', 0):,}원
- ROE: {financial_data.get('ROE', 0):.1f}%
- 부채비율: {financial_data.get('DebtRatio', 0):.1f}%

밸류에이션:
- PER: {valuation_metrics.get('PER', 0):.1f}
- PBR: {valuation_metrics.get('PBR', 0):.1f}

사용자 질문: {user_question or "이 회사의 재무 상태를 분석해주세요"}

위 재무 데이터를 바탕으로 다음을 분석해주세요:
1. 재무 건전성 평가
2. 수익성 및 성장성 분석
3. 밸류에이션 적정성
4. 투자 관점에서의 강점과 약점
5. 투자 의견 및 주의사항

전문적이고 객관적인 분석을 제공해주세요.
"""
        
        analysis = await get_hyperclova_response(prompt)
        
        # 재무 지표 구성
        financial_metrics = [
            {
                "metric_name": "매출액",
                "current_value": financial_data.get('revenue', 0),
                "evaluation": "양호" if financial_data.get('revenue', 0) > 100000000 else "보통",
                "explanation": "기업의 사업 규모를 나타내는 지표"
            },
            {
                "metric_name": "ROE",
                "current_value": financial_data.get('ROE', 0),
                "evaluation": "좋음" if financial_data.get('ROE', 0) > 15 else "보통",
                "explanation": "자기자본 대비 순이익 비율"
            },
            {
                "metric_name": "PER",
                "current_value": valuation_metrics.get('PER', 0),
                "evaluation": "적정" if 5 < valuation_metrics.get('PER', 0) < 20 else "주의",
                "explanation": "주가 대비 주당순이익 배수"
            }
        ]
        
        return {
            "ticker": ticker,
            "company_name": company_info.get('company_name', ticker),
            "analysis_summary": analysis,
            "financial_metrics": financial_metrics,
            "strengths": ["PostgreSQL 데이터 기반 정확한 분석"],
            "weaknesses": ["시장 변동성 존재"],
            "investment_rating": "참고용",
            "target_price": None,
            "data_source": "PostgreSQL financial data"
        }
        
    except Exception as e:
        logger.error(f"재무 분석 실패 {ticker}: {e}")
        return {
            "ticker": ticker,
            "company_name": f"종목 {ticker}",
            "analysis_summary": "재무 분석 중 오류가 발생했습니다.",
            "error": str(e)
        }

async def analyze_news_sentiment(
    ticker: str = None,
    days: int = 7
) -> Dict[str, Any]:
    """뉴스 감성 분석 (모의 버전)"""
    
    logger.info(f"📰 뉴스 감성 분석: {ticker or '전체시장'} ({days}일)")
    
    try:
        # 모의 뉴스 분석 결과
        if ticker:
            company_info = {}
            try:
                from app.services.stock_database import stock_database
                company_info = stock_database.get_company_info(ticker)
            except:
                pass
            
            company_name = company_info.get('company_name', ticker)
            
            prompt = f"""
{company_name} ({ticker}) 종목에 대한 최근 {days}일간의 뉴스 동향을 분석해주세요.

일반적인 시장 상황과 해당 업종의 트렌드를 고려하여 다음을 분석해주세요:
1. 주요 호재 및 악재 요인
2. 시장 반응 및 주가 영향
3. 향후 주목해야 할 포인트
4. 투자자 관점에서의 시사점

객관적이고 균형잡힌 분석을 제공해주세요.
"""
        else:
            prompt = f"""
최근 {days}일간 한국 주식시장의 주요 뉴스와 이슈를 분석해주세요.

다음을 포함해서 분석해주세요:
1. 주요 시장 이슈 및 뉴스
2. 섹터별 호재/악재 동향
3. 투자 심리 및 시장 분위기
4. 향후 주목해야 할 이벤트

시장 전반에 대한 객관적인 분석을 제공해주세요.
"""
        
        analysis = await get_hyperclova_response(prompt)
        
        return {
            "ticker": ticker,
            "analysis_period": f"최근 {days}일",
            "total_articles": 10,  # 모의 값
            "investment_impact": {
                "overall_sentiment": "중립",
                "confidence": 0.7,
                "positive_count": 5,
                "negative_count": 3,
                "neutral_count": 2
            },
            "ai_summary": analysis,
            "market_signals": [
                {
                    "signal_type": "중립적 흐름",
                    "impact_score": 0,
                    "description": "전반적으로 안정적인 뉴스 흐름"
                }
            ],
            "data_source": "뉴스 감성 분석 (모의)"
        }
        
    except Exception as e:
        logger.error(f"뉴스 분석 실패: {e}")
        return {
            "analysis_summary": "뉴스 분석 중 오류가 발생했습니다.",
            "error": str(e)
        }


# ========================================================================
# 기타 유틸리티 함수들
# ========================================================================

def extract_tickers_from_message(message: str) -> List[str]:
    """메시지에서 종목 코드 추출"""
    import re
    
    # 6자리 숫자 패턴 (한국 종목 코드)
    ticker_pattern = r'\b\d{6}\b'
    tickers = re.findall(ticker_pattern, message)
    
    # 회사명 매핑 (추가 가능)
    company_map = {
        "삼성전자": "005930",
        "sk하이닉스": "000660", 
        "네이버": "035420",
        "현대차": "005380",
        "lg화학": "051910"
    }
    
    message_lower = message.lower()
    for company, ticker in company_map.items():
        if company in message_lower:
            tickers.append(ticker)
    
    return list(set(tickers))  # 중복 제거

def determine_user_intent_simple(message: str) -> str:
    """간단한 의도 파악 (기존 시스템 호환용)"""
    intent_analysis = intent_analyzer.analyze_intent(message)
    return intent_analysis["primary_intent"]


# ========================================================================
# 시스템 테스트 함수
# ========================================================================

async def test_ai_agent_system():
    """AI 에이전트 시스템 테스트"""
    
    test_cases = [
        {
            "message": "안녕하세요",
            "expected_intent": "basic",
            "user_profile": {"age": 30}
        },
        {
            "message": "월 100만원 투자 추천해주세요",
            "expected_intent": "portfolio",
            "user_profile": {"age": 30, "investment_amount": 100, "risk_tolerance": "중립형"}
        },
        {
            "message": "삼성전자 재무제표 분석해주세요",
            "expected_intent": "financial",
            "user_profile": None
        }
    ]
    
    print("🧪 AI 에이전트 시스템 테스트")
    print("=" * 50)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. 테스트: {case['message']}")
        
        try:
            # 의도 분석 테스트
            intent_analysis = intent_analyzer.analyze_intent(case['message'])
            detected_intent = intent_analysis['primary_intent']
            
            print(f"   예상 의도: {case['expected_intent']}")
            print(f"   감지 의도: {detected_intent}")
            print(f"   신뢰도: {intent_analysis['confidence']:.2f}")
            
            # 실제 처리 테스트
            result = await chat_with_agent(case['message'], case['user_profile'])
            print(f"   응답 길이: {len(result.get('message', ''))}자")
            print(f"   데이터 소스: {result.get('data_source', 'N/A')}")
            
            if detected_intent == case['expected_intent']:
                print("   ✅ 의도 분석 성공")
            else:
                print("   ⚠️ 의도 분석 차이")
                
        except Exception as e:
            print(f"   ❌ 테스트 실패: {e}")
    
    print("\n🎯 테스트 완료")



async def _handle_financial_request(message: str, user_profile: Optional[Dict]) -> Dict[str, Any]:
    """재무제표 분석 요청 처리"""
    
    logger.info(f"💰 재무제표 분석 모드로 처리")
    
    # 종목 코드 추출
    ticker_pattern = r'\b\d{6}\b'
    tickers = re.findall(ticker_pattern, message)
    
    if not tickers:
        # DB에서 동적으로 회사명 검색
        tickers = await _extract_tickers_from_company_names(message)
    
    try:
        from app.services.stock_database import stock_database
        
        if len(tickers) > 1:
            # 여러 종목 비교
            comparison_data = await stock_database.compare_financials(tickers)
            
            # 데이터 가용성 확인
            if not comparison_data or "데이터가 없습니다" in str(comparison_data):
                # 실제 기업명 찾기
                company_names = []
                for ticker in tickers:
                    company_info = stock_database.get_company_info(ticker)
                    company_names.append(company_info.get('company_name', ticker))
                
                return {
                    "message": f"""죄송합니다. {', '.join(company_names)} 중 일부 기업의 재무 데이터가 현재 데이터베이스에 없습니다.

**현재 상황:**
- 재무데이터 수집이 진행 중입니다 (DART API 활용)
- 곧 더 많은 기업의 재무제표를 이용할 수 있을 예정입니다

**당장 이용 가능한 방법:**
1. 🏢 각 기업의 공식 IR 페이지 방문
2. 📊 금융감독원 전자공시시스템(DART) 활용
3. 🔍 증권사 리서치 보고서 참고
4. 📈 네이버금융, 인베스팅닷컴 등 금융정보 사이트 이용

시스템 개선 중이니 잠시 후 다시 시도해주세요.""",
                    "data_source": "Limited data availability"
                }
            
            prompt = f"""
재무제표 비교 분석 요청입니다.

비교 대상 종목들의 재무 데이터:
{comparison_data}

사용자 질문: "{message}"

위 데이터를 바탕으로 각 기업의 재무 상태를 비교 분석해주세요.
매출액, 영업이익, 순이익 등의 지표를 비교하고,
각 기업의 재무 건전성과 성장성을 평가해주세요.
"""
            
        elif tickers:
            # 단일 종목 분석
            ticker = tickers[0]
            financial_data = stock_database.get_financials(ticker)
            company_info = stock_database.get_company_info(ticker)
            
            # 데이터가 없거나 비어있는 경우 즉시 응답
            if not financial_data or not any(financial_data.values()):
                company_name = company_info.get('company_name', ticker) if company_info else ticker
                return {
                    "message": f"""죄송합니다. {company_name}({ticker})의 재무 데이터가 현재 데이터베이스에 없습니다.

**현재 상황:**
- 재무데이터 수집이 진행 중입니다 (DART API 활용)
- 곧 더 많은 기업의 재무제표를 이용할 수 있을 예정입니다

**당장 이용 가능한 방법:**
1. 🏢 {company_name} 공식 IR 페이지 방문
2. 📊 금융감독원 전자공시시스템(DART)에서 '{company_name}' 검색
3. 🔍 증권사 리서치 보고서 참고
4. 📈 네이버금융, 인베스팅닷컴 등에서 '{ticker}' 검색

시스템 개선 중이니 잠시 후 다시 시도해주세요.""",
                    "data_source": "Limited data availability"
                }
            
            # 연도별 재무 데이터 수집
            multi_year_data = stock_database.get_multi_year_financials(ticker)
            
            if not multi_year_data:
                # 폴백: 단일 년도 데이터
                revenue = financial_data.get('revenue', 0)
                operating_profit = financial_data.get('operating_profit', 0) 
                net_profit = financial_data.get('net_profit', 0)
                roe = financial_data.get('ROE', 0)
                latest_year = financial_data.get('latest_year', 2023)
                
                multi_year_summary = f"**{latest_year}년 단일 데이터**\n- 매출액: {revenue:,.0f}원 ({revenue/1000000000000:.1f}조원)"
            else:
                # 연도별 데이터 포맷팅 (최신순)
                multi_year_summary = "**연도별 재무 성과 추이 (최신 3개년)**\n"
                for i, year_data in enumerate(multi_year_data):
                    year = year_data['year']
                    rev = year_data['revenue']
                    op = year_data['operating_profit'] 
                    net = year_data['net_profit']
                    
                    # 전년 대비 증감률 계산
                    growth_info = ""
                    if i < len(multi_year_data) - 1:
                        prev_year_data = multi_year_data[i + 1]
                        revenue_growth = ((rev - prev_year_data['revenue']) / prev_year_data['revenue']) * 100
                        growth_info = f" (매출 전년대비 {revenue_growth:+.1f}%)"
                    
                    multi_year_summary += f"- **{year}년**: 매출 {rev/1000000000000:.1f}조원, 영업이익 {op/1000000000000:.1f}조원, 순이익 {net/1000000000000:.1f}조원{growth_info}\n"
                
                # 최신 년도 데이터를 기본값으로 사용
                latest_data = multi_year_data[0]  # 첫 번째가 최신
                revenue = latest_data['revenue']
                operating_profit = latest_data['operating_profit']
                net_profit = latest_data['net_profit']
                roe = (net_profit / revenue * 100) if revenue > 0 else 0
                latest_year = latest_data['year']
            
            prompt = f"""
**{company_info.get('company_name', f'종목 {ticker}')}({ticker}) 재무제표 분석**

## 기업 개요
- 종목: {company_info.get('company_name', f'종목 {ticker}')} ({ticker})
- 섹터: {company_info.get('sector', '기타')}

## 📊 연도별 재무 데이터
{multi_year_summary}

## 📈 최신 재무 지표 ({latest_year}년 기준)
- **매출액**: {revenue:,.0f}원 ({revenue/1000000000000:.1f}조원)
- **영업이익**: {operating_profit:,.0f}원 ({operating_profit/1000000000000:.1f}조원)
- **당기순이익**: {net_profit:,.0f}원 ({net_profit/1000000000000:.1f}조원)
- **ROE (자기자본이익률)**: {roe:.1f}%
- **영업이익률**: {(operating_profit/revenue*100):.1f}% (영업이익/매출액)

## 📈 분석 요청
사용자 질문: "{message}"

위의 **연도별 실제 재무 데이터**를 바탕으로 {company_info.get('company_name', f'종목 {ticker}')}의 재무 상태를 구체적으로 분석해주세요:

1. **연도별 트렌드 분석**: 제시된 3개년(2021-2023) 매출과 이익의 변화 패턴
2. **수익성 분석**: 최신 매출액 {revenue/1000000000000:.1f}조원, 영업이익 {operating_profit/1000000000000:.1f}조원의 의미
3. **효율성 분석**: ROE {roe:.1f}%와 영업이익률 {(operating_profit/revenue*100):.1f}%의 해석
4. **성장성 평가**: 연도별 성장률과 미래 전망
5. **투자 관점**: 위 수치들을 종합한 투자 의견

**중요사항**:
- 제공된 구체적인 연도별 숫자들을 정확히 인용해주세요
- 2024년 데이터는 수집 중이므로 2021-2023년 3개년 트렌드를 분석해주세요
- 각 연도의 수치를 정확히 구분하여 분석해주세요
"""
            
        else:
            # 일반적인 재무제표 질문
            prompt = f"""
사용자의 재무제표 관련 질문: "{message}"

재무제표 분석의 일반적인 방법론과 주요 지표 해석 방법을 설명해주세요.
"""
        
        analysis = await get_hyperclova_response(prompt)
        
        return {
            "message": analysis,
            "data_source": "PostgreSQL financial data"
        }
        
    except Exception as e:
        logger.error(f"재무제표 분석 실패: {e}")
        return {
            "message": "재무제표 분석 중 오류가 발생했습니다.",
            "data_source": "Error"
        }

async def _handle_market_request(message: str, user_profile: Optional[Dict]) -> Dict[str, Any]:
    """시장 분석 요청 처리"""
    
    logger.info(f"📈 시장 분석 모드로 처리")
    
    # 업종/섹터 키워드 추출
    sector_keywords = {
        "반도체": ["반도체", "메모리", "반도체주"],
        "바이오": ["바이오", "제약", "의료"],
        "게임": ["게임", "엔터테인먼트"],
        "금융": ["은행", "증권", "금융"],
        "자동차": ["자동차", "전기차"],
        "IT": ["IT", "인터넷", "플랫폼"]
    }
    
    detected_sector = None
    for sector, keywords in sector_keywords.items():
        if any(keyword in message.lower() for keyword in keywords):
            detected_sector = sector
            break
    
    try:
        # 시장 분석 프롬프트
        if detected_sector:
            prompt = f"""
사용자 질문: "{message}"
관심 섹터: {detected_sector}

{detected_sector} 업종의 시장 동향과 투자 전망에 대해 전문적으로 분석해주세요.
다음 내용을 포함해주세요:
1. 업종 현황 및 트렌드
2. 주요 성장 동력과 리스크 요인
3. 대표 기업들과 투자 포인트
4. 향후 전망

투자에는 위험이 따른다는 점을 반드시 언급해주세요.
"""
        else:
            prompt = f"""
사용자의 시장 분석 질문: "{message}"

전체 주식시장 또는 특정 시장에 대한 전문적인 분석을 제공해주세요.
최근 시장 동향, 주요 이슈, 투자 관점에서의 시사점 등을 포함해서 답변해주세요.
"""
        
        analysis = await get_hyperclova_response(prompt)
        
        return {
            "message": analysis,
            "detected_sector": detected_sector,
            "data_source": "Market analysis"
        }
        
    except Exception as e:
        logger.error(f"시장 분석 실패: {e}")
        return {
            "message": "시장 분석 중 오류가 발생했습니다. 다시 시도해주세요.",
            "data_source": "Market analysis error"
        }

# 기존 함수들 (하위 호환성 유지)
async def analyze_portfolio(
    user_input: PortfolioInput, 
    db: StockDatabase,
    force_comparison: bool = False,
    original_message: str = ""
) -> Dict[str, Any]:
    """PostgreSQL 데이터 기반 포트폴리오 분석"""
    try:
        # 원본 메시지를 user_input에 저장
        user_input.original_message = original_message
        
        logger.info(f"🎯 사용자 요청: {original_message}")
        logger.info(f"💰 투자 금액: {user_input.initial_capital:,}원")
        logger.info(f"📊 위험 성향: {user_input.risk_appetite}")
        
        # PostgreSQL 기반 스마트 포트폴리오 생성
        portfolio_details = create_smart_portfolio(user_input, db, original_message)
        
        if "error" in portfolio_details:
            logger.error(f"포트폴리오 생성 실패: {portfolio_details['error']}")
            return {
                "user_profile": user_input.dict(),
                "explanation": f"죄송합니다. 포트폴리오 구성 중 문제가 발생했습니다.\n\n{portfolio_details['error']}",
                "data_source": "PostgreSQL"
            }
        
        # 시장 필터 정보 추가
        market_filter = portfolio_details.get("market_filter", "auto")
        market_dist = portfolio_details.get("portfolio_stats", {}).get("market_distribution", {})
        
        # AI 설명 생성을 위한 프롬프트
        prompt = _create_postgresql_based_prompt(user_input, portfolio_details, original_message, market_filter)
        
        # HyperCLOVA를 통한 설명 생성
        explanation = await get_hyperclova_response(prompt)
        
        # 최종 결과
        result = {
            "user_profile": user_input.dict(),
            "portfolio_details": portfolio_details,
            "explanation": explanation,
            "analysis_method": "PostgreSQL real-time data + AI optimization",
            "market_filter": market_filter,
            "data_stats": {
                "total_stocks_analyzed": portfolio_details.get("selected_tickers_count", 0),
                "kospi_stocks": market_dist.get("KOSPI", 0),
                "kosdaq_stocks": market_dist.get("KOSDAQ", 0)
            }
        }
        
        logger.info(f"✅ 포트폴리오 분석 완료: {portfolio_details.get('selected_tickers_count', 0)}개 종목 분석")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 포트폴리오 분석 중 오류: {e}", exc_info=True)
        return {
            "error": "포트폴리오 분석 중 오류가 발생했습니다.",
            "detail": str(e),
            "data_source": "PostgreSQL"
        }

def _create_postgresql_based_prompt(
    user_input: PortfolioInput, 
    portfolio_details: Dict[str, Any],
    original_message: str,
    market_filter: str
) -> str:
    """PostgreSQL 데이터 기반 설명 프롬프트"""
    
    weights = portfolio_details.get("weights", {})
    market_dist = portfolio_details.get("portfolio_stats", {}).get("market_distribution", {})
    
    # 시장 분석 설명
    if market_filter == "kospi_only":
        market_analysis = "고객님께서 코스피 종목을 요청하셔서 코스피 상장 기업들로만 포트폴리오를 구성했습니다."
    elif market_filter == "kosdaq_only":
        market_analysis = "고객님께서 코스닥 종목을 요청하셔서 코스닥 상장 성장주들로 포트폴리오를 구성했습니다."
    else:
        market_analysis = f"AI가 최적의 분산을 위해 코스피 {market_dist.get('KOSPI', 0)}개, 코스닥 {market_dist.get('KOSDAQ', 0)}개 종목을 선별했습니다."
    
    # 포트폴리오 구성 설명 (재무데이터 포함)
    portfolio_composition = ""
    if weights:
        portfolio_composition = "\n**📊 선별된 종목 구성 및 재무 현황:**\n"
        for ticker, data in weights.items():
            company_name = data.get("name", ticker)
            weight = data.get("weight", 0)
            sector = data.get("sector", "기타")
            market = data.get("market", "Unknown")
            revenue = data.get("revenue")
            
            # 종목 코드에서 .KS/.KQ 제거
            clean_ticker = ticker.replace('.KS', '').replace('.KQ', '')
            
            portfolio_composition += f"- **{company_name} ({clean_ticker})**: {weight:.1%} - {sector} ({market})\n"
            
            # 실제 재무데이터 조회 및 추가
            try:
                from app.services.stock_database import stock_database
                financial_data = stock_database.get_multi_year_financials(clean_ticker)
                if financial_data and len(financial_data) > 0:
                    latest_data = financial_data[0]  # 최신년도 데이터
                    revenue = latest_data.get('revenue', 0)
                    op_profit = latest_data.get('operating_profit', 0)
                    net_profit = latest_data.get('net_profit', 0)
                    year = latest_data.get('year', 0)
                    
                    portfolio_composition += f"  - {year}년 매출: {revenue/1000000000000:.1f}조원, 영업이익: {op_profit/1000000000000:.1f}조원, 순이익: {net_profit/1000000000000:.1f}조원\n"
                else:
                    if revenue:
                        portfolio_composition += f"  - 추정 매출: {revenue/1000000000000:.1f}조원\n"
            except Exception as e:
                if revenue:
                    portfolio_composition += f"  - 추정 매출: {revenue/1000000000000:.1f}조원\n"
    
    # 섹터 분포
    sector_dist = portfolio_details.get("portfolio_stats", {}).get("sector_distribution", {})
    sector_info = "섹터별 비중: " + ", ".join([f"{s} {w:.1%}" for s, w in sector_dist.items()])
    
    prompt = f"""
# PostgreSQL 실시간 데이터 기반 포트폴리오 분석

## 🎯 고객 요청 분석
**원본 요청**: "{original_message}"
{market_analysis}

## 📈 데이터 분석 결과
- 분석 대상: PostgreSQL에 저장된 {portfolio_details.get('selected_tickers_count', 0)}개 한국 상장 종목
- 데이터 소스: 실시간 주가 데이터 및 재무제표 (prices_merged, financials 테이블)
- 선별 기준: 최근 30일 가격 데이터 존재, 재무 데이터 완전성

{portfolio_composition}

## 📊 포트폴리오 성과 지표
- 예상 연수익률: {portfolio_details.get('performance', {}).get('expected_annual_return', 0):.1%}
- 연변동성: {portfolio_details.get('performance', {}).get('annual_volatility', 0):.1%}
- 샤프비율: {portfolio_details.get('performance', {}).get('sharpe_ratio', 0):.3f}
- {sector_info}

## 💼 투자자 프로필
- 나이: {user_input.age}세
- 투자 금액: {user_input.initial_capital / 10000:,.0f}만원
- 위험 성향: {user_input.risk_appetite}
- 투자 경험: {getattr(user_input, 'experience_level', '초보')}

위의 **PostgreSQL 실시간 데이터**를 바탕으로 다음을 포함해 상세히 설명하세요:

1. 고객의 시장 선호도(코스피/코스닥)를 어떻게 반영했는지
2. 각 종목이 선정된 구체적 이유 (재무 데이터 기반)
3. 섹터 분산과 리스크 관리 전략
4. 투자 실행 방법과 주의사항

반드시 "이상으로 PostgreSQL 실시간 데이터 기반 포트폴리오 분석을 마치겠습니다."로 마무리하세요.
"""
    
    return prompt

# 나머지 기존 함수들도 동일하게 유지...
async def get_single_portfolio_analysis(
    user_input: PortfolioInput, 
    db: StockDatabase, 
    optimization_mode: OptimizationMode
) -> Dict[str, Any]:
    user_input.optimization_mode = optimization_mode
    user_input.analysis_type = AnalysisType.SINGLE
    return await analyze_portfolio(user_input, db)

async def get_comparison_portfolio_analysis(
    user_input: PortfolioInput, 
    db: StockDatabase
) -> Dict[str, Any]:
    user_input.analysis_type = AnalysisType.COMPARISON
    result = await analyze_portfolio(user_input, db, force_comparison=True)
    if "error" not in result:
        result["comparison_results"] = {
            "recommended": result.get("portfolio_details", {}),
        }
        result["recommendation"] = "PostgreSQL 데이터 기반으로 최적화된 포트폴리오입니다."
    return result

async def get_recommended_portfolio_analysis(
    user_input: PortfolioInput, 
    db: StockDatabase
) -> Dict[str, Any]:
    user_input.analysis_type = AnalysisType.RECOMMENDED
    return await analyze_portfolio(user_input, db)

# 904-910줄 부근 올바른 코드

async def get_stock_recommendations(message: str, user_profile: Dict) -> Dict[str, Any]:
    """종목 추천 (기존 호환성 유지)"""
    try:
        portfolio_input = PortfolioInput(
            initial_capital=user_profile.get("investment_amount", 1000) * 10000,
            risk_appetite=user_profile.get("risk_tolerance", "중립형"),
            experience_level=user_profile.get("experience_level", "초보"),
            age=user_profile.get("age", 35),
            analysis_type=AnalysisType.RECOMMENDED
        )
        
        from app.services.stock_database import stock_database
        result = await analyze_portfolio(portfolio_input, stock_database, original_message=message)
        
        # 종목 추천 형태로 변환
        recommendations = []
        weights = result.get("portfolio_details", {}).get("weights", {})
        
        for ticker, data in weights.items():
            recommendations.append({
                "ticker": ticker,
                "name": data.get("name", ticker),
                "target_weight": data.get("weight", 0),
                "reason": "PostgreSQL yfinance 데이터 기반 AI 포트폴리오 최적화 결과",
                "sector": data.get("sector", "기타"),
                "market": data.get("market", "Unknown"),
                "risk_level": "보통"
            })
        
        return {
            "recommendations": recommendations,
            "explanation": result.get("explanation", ""),
            "message": "PostgreSQL 기반 포트폴리오 추천이 완료되었습니다.",
            "data_source": "PostgreSQL yfinance data"
        }
        
    except Exception as e:
        logger.error(f"종목 추천 생성 실패: {e}")
        return {
            "recommendations": [],
            "error": str(e),
            "message": "추천 생성 중 오류가 발생했습니다.",
            "data_source": "PostgreSQL yfinance data"
        }

async def _extract_tickers_from_company_names(message: str) -> List[str]:
    """메시지에서 회사명을 추출하여 DB에서 해당 티커들을 찾기"""
    from utils.db import SessionLocal
    
    tickers = []
    message_lower = message.lower()
    
    session = SessionLocal()
    try:
        # 특정 기업 직접 매핑 (확실한 매칭) - 확대된 목록
        direct_mappings = {
            '삼성전자': '005930',
            '삼성': '005930', 
            'samsung': '005930',
            'sk하이닉스': '000660',
            '하이닉스': '000660', 
            'hynix': '000660',
            '네이버': '035420',
            'naver': '035420',
            '현대차': '005380',
            '현대자동차': '005380',
            'lg화학': '051910',
            '셀트리온': '068270',
            'celltrion': '068270',
            '안랩': '053800',
            'ahnlab': '053800',
            # 추가 매핑
            '에스오일': '010950',
            's-oil': '010950',
            '에코프로비엠': '247540',
            '에코프로': '086520',
            'ecopro': '086520',
            '카카오': '035720',
            'kakao': '035720',
            '카카오게임즈': '293490',
            '포스코': '005490',
            'posco': '005490',
            '기아': '000270',
            'kia': '000270',
            '한국전력': '015760',
            '한전': '015760',
            'kepco': '015760',
            '신한지주': '055550',
            '하나금융': '086790',
            'kb금융': '105560',
            '두산': '000150',
            'doosan': '000150'
        }
        
        # 직접 매핑 먼저 확인
        logger.info(f"🔍 회사명 매핑 시도: '{message_lower}'")
        
        for keyword, ticker in direct_mappings.items():
            if keyword in message_lower:
                logger.info(f"🎯 키워드 매칭: '{keyword}' -> {ticker}")
                
                # 해당 ticker가 DB에 있는지 확인
                result = session.execute(text("""
                    SELECT ticker, corp_name 
                    FROM company_info 
                    WHERE ticker = :ticker
                """), {"ticker": ticker}).fetchone()
                
                if result:
                    tickers.append(result[0])
                    logger.info(f"🎯 직접 매핑: {result[1]} ({result[0]})")
                    return list(set(tickers))  # 중복 제거
                else:
                    logger.warning(f"⚠️ DB에서 {ticker} 찾을 수 없음")
        
        logger.warning(f"🚫 직접 매핑 실패: '{message_lower}'에서 알려진 회사 없음")
        
        # 🔥 DB에서 동적 회사명 검색 (전체 826개 기업 대상)
        logger.info("🔍 DB에서 동적 회사명 검색 시작")
        
        # 메시지에서 키워드 추출 (한글 + 영어)
        import re
        korean_words = re.findall(r'[가-힣]{2,}', message_lower)
        english_words = re.findall(r'[a-z]{3,}', message_lower)
        all_keywords = korean_words + english_words
        logger.info(f"🔍 추출된 키워드: 한글={korean_words}, 영어={english_words}")
        
        for word in all_keywords:
            if len(word) >= 2:  # 2글자 이상만
                # 회사명에서 해당 키워드 검색 (더 정확한 매칭)
                # 한글 키워드에 대한 특별 처리
                if word and all(ord(ch) >= 0xAC00 and ord(ch) <= 0xD7A3 for ch in word):
                    # 한글인 경우 - 일반적인 영문 변환 시도
                    search_keywords = [word]
                    # 공백 제거 버전도 추가
                    if ' ' in word:
                        search_keywords.append(word.replace(' ', ''))
                else:
                    # 영문인 경우 - 대소문자 무시
                    search_keywords = [word.lower(), word.upper(), word.capitalize()]
                
                for search_word in search_keywords:
                    search_result = session.execute(text("""
                        SELECT ci.ticker, ci.corp_name, 
                               CASE 
                                   WHEN ci.corp_name LIKE :exact_match THEN 1
                                   WHEN ci.corp_name LIKE :keyword THEN 2
                                   ELSE 3
                               END as priority
                        FROM company_info ci
                        JOIN financials f ON ci.ticker = f.ticker
                        WHERE ci.corp_name LIKE :keyword
                           OR REPLACE(LOWER(ci.corp_name), ' ', '') LIKE :keyword_no_space
                           OR REPLACE(LOWER(ci.corp_name), '.', '') LIKE :keyword_no_dot
                           OR REPLACE(LOWER(ci.corp_name), ',', '') LIKE :keyword_no_comma
                        GROUP BY ci.ticker, ci.corp_name
                        ORDER BY priority, ci.corp_name
                        LIMIT 3
                    """), {
                        "keyword": f"%{search_word}%",
                        "exact_match": f"{search_word}%",
                        "keyword_no_space": f"%{search_word.replace(' ', '')}%",
                        "keyword_no_dot": f"%{search_word.replace('.', '')}%",
                        "keyword_no_comma": f"%{search_word.replace(',', '')}%"
                    }).fetchall()
                    
                    if search_result:
                        break
                
                if search_result:
                    logger.info(f"🎯 동적 검색 성공: '{word}' -> {len(search_result)}개 매칭")
                    for result in search_result:
                        tickers.append(result[0])
                        logger.info(f"🎯 동적 매핑: {result[1]} ({result[0]}) - 우선순위 {result[2]}")
                    return list(set(tickers))  # 중복 제거
        
        # 직접 매핑에서 못 찾은 경우 패턴 매칭
        company_patterns = {
        # 삼성 그룹
        'samsung.*c&t|삼성물산': ['Samsung C&T'],
        # SK 그룹  
        'sk.*hynix': ['SK hynix', 'hynix'],
        'sk': ['SK'],
        # LG 그룹
        'lg.*chem': ['LG Chem'],
        'lg.*display': ['LG Display'], 
        'lg': ['LG'],
        # 현대 그룹
        'hyundai.*motor': ['Hyundai Motor'],
        'hyundai': ['Hyundai', 'HD Hyundai'],
        # 두산 그룹
        'doosan.*ener|두산에너빌리티': ['Doosan Enerbility'],
        'doosan|두산': ['Doosan'],
        # 기타 주요 기업들
        'kakao|카카오': ['Kakao'],
        'posco|포스코': ['POSCO']
    }
        
        # 패턴별로 매칭 확인
        for pattern, search_terms in company_patterns.items():
            if re.search(pattern, message_lower):
                for term in search_terms:
                    result = session.execute(text("""
                        SELECT ticker, corp_name,
                            CASE 
                                WHEN corp_name ILIKE :exact_term THEN 1
                                ELSE 2 
                            END as priority
                        FROM company_info 
                        WHERE corp_name ILIKE :term
                        ORDER BY priority, corp_name
                        LIMIT 3
                    """), {"term": f"%{term}%", "exact_term": f"{term}%"})
                    
                    for row in result:
                        tickers.append(row[0])
                        logger.info(f"🏢 매칭된 기업: {row[1]} ({row[0]})")
                
                # 첫 번째 매칭에서 결과를 찾으면 중단
                if tickers:
                    break
        
        # 직접적인 회사명 검색 (위에서 못 찾은 경우)
        if not tickers:
            # 메시지에서 한글/영문 기업명 추출
            words = re.findall(r'[가-힣]{2,}|[A-Za-z]{2,}', message)
            for word in words:
                if len(word) >= 2:
                    result = session.execute(text("""
                        SELECT ticker, corp_name,
                            CASE 
                                WHEN corp_name ILIKE :exact_word THEN 1
                                ELSE 2 
                            END as priority
                        FROM company_info 
                        WHERE corp_name ILIKE :word
                        ORDER BY priority, corp_name
                        LIMIT 2
                    """), {"word": f"%{word}%", "exact_word": f"{word}%"})
                    
                    for row in result:
                        tickers.append(row[0])
                        logger.info(f"🏢 검색된 기업: {row[1]} ({row[0]})")
    
    except Exception as e:
        logger.error(f"회사명 추출 실패: {e}")
    finally:
        session.close()
    
    # 중복 제거
    return list(set(tickers))

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_agent_system())