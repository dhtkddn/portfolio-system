"""기본 포트폴리오 추천 서비스 (순환 import 해결)."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Tuple

from app.services.hyperclova_client import _call_hcx_async
from optimizer.optimize import PortfolioOptimizer

logger = logging.getLogger(__name__)

async def create_portfolio_with_explanation(
    tickers: List[str],
    age: int,
    experience: str,
    risk_profile: str,
    investment_goal: str,
    investment_period: str,
) -> Dict:
    """포트폴리오 최적화 + HyperCLOVA 설명 생성."""
    
    try:
        # 1. 포트폴리오 최적화
        optimizer = PortfolioOptimizer(tickers)
        weights, performance = optimizer.optimize()
        
        # 2. AI 설명 생성
        explanation = await _generate_portfolio_explanation(
            weights, performance, age, experience, risk_profile, 
            investment_goal, investment_period
        )
        
        return {
            "weights": weights,
            "performance": {
                "expected_annual_return": performance[0],
                "annual_volatility": performance[1], 
                "sharpe_ratio": performance[2]
            },
            "explanation": explanation
        }
        
    except Exception as e:
        logger.error(f"포트폴리오 생성 실패: {e}")
        
        # 폴백: 균등 분산 포트폴리오
        n = len(tickers)
        fallback_weights = {ticker: 1.0/n for ticker in tickers}
        
        return {
            "weights": fallback_weights,
            "performance": {
                "expected_annual_return": 0.08,
                "annual_volatility": 0.15,
                "sharpe_ratio": 0.53
            },
            "explanation": f"시스템 오류로 인해 균등 분산 포트폴리오를 제공합니다. 오류: {str(e)}"
        }

async def _generate_portfolio_explanation(
    weights: Dict[str, float],
    performance: Tuple[float, float, float],
    age: int,
    experience: str,
    risk_profile: str,
    investment_goal: str,
    investment_period: str
) -> str:
    """포트폴리오 설명 생성."""
    
    context = f"""
다음 포트폴리오에 대해 상세한 설명을 해주세요:

**포트폴리오 구성:**
{weights}

**예상 성과:**
- 연수익률: {performance[0]:.1%}
- 연변동성: {performance[1]:.1%}  
- 샤프비율: {performance[2]:.3f}

**투자자 정보:**
- 나이: {age}세
- 투자경험: {experience}
- 위험성향: {risk_profile}
- 투자목표: {investment_goal}
- 투자기간: {investment_period}

다음 내용을 포함해서 설명해주세요:
1. 포트폴리오 구성 근거
2. 각 종목 선택 이유
3. 위험도와 수익성 분석
4. 투자자에게 적합한 이유
5. 주의사항 및 리스크
"""

    system_prompt = """
당신은 20년 경력의 투자 전문가입니다.
포트폴리오에 대해 쉽고 친근하게 설명해주세요.
투자 위험을 반드시 언급하고, 개인 투자 판단의 중요성을 강조해주세요.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]
    
    try:
        explanation = await _call_hcx_async(messages)
        return explanation
    except Exception as e:
        logger.error(f"설명 생성 실패: {e}")
        return f"포트폴리오 설명 생성에 실패했습니다. 오류: {str(e)}"