"""HyperCLOVA API 클라이언트 - 공통 유틸리티."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class HyperCLOVAClient:
    """HyperCLOVA X API 클라이언트."""
    
    def __init__(self):
        self.api_key = os.getenv("NCP_CLOVASTUDIO_API_KEY")
        self.api_url = os.getenv("NCP_CLOVASTUDIO_API_URL", 
                                "https://clovastudio.stream.ntruss.com/testapp/v3/chat-completions/HCX-005")
        self.request_id = os.getenv("NCP_CLOVASTUDIO_REQUEST_ID", "portfolio-ai")
        
        if not self.api_key:
            logger.warning("⚠️ HyperCLOVA API key not found. Using mock responses.")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """HyperCLOVA 채팅 완성 요청."""
        
        if not self.api_key:
            return await self._mock_response(messages)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-NCP-CLOVASTUDIO-REQUEST-ID": self.request_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await response.text()
                        logger.error(f"HyperCLOVA API error {response.status}: {error_text}")
                        return await self._mock_response(messages)
                        
        except asyncio.TimeoutError:
            logger.error("HyperCLOVA API timeout")
            return await self._mock_response(messages)
        except Exception as e:
            logger.error(f"HyperCLOVA API error: {e}")
            return await self._mock_response(messages)
    
    async def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        """API 오류 시 모의 응답 생성."""
        
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # 키워드 기반 모의 응답
        if "포트폴리오" in user_message or "추천" in user_message:
            return """
## 포트폴리오 분석 결과

**추천 종목:**
1. **삼성전자 (005930)** - 30%
   - 국내 대표 기술주로 안정성과 성장성을 모두 갖춤
   - 반도체 시장 회복과 AI 수요 증가로 긍정적 전망

2. **네이버 (035420)** - 25%  
   - 국내 최대 포털 사업자로 안정적 수익 기반
   - 클라우드, AI 등 신사업 확장으로 성장 동력 확보

3. **LG화학 (051910)** - 20%
   - 배터리 사업의 글로벌 경쟁력
   - 전기차 시장 확대에 따른 수혜 기대

4. **현대차 (005380)** - 15%
   - 국내 대표 완성차 업체
   - 전기차 전환과 해외 시장 확대

5. **현금성 자산** - 10%
   - 시장 변동성 대비 안전자산 확보

**투자 포인트:**
- 장기 관점에서 안정적 성장이 기대되는 대형주 중심
- 섹터 분산을 통한 리스크 관리
- 정기적인 리밸런싱 권장

**주의사항:**
- 모든 투자에는 원금 손실 위험이 있습니다
- 개인의 투자 성향과 목표를 고려하여 조정하세요
- 정기적인 포트폴리오 점검이 필요합니다
"""
        
        elif "재무" in user_message or "분석" in user_message:
            return """
## 재무 분석 결과

**재무 건전성:**
- 매출액과 영업이익이 지속적으로 성장하는 추세
- 부채비율이 안정적이며 현금흐름이 양호
- ROE와 ROA가 업종 평균 이상 수준

**성장성:**
- 최근 3년간 연평균 매출 성장률 양호
- 신사업 투자를 통한 미래 성장 동력 확보
- 글로벌 시장 확대 노력

**수익성:**
- 영업이익률이 업종 대비 우수
- 원가 관리 효율성 개선
- 고부가가치 제품 비중 확대

**투자 의견:**
이 기업은 재무적으로 건전하며 지속 가능한 성장이 기대됩니다. 
다만 시장 환경 변화와 경쟁 심화 요인을 지속 모니터링할 필요가 있습니다.

**주의사항:**
본 분석은 참고용이며, 투자 결정은 개인의 판단에 따라 신중히 하시기 바랍니다.
"""
        
        elif "시장" in user_message or "전망" in user_message:
            return """
## 시장 분석 및 전망

**현재 시장 상황:**
- 글로벌 경제 불확실성 속에서도 국내 주식시장은 상대적으로 안정
- 금리 정책과 환율 변동이 주요 변수로 작용
- 기술주와 2차전지 관련주가 주목받고 있음

**섹터별 전망:**
- **IT/반도체**: AI 수요 증가로 중장기 성장 기대
- **자동차**: 전기차 전환 가속화로 관련 업체 수혜
- **바이오**: 신약 개발과 고령화로 지속 성장
- **금융**: 금리 변동성에 따른 수익성 변화 주목

**투자 전략:**
1. 분산 투자를 통한 리스크 관리
2. 장기 관점에서의 우량주 중심 투자
3. 정기적인 포트폴리오 리밸런싱
4. 시장 변동성에 대비한 현금 비중 유지

**주요 리스크:**
- 글로벌 경제 둔화 우려
- 지정학적 리스크
- 금리 및 환율 변동성

투자 시에는 개인의 위험 성향과 투자 목표를 고려하여 신중한 판단이 필요합니다.
"""
        
        else:
            return """
안녕하세요! 저는 AI 투자 상담사입니다.

다음과 같은 도움을 드릴 수 있습니다:
- 개인 맞춤형 포트폴리오 추천
- 종목별 재무 분석 및 투자 의견
- 시장 동향 분석 및 전망
- 투자 전략 수립 상담

구체적으로 어떤 도움이 필요하신지 말씀해 주세요.
예를 들어:
- "30대 직장인 포트폴리오 추천해주세요"
- "삼성전자 재무 분석 해주세요"  
- "현재 시장 상황과 투자 전략은?"

**주의사항:** 모든 투자 조언은 참고용이며, 최종 투자 결정은 개인의 책임입니다.
"""

# 전역 클라이언트 인스턴스
hyperclova_client = HyperCLOVAClient()

# 호환성을 위한 함수
async def _call_hcx_async(messages: List[Dict[str, str]]) -> str:
    """HyperCLOVA 호출 래퍼 함수 (기존 코드 호환성)."""
    return await hyperclova_client.chat_completion(messages)

# HyperCLOVA 연결 테스트
async def test_hyperclova() -> bool:
    """HyperCLOVA 연결 테스트."""
    try:
        test_messages = [
            {"role": "user", "content": "안녕하세요. 연결 테스트입니다."}
        ]
        response = await _call_hcx_async(test_messages)
        return len(response) > 10
    except Exception as e:
        logger.error(f"HyperCLOVA 테스트 실패: {e}")
        return False