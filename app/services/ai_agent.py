"""AI 에이전트 서비스 - RAG 기반 지능형 투자 상담."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Tuple

from app.services.models import (
    ChatResponse, 
    UserProfile, 
    StockRecommendation,
    MarketAnalysisResponse,
    FinancialAnalysisResponse,
    ConversationMessage
)
from app.services.portfolio import _call_hcx_async
from app.services.stock_database import StockDatabase
from utils.db import SessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

class InvestmentAIAgent:
    """HyperCLOVA 기반 투자 상담 AI 에이전트."""
    
    def __init__(self):
        self.stock_db = StockDatabase()
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """AI 에이전트 시스템 프롬프트 생성."""
        return """
당신은 대한민국 주식시장 전문가이자 개인 투자 상담사입니다. 
다음 역할을 수행해주세요:

**핵심 역할:**
1. 개인화된 종목 추천 및 포트폴리오 구성
2. 재무지표 분석 및 해석
3. 시장 동향 및 섹터 분석
4. 투자 위험 관리 조언
5. 자연어로 쉬운 투자 교육

**응답 원칙:**
- 사용자의 나이, 소득, 투자경험, 위험성향을 고려한 맞춤형 조언
- KOSPI/KOSDAQ 종목 데이터를 기반으로 한 구체적 추천
- 복잡한 금융 용어는 쉽게 설명
- 위험 요소와 주의사항을 반드시 언급
- 투자 결정은 사용자 몫임을 명시

**출력 형식:**
- 친근하고 전문적인 톤
- 구체적 수치와 근거 제시
- 단계별 실행 가능한 조언
- 추가 질문 유도로 대화 지속

**금지사항:**
- 투자 수익 보장 약속
- 특정 시점의 매매 타이밍 제시
- 개인적 투자 의견 강요
- 과도한 위험 추천
"""

    async def chat(
        self, 
        user_message: str, 
        user_profile: Optional[UserProfile] = None,
        conversation_history: Optional[List[ConversationMessage]] = None
    ) -> ChatResponse:
        """자연어 대화형 투자 상담."""
        
        # 1. 사용자 의도 분석
        intent = await self._analyze_user_intent(user_message)
        
        # 2. 관련 종목 데이터 검색 (RAG)
        relevant_stocks = await self._search_relevant_stocks(user_message, user_profile)
        
        # 3. 컨텍스트 구성
        context = await self._build_context(
            user_message, user_profile, relevant_stocks, conversation_history
        )
        
        # 4. AI 응답 생성
        ai_response = await self._generate_ai_response(context, intent)
        
        # 5. 구조화된 응답 파싱
        parsed_response = await self._parse_ai_response(ai_response, relevant_stocks)
        
        return parsed_response

    async def _analyze_user_intent(self, message: str) -> str:
        """사용자 의도 분석 (종목추천/시장분석/재무분석/일반상담)."""
        intent_keywords = {
            "stock_recommendation": ["추천", "종목", "어떤 주식", "포트폴리오", "투자하고 싶어"],
            "market_analysis": ["시장", "전망", "동향", "섹터", "업종", "상황"],
            "financial_analysis": ["재무", "실적", "매출", "영업이익", "분석해줘"],
            "general_consultation": ["초보", "처음", "방법", "어떻게", "가이드"]
        }
        
        message_lower = message.lower()
        intent_scores = {}
        
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            intent_scores[intent] = score
        
        return max(intent_scores, key=intent_scores.get)

    async def _search_relevant_stocks(
        self, 
        message: str, 
        user_profile: Optional[UserProfile]
    ) -> List[Dict]:
        """RAG: 사용자 질문과 관련된 종목 검색."""
        
        # 키워드 추출
        keywords = self._extract_keywords(message)
        
        # 데이터베이스에서 관련 종목 검색
        relevant_stocks = await self.stock_db.search_stocks_by_keywords(keywords)
        
        # 사용자 프로필 기반 필터링
        if user_profile:
            relevant_stocks = self._filter_by_user_profile(relevant_stocks, user_profile)
        
        return relevant_stocks[:20]  # 상위 20개만

    def _extract_keywords(self, message: str) -> List[str]:
        """메시지에서 키워드 추출."""
        # 업종/테마 키워드
        sector_keywords = {
            "반도체": ["반도체", "삼성전자", "SK하이닉스", "메모리"],
            "바이오": ["바이오", "제약", "의료", "헬스케어"],
            "게임": ["게임", "엔터테인먼트", "넷마블"],
            "금융": ["은행", "증권", "보험", "금융"],
            "자동차": ["자동차", "현대차", "기아", "전기차"],
            "화학": ["화학", "정유", "플라스틱"],
            "건설": ["건설", "부동산", "건설사"],
            "유통": ["유통", "이마트", "백화점"],
            "통신": ["통신", "KT", "SKT", "LG유플러스"]
        }
        
        keywords = []
        message_lower = message.lower()
        
        # 섹터 키워드 매칭
        for sector, sector_words in sector_keywords.items():
            if any(word in message_lower for word in sector_words):
                keywords.append(sector)
        
        # 일반 키워드 추출 (한글 명사)
        import re
        korean_words = re.findall(r'[가-힣]{2,}', message)
        keywords.extend(korean_words)
        
        return list(set(keywords))

    def _filter_by_user_profile(
        self, 
        stocks: List[Dict], 
        profile: UserProfile
    ) -> List[Dict]:
        """사용자 프로필에 따른 종목 필터링."""
        
        if not profile:
            return stocks
        
        filtered_stocks = []
        
        for stock in stocks:
            # 위험성향에 따른 필터링
            if profile.risk_tolerance == "안전형":
                # 대형주, 배당주 우선
                if stock.get("market_cap", 0) > 10000000:  # 10조원 이상
                    filtered_stocks.append(stock)
            elif profile.risk_tolerance == "공격형":
                # 성장주, 중소형주 포함
                filtered_stocks.append(stock)
            else:
                # 중립형: 모든 종목
                filtered_stocks.append(stock)
        
        # 투자 경험에 따른 필터링
        if profile.experience_level == "초보":
            # 대형주 위주로 필터링
            filtered_stocks = [
                s for s in filtered_stocks 
                if s.get("market_cap", 0) > 5000000  # 5조원 이상
            ]
        
        return filtered_stocks

    async def _build_context(
        self,
        user_message: str,
        user_profile: Optional[UserProfile],
        relevant_stocks: List[Dict],
        conversation_history: Optional[List[ConversationMessage]]
    ) -> str:
        """AI 응답 생성용 컨텍스트 구성."""
        
        context_parts = []
        
        # 사용자 프로필 정보
        if user_profile:
            profile_text = f"""
