"""LLM 기반 포트폴리오 설명 생성 서비스 모듈."""
from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Tuple
import os
import uuid

import httpx

from optimizer.optimize import PortfolioOptimizer
from utils.config import get_settings


# 1. HyperCLOVA X REST 설정 ---------------------------------------------------
CLOVA_KEY = os.getenv("NCP_CLOVASTUDIO_API_KEY") or "nv-59554eec61cf46d09d20445bcf1577b30ro3"
CLOVA_URL = os.getenv("NCP_CLOVASTUDIO_API_URL", "https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions/HCX-005")
REQUEST_ID = os.getenv("NCP_CLOVASTUDIO_REQUEST_ID", "5fb7ea761fea4ebc9e5d4e6256d34783")

print(f"🔑 Using API key: {CLOVA_KEY[:10] if CLOVA_KEY else 'None'}...")  # 디버깅용
print(f"🌐 API URL: {CLOVA_URL}")
print(f"🆔 Request ID: {REQUEST_ID[:10]}...")

# 수정된 헤더 - Accept를 text/event-stream으로 변경
HEADERS = {
    "Authorization": f"Bearer {CLOVA_KEY}",  # Bearer 키워드 포함
    "X-NCP-CLOVASTUDIO-REQUEST-ID": REQUEST_ID,
    "Content-Type": "application/json",
    "Accept": "text/event-stream",  # 스트리밍 응답 처리를 위해 변경
}


async def _call_hcx_async(messages: list[dict]) -> str:
    """비동기 REST 방식으로 HyperCLOVA X 호출 - 스트리밍 응답 처리"""
    payload = {
        "messages": messages,
        "topP": 0.8,
        "topK": 0,
        "maxTokens": 512,  # 더 긴 응답을 위해 증가
        "temperature": 0.5,
        "repetitionPenalty": 1.1,
        "stop": [],
        "includeAiFilters": True,
        "seed": 0
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(CLOVA_URL, headers=HEADERS, json=payload)
            response.raise_for_status()
            
            # 스트리밍 응답 처리
            full_content = ""
            
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith("data:"):
                    try:
                        # "data:" 접두사 제거
                        data_str = line[5:].strip()
                        
                        # [DONE] 신호 확인
                        if "[DONE]" in data_str:
                            break
                            
                        # JSON 파싱
                        data = json.loads(data_str)
                        
                        # 메시지 내용 추출
                        if "message" in data and "content" in data["message"]:
                            content = data["message"]["content"]
                            if content:  # 빈 문자열이 아닌 경우만 추가
                                full_content += content
                                
                    except json.JSONDecodeError:
                        # JSON 파싱 실패한 라인은 무시
                        continue
                    except Exception as e:
                        print(f"Line processing error: {e}")
                        continue
            
            return full_content.strip() if full_content else "응답을 받지 못했습니다."
                
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        return f"HyperCLOVA API 오류: {e.response.status_code}"
    except Exception as e:
        print(f"General Error: {str(e)}")
        return f"시스템 오류: {str(e)}"


def _call_hcx_sync(messages: list[dict]) -> str:
    """동기 방식으로 HyperCLOVA X 호출 (백업용)"""
    import requests
    
    payload = {
        "messages": messages,
        "topP": 0.8,
        "topK": 0,
        "maxTokens": 512,
        "temperature": 0.5,
        "repetitionPenalty": 1.1,
        "stop": [],
        "includeAiFilters": True,
        "seed": 0
    }
    
    try:
        response = requests.post(CLOVA_URL, headers=HEADERS, json=payload, timeout=30, stream=True)
        response.raise_for_status()
        
        # 스트리밍 응답 처리 (동기 버전)
        full_content = ""
        
        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.strip():
                continue
                
            line = line.strip()
            if line.startswith("data:"):
                try:
                    data_str = line[5:].strip()
                    
                    if "[DONE]" in data_str:
                        break
                        
                    data = json.loads(data_str)
                    
                    if "message" in data and "content" in data["message"]:
                        content = data["message"]["content"]
                        if content:
                            full_content += content
                            
                except (json.JSONDecodeError, KeyError):
                    continue
        
        return full_content.strip() if full_content else "응답을 받지 못했습니다."
            
    except Exception as e:
        return f"HyperCLOVA 호출 실패: {str(e)}"


# 2. 프롬프트 템플릿 -----------------------------------------------------------
_SYSTEM_PROMPT = """당신은 한국 자산관리 전문가입니다. 포트폴리오 추천 시 고객의 나이, 투자 경험, 리스크 성향을 고려하여 개인화된 설명을 제공합니다.

다음 형식으로 설명해주세요:
1. 포트폴리오 구성 요약
2. 각 자산 배분 비율과 선택 이유  
3. 예상 수익률과 위험도 분석
4. 투자 시 주의사항 및 추천 사항

고객이 이해하기 쉽도록 전문용어는 최소화하고, 구체적인 수치와 근거를 제시하여 설명하세요."""

_USER_PROMPT_TEMPLATE = """다음 포트폴리오 분석 결과를 바탕으로 고객에게 맞춤형 투자 설명을 해주세요.

**포트폴리오 정보:**
- 자산별 비중: {weights}
- 예상 연수익률: {expected_return:.1%}
- 연변동성: {volatility:.1%}  
- 샤프비율: {sharpe:.3f}

**고객 정보:**
- 나이: {age}세
- 투자 경험: {experience}
- 리스크 성향: {risk_profile}
- 투자 목표: {investment_goal}
- 투자 기간: {investment_period}

위 정보를 종합하여 고객에게 적합한 포트폴리오 추천 이유를 설명해주세요."""


# 3. 내부 함수 -----------------------------------------------------------------
async def _get_explanation_async(
    weights: Dict[str, float],
    perf: Tuple[float, float, float],
    age: int,
    experience: str,
    risk_profile: str,
    investment_goal: str,
    investment_period: str,
) -> str:
    """비동기 방식으로 HyperCLOVA 설명 생성"""
    
    # 종목 이름 매핑 (실제 서비스에서는 DB에서 가져와야 함)
    ticker_names = {
        "005930": "삼성전자",
        "000660": "SK하이닉스", 
        "035420": "네이버",
        "005380": "현대차",
        "051910": "LG화학"
    }
    
    # 종목별 비중을 이름으로 변환
    weight_text = ", ".join([
        f"{ticker_names.get(ticker, ticker)} {weight:.1%}" 
        for ticker, weight in weights.items() if weight > 0
    ])
    
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        weights=weight_text,
        expected_return=perf[0],
        volatility=perf[1],
        sharpe=perf[2],
        age=age,
        experience=experience,
        risk_profile=risk_profile,
        investment_goal=investment_goal,
        investment_period=investment_period
    )
    
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    return await _call_hcx_async(messages)


def _get_explanation_sync(
    weights: Dict[str, float],
    perf: Tuple[float, float, float],
    age: int,
    experience: str,
    risk_profile: str,
    investment_goal: str,
    investment_period: str,
) -> str:
    """동기 방식으로 HyperCLOVA 설명 생성 (백업용)"""
    
    ticker_names = {
        "005930": "삼성전자",
        "000660": "SK하이닉스", 
        "035420": "네이버",
        "005380": "현대차",
        "051910": "LG화학"
    }
    
    weight_text = ", ".join([
        f"{ticker_names.get(ticker, ticker)} {weight:.1%}" 
        for ticker, weight in weights.items() if weight > 0
    ])
    
    user_prompt = _USER_PROMPT_TEMPLATE.format(
        weights=weight_text,
        expected_return=perf[0],
        volatility=perf[1],
        sharpe=perf[2],
        age=age,
        experience=experience,
        risk_profile=risk_profile,
        investment_goal=investment_goal,
        investment_period=investment_period
    )
    
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    return _call_hcx_sync(messages)


async def _run_optimizer_async(tickers: List[str]) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
    """비동기 컨텍스트에서 포트폴리오 최적화 실행"""
    loop = asyncio.get_running_loop()
    
    def _optimize():
        optimizer = PortfolioOptimizer(tickers)
        return optimizer.optimize()
    
    # CPU-bound 작업을 별도 스레드에서 실행
    return await loop.run_in_executor(None, _optimize)


# 4. 외부 공개 함수 ------------------------------------------------------------
async def create_portfolio_with_explanation(
    tickers: List[str],
    *,
    age: int,
    experience: str,
    risk_profile: str,
    investment_goal: str,
    investment_period: str,
) -> Dict:
    """
    비동기 방식으로 포트폴리오 최적화 + HyperCLOVA 설명 생성
    
    Args:
        tickers: 종목 코드 리스트
        age: 고객 나이
        experience: 투자 경험
        risk_profile: 리스크 성향
        investment_goal: 투자 목표
        investment_period: 투자 기간
        
    Returns:
        포트폴리오 결과와 설명이 포함된 딕셔너리
        
    Raises:
        ValueError: 종목 데이터가 부족하거나 최적화 실패 시
        httpx.HTTPError: HyperCLOVA API 호출 실패 시
    """
    try:
        # 1. 포트폴리오 최적화 (비동기)
        weights, perf = await _run_optimizer_async(tickers)
        
        # 2. HyperCLOVA 설명 생성 (비동기)
        explanation = await _get_explanation_async(
            weights, perf, age, experience, risk_profile, investment_goal, investment_period
        )
        
        return {
            "weights": weights,
            "performance": {
                "expected_annual_return": perf[0],
                "annual_volatility": perf[1],
                "sharpe_ratio": perf[2],
            },
            "explanation": explanation,
        }
        
    except Exception as e:
        # 로깅
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"포트폴리오 생성 실패: {e}")
        raise


def create_portfolio_with_explanation_sync(
    tickers: List[str],
    *,
    age: int,
    experience: str,
    risk_profile: str,
    investment_goal: str,
    investment_period: str,
) -> Dict:
    """
    동기 방식으로 포트폴리오 최적화 + HyperCLOVA 설명 생성 (백업용)
    """
    try:
        # 1. 포트폴리오 최적화
        optimizer = PortfolioOptimizer(tickers)
        weights, perf = optimizer.optimize()
        
        # 2. HyperCLOVA 설명 생성
        explanation = _get_explanation_sync(
            weights, perf, age, experience, risk_profile, investment_goal, investment_period
        )
        
        return {
            "weights": weights,
            "performance": {
                "expected_annual_return": perf[0],
                "annual_volatility": perf[1],
                "sharpe_ratio": perf[2],
            },
            "explanation": explanation,
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"포트폴리오 생성 실패 (sync): {e}")
        raise


# 5. 테스트 함수 ---------------------------------------------------------------
async def test_hyperclova():
    """HyperCLOVA 연동 테스트"""
    print("🚀 HyperCLOVA 연동 테스트 시작...")
    
    try:
        messages = [
            {"role": "system", "content": "당신은 친근한 AI 어시스턴트입니다."},
            {"role": "user", "content": "안녕하세요! 간단한 인사말을 해주세요."}
        ]
        
        result = await _call_hcx_async(messages)
        print(f"✅ HyperCLOVA 응답: {result}")
        return True
        
    except Exception as e:
        print(f"❌ HyperCLOVA 연동 실패: {e}")
        return False


if __name__ == "__main__":
    # HyperCLOVA 연동 테스트
    asyncio.run(test_hyperclova())