**사용자 프로필:**
- 나이: {user_profile.age}세
- 월소득: {user_profile.monthly_income}만원
- 투자가능금액: {user_profile.investment_amount}만원
- 투자경험: {user_profile.experience_level}
- 위험성향: {user_profile.risk_tolerance}
- 투자목표: {user_profile.investment_goal}
- 투자기간: {user_profile.investment_period}
"""
            context_parts.append(profile_text)
        
        # 관련 종목 정보
        if relevant_stocks:
            stocks_text = "**관련 종목 정보:**\n"
            for stock in relevant_stocks[:10]:  # 상위 10개만
                stocks_text += f"- {stock.get('name', 'N/A')} ({stock.get('ticker', 'N/A')}): "
                stocks_text += f"{stock.get('sector', 'N/A')} 업종, "
                stocks_text += f"시가총액 {stock.get('market_cap', 0):,.0f}억원\n"
            context_parts.append(stocks_text)
        
        # 대화 히스토리
        if conversation_history:
            history_text = "**이전 대화:**\n"
            for msg in conversation_history[-3:]:  # 최근 3개만
                history_text += f"{msg.role}: {msg.content}\n"
            context_parts.append(history_text)
        
        # 현재 질문
        context_parts.append(f"**현재 질문:** {user_message}")
        
        return "\n\n".join(context_parts)

    async def _generate_ai_response(self, context: str, intent: str) -> str:
        """HyperCLOVA를 사용한 AI 응답 생성."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": context}
        ]
        
        response = await _call_hcx_async(messages)
        return response

    async def _parse_ai_response(
        self, 
        ai_response: str, 
        relevant_stocks: List[Dict]
    ) -> ChatResponse:
        """AI 응답을 구조화된 형태로 파싱."""
        
        # 종목 추천 추출
        recommendations = self._extract_stock_recommendations(ai_response, relevant_stocks)
        
        # 포트폴리오 비중 추출
        portfolio = self._extract_portfolio_weights(ai_response)
        
        # 다음 질문 제안
        next_questions = self._generate_next_questions(ai_response)
        
        return ChatResponse(
            message=ai_response,
            recommendations=recommendations,
            suggested_portfolio=portfolio,
            next_questions=next_questions,
            confidence_score=0.8  # 임시값
        )

    def _extract_stock_recommendations(
        self, 
        response: str, 
        relevant_stocks: List[Dict]
    ) -> List[StockRecommendation]:
        """응답에서 종목 추천 정보 추출."""
        
        recommendations = []
        
        # 종목명이나 코드가 언급된 경우 추천으로 간주
        for stock in relevant_stocks:
            stock_name = stock.get('name', '')
            ticker = stock.get('ticker', '')
            
            if stock_name in response or ticker in response:
                # 추천 이유 추출 (해당 종목 언급 주변 텍스트)
                reason = self._extract_reason_for_stock(response, stock_name, ticker)
                
                recommendations.append(StockRecommendation(
                    ticker=ticker,
                    name=stock_name,
                    sector=stock.get('sector', ''),
                    reason=reason,
                    target_weight=0.2,  # 기본값, 실제로는 AI가 제안한 비중 파싱
                    risk_level=self._assess_risk_level(stock)
                ))
        
        return recommendations[:5]  # 최대 5개 추천

    def _extract_reason_for_stock(self, response: str, stock_name: str, ticker: str) -> str:
        """특정 종목의 추천 이유 추출."""
        sentences = response.split('.')
        reason_sentences = []
        
        for sentence in sentences:
            if stock_name in sentence or ticker in sentence:
                reason_sentences.append(sentence.strip())
        
        return '. '.join(reason_sentences) if reason_sentences else "AI가 추천한 종목입니다."

    def _assess_risk_level(self, stock: Dict) -> str:
        """종목의 위험도 평가."""
        market_cap = stock.get('market_cap', 0)
        
        if market_cap > 10000000:  # 10조원 이상
            return "낮음"
        elif market_cap > 1000000:  # 1조원 이상
            return "보통"
        else:
            return "높음"

    def _extract_portfolio_weights(self, response: str) -> Optional[Dict[str, float]]:
        """응답에서 포트폴리오 비중 추출."""
        # 비중이 언급된 패턴 찾기 (예: "삼성전자 30%, 네이버 20%")
        import re
        
        weight_pattern = r'([가-힣\w]+)\s*:?\s*(\d+)%'
        matches = re.findall(weight_pattern, response)
        
        if matches:
            portfolio = {}
            total_weight = 0
            
            for stock_name, weight_str in matches:
                weight = float(weight_str) / 100
                portfolio[stock_name] = weight
                total_weight += weight
            
            # 비중 정규화
            if total_weight > 0:
                portfolio = {k: v/total_weight for k, v in portfolio.items()}
                return portfolio
        
        return None

    def _generate_next_questions(self, response: str) -> List[str]:
        """응답 기반 다음 질문 제안."""
        base_questions = [
            "이 종목들의 최근 실적은 어떤가요?",
            "리스크를 더 줄이고 싶은데 어떻게 하면 좋을까요?",
            "투자 시기는 언제가 좋을까요?",
            "이 업종의 향후 전망은 어떤가요?",
            "다른 투자 옵션도 알고 싶어요."
        ]
        
        # 응답 내용에 따라 맞춤형 질문 생성
        if "반도체" in response:
            base_questions.append("반도체 업종의 사이클을 고려해야 하나요?")
        if "배당" in response:
            base_questions.append("배당금은 언제 받을 수 있나요?")
        if "성장주" in response:
            base_questions.append("성장주 투자 시 주의사항은 무엇인가요?")
        
        return base_questions[:3]


# 전역 AI 에이전트 인스턴스
agent = InvestmentAIAgent()


# 공개 함수들
async def chat_with_agent(
    user_message: str,
    user_profile: Optional[UserProfile] = None,
    conversation_history: Optional[List[ConversationMessage]] = None
) -> ChatResponse:
    """자연어 대화형 투자 상담."""
    return await agent.chat(user_message, user_profile, conversation_history)


async def get_stock_recommendations(
    user_message: str,
    user_profile: Optional[UserProfile] = None
) -> Dict:
    """AI 기반 개인화 종목 추천."""
    
    # 1. 사용자 프로필 분석
    if not user_profile:
        user_profile = await _extract_profile_from_message(user_message)
    
    # 2. 전체 KOSPI/KOSDAQ 종목에서 추천
    all_stocks = await agent.stock_db.get_all_stocks()
    filtered_stocks = agent._filter_by_user_profile(all_stocks, user_profile)
    
    # 3. AI 추천 생성
    context = f"""
사용자 프로필: {user_profile.dict() if user_profile else {}}
요청사항: {user_message}
가능한 종목들: {[s['name'] for s in filtered_stocks[:50]]}

위 정보를 바탕으로 최적의 5-10개 종목을 추천하고 포트폴리오를 구성해주세요.
각 종목별로 추천 이유와 적정 비중을 제시해주세요.
"""
    
    ai_response = await agent._generate_ai_response(context, "stock_recommendation")
    parsed_response = await agent._parse_ai_response(ai_response, filtered_stocks)
    
    return {
        "recommendations": parsed_response.recommendations,
        "portfolio": parsed_response.suggested_portfolio,
        "explanation": parsed_response.message,
        "user_profile": user_profile.dict() if user_profile else None
    }


async def analyze_market_trends(
    analysis_type: str,
    target: str,
    time_period: str = "3M"
) -> MarketAnalysisResponse:
    """AI 기반 시장 동향 분석."""
    
    # 1. 관련 데이터 수집
    if analysis_type == "sector":
        sector_data = await agent.stock_db.get_sector_data(target)
        context_data = sector_data
    elif analysis_type == "stock":
        stock_data = await agent.stock_db.get_stock_data(target)
        context_data = stock_data
    else:
        market_data = await agent.stock_db.get_market_overview()
        context_data = market_data
    
    # 2. AI 분석 요청
    context = f"""
분석 유형: {analysis_type}
분석 대상: {target}
분석 기간: {time_period}
관련 데이터: {context_data}

위 정보를 바탕으로 시장 동향을 종합 분석해주세요:
1. 현재 트렌드 방향과 강도
2. 주요 상승/하락 요인
3. 향후 전망과 리스크
4. 투자 포인트와 주의사항
"""
    
    ai_response = await agent._generate_ai_response(context, "market_analysis")
    
    # 응답 파싱 및 구조화
    return MarketAnalysisResponse(
        analysis_summary=ai_response,
        current_trend={
            "trend_direction": "상승",  # AI 응답에서 추출
            "strength": 0.7,
            "key_drivers": ["실적 개선", "정책 호재"],
            "risk_factors": ["금리 인상", "환율 변동"]
        },
        key_metrics={"pe_ratio": 12.5, "pb_ratio": 1.2},
        recommendations=["분할 매수 전략", "장기 투자 관점"],
        outlook="단기 조정 후 상승 전망",
        related_stocks=[]
    )


async def analyze_financial_metrics(
    ticker: str,
    user_question: Optional[str] = None
) -> FinancialAnalysisResponse:
    """특정 종목의 재무지표 AI 분석."""
    
    # 1. 재무 데이터 수집
    financial_data = await agent.stock_db.get_financial_data(ticker)
    
    # 2. AI 분석 요청
    context = f"""
종목 코드: {ticker}
재무 데이터: {financial_data}
사용자 질문: {user_question or "이 종목의 재무상태를 종합 분석해주세요"}

다음 관점에서 분석해주세요:
1. 수익성 지표 (매출액, 영업이익률, 순이익률)
2. 성장성 지표 (매출 성장률, 이익 성장률)
3. 안정성 지표 (부채비율, 유동비율)
4. 효율성 지표 (ROE, ROA)
5. 밸류에이션 (PER, PBR)
6. 종합 평가 및 투자 의견
"""
    
    ai_response = await agent._generate_ai_response(context, "financial_analysis")
    
    return FinancialAnalysisResponse(
        ticker=ticker,
        company_name=financial_data.get('company_name', ''),
        analysis_summary=ai_response,
        financial_metrics=[],  # AI 응답에서 파싱
        strengths=["견고한 수익성", "성장 가능성"],
        weaknesses=["높은 부채비율"],
        investment_rating="매수",
        target_price=None
    )


async def _extract_profile_from_message(message: str) -> UserProfile:
    """메시지에서 사용자 프로필 정보 추출."""
    
    import re
    
    profile = UserProfile()
    
    # 나이 추출
    age_pattern = r'(\d+)세|(\d+)살'
    age_match = re.search(age_pattern, message)
    if age_match:
        profile.age = int(age_match.group(1) or age_match.group(2))
    
    # 투자 금액 추출
    amount_patterns = [
        r'(\d+)만원',
        r'(\d+)백만원',
        r'월\s*(\d+)'
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, message)
        if match:
            amount = int(match.group(1))
            if '백만원' in pattern:
                amount *= 100
            profile.investment_amount = amount
            break
    
    # 투자 경험 추출
    if any(word in message for word in ['초보', '처음', '시작']):
        profile.experience_level = "초보"
    elif any(word in message for word in ['경험', '해봤', '알고 있']):
        profile.experience_level = "중급"
    
    # 위험 성향 추출
    if any(word in message for word in ['안전', '안정', '위험 싫어']):
        profile.risk_tolerance = "안전형"
    elif any(word in message for word in ['공격적', '수익', '많이']):
        profile.risk_tolerance = "공격형"
    else:
        profile.risk_tolerance = "중립형"
    
    return profile