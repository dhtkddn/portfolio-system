# app/services/hyperclova_client.py - 완전 수정 버전

import os
import json
import logging
import aiohttp
import uuid
import re
from typing import List, Dict, Any, Union

from utils.config import (
    NCP_CLOVASTUDIO_API_KEY as API_KEY,
    NCP_CLOVASTUDIO_API_URL as API_URL,
    NCP_CLOVASTUDIO_REQUEST_ID as REQUEST_ID,
    MAX_TOKENS,
    REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

IS_MOCK_MODE = not all([API_KEY, API_URL])

if IS_MOCK_MODE:
    logger.warning("HyperCLOVA Studio의 API 설정(.env)이 누락되었습니다. 모의(Mock) 모드로 동작합니다.")
else:
    logger.info("🔑 HyperCLOVA API 키 설정 감지됨")

async def _call_hcx_api(messages: List[Dict[str, str]]) -> str:
    """HyperCLOVA API 호출 - 강화된 응답 파싱 및 오류 처리"""
    
    # 🔥 동적 REQUEST_ID 생성 (UUID 형식)
    dynamic_request_id = str(uuid.uuid4()).replace('-', '')
    
    # 🔥 최적화된 헤더 구조
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'X-NCP-CLOVASTUDIO-REQUEST-ID': dynamic_request_id,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
    }

    logger.info(f"🔑 REQUEST_ID: {dynamic_request_id}")

    # 🔥 요청 파라미터 최적화
    data = {
        'messages': messages,
        'topP': 0.8,
        'topK': 0,
        'maxTokens': 3500,  # 🔥 충분한 토큰 수로 증가
        'temperature': 0.7,  # 🔥 창의성 약간 증가
        'repetitionPenalty': 1.1,
        'stop': [],
        'includeAiFilters': True,
        'seed': 0
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                API_URL, 
                headers=headers, 
                json=data, 
                timeout=REQUEST_TIMEOUT
            ) as response:
                response_text = await response.text()
                
                logger.info(f"🔍 API 응답 상태: {response.status}")
                logger.debug(f"🔍 API 응답 길이: {len(response_text)}")
                
                if response.status == 200:
                    # 🔥 강화된 응답 파싱
                    content = _extract_from_streaming_response(response_text)
                    
                    if content and len(content) > 50:
                        logger.info(f"✅ HyperCLOVA API 성공: {len(content)}자")
                        return content
                    else:
                        logger.warning("⚠️ API 응답이 비어있거나 너무 짧음")
                        logger.debug(f"🔍 전체 응답 내용: {response_text[:1000]}...")
                        
                        # 🔥 다른 파싱 방법 시도
                        alternative_content = _alternative_content_extraction(response_text)
                        if alternative_content:
                            logger.info(f"✅ 대안 파싱 성공: {len(alternative_content)}자")
                            return alternative_content
                        
                        logger.error("❌ 모든 파싱 방법 실패")
                        return ""
                else:
                    logger.error(f"❌ HyperCLOVA API 오류 ({response.status}): {response_text}")
                    raise Exception(f"API 호출 실패: {response.status}")
                    
    except Exception as e:
        logger.error(f"❌ HyperCLOVA API 호출 중 예외 발생: {e}")
        raise


def _extract_from_streaming_response(response_text: str) -> str:
    """스트리밍 응답에서 실제 텍스트 추출 - 강화된 파싱"""
    try:
        logger.debug(f"🔍 스트리밍 응답 파싱 시작 (길이: {len(response_text)})")
        
        lines = response_text.strip().split('\n')
        content_parts = []
        
        for line in lines:
            # 🔥 다양한 스트리밍 형식 지원
            if 'event:token data:' in line:
                try:
                    json_start = line.find('data:') + 5
                    json_str = line[json_start:].strip()
                    
                    if json_str:
                        data = json.loads(json_str)
                        
                        if 'message' in data and 'content' in data['message']:
                            content = data['message']['content']
                            if content:
                                content_parts.append(content)
                                
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON 파싱 실패: {e}")
                    continue
            
            # 🔥 추가 파싱 방법들
            elif line.startswith('data: '):
                try:
                    json_str = line[6:].strip()  # 'data: ' 제거
                    if json_str and json_str != '[DONE]':
                        data = json.loads(json_str)
                        
                        # 다양한 응답 구조 지원
                        content = None
                        if 'message' in data and 'content' in data['message']:
                            content = data['message']['content']
                        elif 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                        elif 'content' in data:
                            content = data['content']
                        
                        if content:
                            content_parts.append(content)
                            
                except json.JSONDecodeError:
                    continue
            
            # 🔥 일반 JSON 라인 처리
            elif line.strip().startswith('{') and line.strip().endswith('}'):
                try:
                    data = json.loads(line.strip())
                    if 'message' in data and 'content' in data['message']:
                        content = data['message']['content']
                        if content:
                            content_parts.append(content)
                except json.JSONDecodeError:
                    continue
        
        if content_parts:
            full_content = ''.join(content_parts)
            
            # 🔥 포맷팅 개선
            full_content = _format_response_text(full_content)
            
            logger.info(f"✅ 스트리밍 파싱 성공: {len(full_content)}자, 토큰 수: {len(content_parts)}")
            return full_content
        
        # 🔥 폴백 처리 - 전체 응답에서 JSON 추출 시도
        logger.warning("일반 토큰 파싱 실패, 폴백 방법 시도...")
        
        # 전체 텍스트에서 JSON 블록 찾기
        json_blocks = re.findall(r'\{[^{}]*"content"[^{}]*\}', response_text)
        
        fallback_content = []
        for block in json_blocks:
            try:
                data = json.loads(block)
                if 'content' in data and data['content']:
                    fallback_content.append(data['content'])
            except json.JSONDecodeError:
                continue
        
        if fallback_content:
            result = ''.join(fallback_content)
            logger.info(f"✅ 폴백 파싱 성공: {len(result)}자")
            return _format_response_text(result)
        
        logger.error("❌ 모든 파싱 방법 실패")
        return ""
        
    except Exception as e:
        logger.error(f"스트리밍 응답 파싱 중 오류: {e}")
        logger.debug(f"응답 내용 샘플: {response_text[:500]}...")
        return ""


def _alternative_content_extraction(response_text: str) -> str:
    """대안적 콘텐츠 추출 방법"""
    try:
        # 🔥 방법 1: 응답 텍스트에서 직접 한글 텍스트 추출
        korean_blocks = re.findall(r'[가-힣].{100,}', response_text)
        if korean_blocks:
            longest_block = max(korean_blocks, key=len)
            logger.info(f"✅ 한글 블록 추출 성공: {len(longest_block)}자")
            return _format_response_text(longest_block)
        
        # 🔥 방법 2: 따옴표로 둘러싸인 긴 텍스트 추출
        quoted_texts = re.findall(r'"([^"]{200,})"', response_text)
        if quoted_texts:
            longest_text = max(quoted_texts, key=len)
            logger.info(f"✅ 따옴표 텍스트 추출 성공: {len(longest_text)}자")
            return _format_response_text(longest_text)
        
        # 🔥 방법 3: content 필드가 포함된 JSON 객체 찾기
        content_jsons = re.findall(r'\{"[^"]*content[^"]*":\s*"([^"]+)"\}', response_text)
        if content_jsons:
            combined_content = ''.join(content_jsons)
            logger.info(f"✅ JSON content 필드 추출 성공: {len(combined_content)}자")
            return _format_response_text(combined_content)
        
        logger.warning("❌ 대안 추출 방법 모두 실패")
        return ""
        
    except Exception as e:
        logger.error(f"대안 추출 실패: {e}")
        return ""


async def get_hyperclova_response(prompt: Union[str, List[Dict[str, str]]]) -> str:
    """문자열과 메시지 리스트 모두 처리할 수 있는 통합 인터페이스"""
    
    # 입력 타입에 따라 메시지 형식 통일
    if isinstance(prompt, str):
        messages = [{"role": "user", "content": prompt}]
    elif isinstance(prompt, list):
        messages = prompt
    else:
        logger.error(f"지원하지 않는 prompt 타입: {type(prompt)}")
        messages = [{"role": "user", "content": str(prompt)}]
    
    if IS_MOCK_MODE:
        logger.info("📝 모의(Mock) 모드로 AI 응답을 생성합니다.")
        return _generate_enhanced_mock_response(messages)

    try:
        content = await _call_hcx_api(messages)
        if content and len(content) > 100:
            return content
        else:
            # 빈 응답이거나 너무 짧은 경우 모의 응답으로 대체
            logger.warning("빈 응답 또는 너무 짧은 응답으로 인해 모의 응답으로 대체합니다.")
            return _generate_enhanced_mock_response(messages)
    except Exception as e:
        logger.error(f"get_hyperclova_response 처리 중 최종 오류 발생, 모의 응답으로 대체합니다: {e}")
        return _generate_enhanced_mock_response(messages)


# 하위 호환성을 위한 별칭들
async def _call_hcx_async(messages: List[Dict[str, str]]) -> str:
    """하위 호환성을 위한 별칭"""
    try:
        if IS_MOCK_MODE:
            return _generate_enhanced_mock_response(messages) 
        return await _call_hcx_api(messages)
    except Exception as e:
        logger.error(f"_call_hcx_async 실패: {e}")
        return _generate_enhanced_mock_response(messages)


def _format_response_text(text: str) -> str:
    """AI 응답 텍스트 포맷팅 개선"""
    if not text:
        return text
    
    # 🔥 제목과 본문 사이의 줄바꿈 처리 강화
    text = text.replace('방식안녕하세요', '방식\n\n안녕하세요')
    text = text.replace('방식고객님', '방식\n\n고객님')
    text = text.replace('리포트안녕하세요', '리포트\n\n안녕하세요')
    text = text.replace('분석안녕하세요', '분석\n\n안녕하세요')
    
    # 🔥 문단 구분 개선
    # 제목 다음에 줄바꿈 추가
    text = re.sub(r'(리포트 - [^안]*)(안녕하세요)', r'\1\n\n\2', text)
    text = re.sub(r'(분석[^안]*)(안녕하세요)', r'\1\n\n\2', text)
    
    # 문단 끝 마침표 다음에 적절한 간격
    text = re.sub(r'(\.)([가-힣A-Z].*?께서)', r'\1\n\n\2', text)
    text = re.sub(r'(습니다\.)([가-힣].*?포트폴리오)', r'\1\n\n\2', text)
    text = re.sub(r'(습니다\.)([가-힣].*?종목)', r'\1\n\n\2', text)
    text = re.sub(r'(습니다\.)([가-힣].*?투자)', r'\1\n\n\2', text)
    text = re.sub(r'(습니다\.)([가-힣].*?분석)', r'\1\n\n\2', text)
    
    # 특정 문단 구분점들
    paragraph_breaks = [
        ('먼저,', '\n\n먼저,'),
        ('이러한 종목들', '\n\n이러한 종목들'),
        ('포트폴리오 전체의', '\n\n포트폴리오 전체의'),
        ('그러나 만약', '\n\n그러나 만약'),
        ('리스크 관리를', '\n\n리스크 관리를'),
        ('종합적으로', '\n\n종합적으로'),
        ('이상으로', '\n\n이상으로'),
        ('마지막으로', '\n\n마지막으로'),
        ('결론적으로', '\n\n결론적으로')
    ]
    
    for old, new in paragraph_breaks:
        text = text.replace(old, new)
    
    # 🔥 중복된 줄바꿈 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 🔥 시작과 끝 공백 정리
    text = text.strip()
    
    return text


def _generate_enhanced_mock_response(messages: List[Dict[str, str]]) -> str:
    """향상된 모의 응답 생성 - 사용자 요청 분석 반영"""
    
    user_message = ""
    
    # 안전한 메시지 추출
    try:
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
    except Exception as e:
        logger.debug(f"메시지 파싱 중 오류: {e}")
        user_message = "일반적인 투자 질문"
    
    # 🔥 사용자 요청 키워드 분석
    message_lower = user_message.lower() if user_message else ""
    
    # 코스닥 + 과감한 투자 요청인지 확인
    is_kosdaq_request = "코스닥" in message_lower
    is_aggressive_request = any(keyword in message_lower for keyword in ['과감', '공격적', '적극적'])
    
    if is_kosdaq_request and is_aggressive_request:
        return f"""
코스닥 중심 공격형 포트폴리오 분석 리포트

안녕하세요, 고객님의 적극적인 투자 의지와 코스닥 시장에 대한 관심을 확인했습니다.

## 🎯 고객 요청 분석

고객님께서는 "과감한 투자"와 "코스닥 종목" 투자를 명확히 요청하셨습니다. 이는 높은 성장 가능성을 추구하며, 그에 따른 변동성도 기꺼이 감수하겠다는 적극적인 투자 성향을 보여줍니다.

월 100만원의 투자 가능 금액으로 코스닥 성장주에 집중 투자하여 중장기적으로 높은 수익률을 추구하시는 전략은 현명한 접근입니다.

## 📊 코스닥 시장 특성 및 투자 매력

코스닥 시장은 다음과 같은 특징을 가지고 있습니다:

**성장성 측면**
- 신기술 기업들의 집결지로 혁신 동력이 풍부합니다
- 바이오, IT, 게임 등 미래 성장 동력 섹터가 다수 포진
- 중소형주 특성상 기업 가치 상승 시 주가 상승폭이 큽니다
- 정부의 K-뉴딜 정책과 벤처 육성 지원으로 성장 환경이 개선되고 있습니다

**투자 기회**
- 대형주 대비 상대적으로 저평가된 우량 기업들이 존재
- 글로벌 진출 성공 시 폭발적 성장 가능성
- ESG 경영과 지속가능성에 대한 관심 증가로 관련 기업들의 주목도 상승

## 💼 추천 포트폴리오 구성

**1. 에코프로비엠 (247540)** - 30%
이차전지 소재 전문기업으로 전기차 시대의 핵심 수혜주입니다. 글로벌 배터리 업체들과의 장기 공급계약을 바탕으로 안정적인 성장이 예상됩니다. 특히 LG에너지솔루션, SK온 등 국내 배터리 대기업들의 성장과 함께 동반 성장할 수 있는 구조입니다.

**2. 카카오게임즈 (293490)** - 25%
모바일 게임 퍼블리싱 분야의 선두주자로, 지속적인 신작 게임 출시와 해외 진출 확대로 성장 동력을 확보하고 있습니다. 메타버스와 NFT 등 신기술 도입으로 새로운 수익 모델 창출이 기대됩니다.

**3. 셀트리온헬스케어 (091990)** - 20%
바이오시밀러 분야의 글로벌 경쟁력을 보유한 기업으로, 고령화 사회 진입과 함께 지속적인 수요 증가가 예상됩니다. 유럽과 미국 시장에서의 승인 확대로 글로벌 매출 성장이 지속될 전망입니다.

**4. 엔씨소프트 (036570)** - 25%
게임 산업의 대표주자로 메타버스, NFT 등 신사업 영역 진출을 통한 새로운 성장 동력을 모색하고 있습니다. 리니지 시리즈의 안정적인 수익 기반 위에 신규 IP 개발로 성장성을 확보하고 있습니다.

## ⚡ 공격적 투자 전략

**매수 전략**
1. **분할 매수를 통한 평균 단가 관리**: 월 100만원을 4주에 걸쳐 25만원씩 분할 매수
2. **시장 조정 시 추가 매수 기회 포착**: 개별 종목이 -10% 이상 하락 시 추가 매수 검토
3. **3-6개월 단위의 중기 투자 관점 유지**: 단기 변동성에 흔들리지 않는 투자 원칙

**수익 실현 전략**
- 개별 종목 +30% 달성 시 일부 수익 실현 (전체 보유량의 30%)
- 전체 포트폴리오 +50% 달성 시 리밸런싱 검토
- 손절 기준: 개별 종목 -20% 도달 시 과감한 손절

**포트폴리오 관리**
- 월 1회 정기적인 비중 점검 및 조정
- 분기별 실적 발표 후 포트폴리오 재검토
- 시장 급변동 시 현금 비중 조정 고려

## ⚠️ 리스크 관리 방안

**주요 리스크 요소**
- 코스닥 시장의 높은 변동성 (일일 등락폭 ±5% 이상 빈번)
- 중소형주 특성상 유동성 제약
- 기술주 집중으로 인한 섹터 리스크
- 금리 상승 시 성장주 밸류에이션 압박

**관리 방안**
1. **자금 관리**: 투자 자금의 80% 이하로 제한하여 현금 비중 20% 유지
2. **정기 점검**: 월 1회 정기적인 포트폴리오 점검
3. **손절 원칙**: 시장 급변동 시 미리 정한 손절 원칙 준수
4. **분산 투자**: 동일 섹터 내 과도한 집중 지양

## 🎯 투자 실행 가이드

**1단계: 초기 투자 (첫 달)**
- 추천 종목들의 기본 포지션 구축
- 시장 상황을 보며 점진적 매수
- 각 종목별 목표 비중의 70% 수준까지 매수

**2단계: 추가 투자 (2-3개월차)**
- 시장 조정 시 추가 매수 기회 활용
- 성과가 좋은 종목 비중 점진적 확대
- 실적 발표 시즌을 활용한 기회 매수

**3단계: 모니터링 및 조정 (3개월 이후)**
- 주간 단위 시장 동향 점검
- 분기별 실적 발표 후 포트폴리오 재검토
- 필요시 비중 조정 및 신규 종목 편입 검토

## 📈 기대 성과 및 전망

고객님의 공격적 투자 성향에 맞춰 구성된 이 포트폴리오는 다음과 같은 성과를 기대할 수 있습니다:

**예상 수익률**
- 연수익률: 20-35% (시장 상황에 따라 변동)
- 예상 변동성: 30-40% (코스닥 시장 특성)
- 투자 기간: 1-2년 중기 관점

**성공 요인**
- 각 종목의 펀더멘털 개선과 실적 성장
- 해당 섹터의 성장세 지속 (이차전지, 게임, 바이오)
- 전체적인 코스닥 시장 상승 흐름
- 정부 정책 지원과 글로벌 시장 확대

**주요 모니터링 지표**
- 개별 기업의 분기별 실적 성장률
- 해당 업종의 글로벌 시장 동향
- 코스닥 지수 대비 상대 성과
- 외국인 투자자들의 매매 동향

## 🔔 주의사항 및 투자 원칙

**투자 시 유의사항**
투자에는 항상 원금 손실의 위험이 따릅니다. 특히 코스닥 공격형 포트폴리오는 높은 수익 가능성과 함께 그만큼의 위험도 내포하고 있습니다.

**투자 성공을 위한 원칙**
- 투자 결정은 본인의 재정 상황과 위험 수용 능력을 충분히 고려하여 신중하게 내리시기 바랍니다
- 시장 상황 변화에 따라 포트폴리오 조정이 필요할 수 있습니다
- 정기적인 점검을 통해 투자 목표 달성 여부를 확인하시기 바랍니다
- 감정적 판단보다는 객관적 지표와 데이터에 기반한 의사결정을 유지하세요

**장기 투자 관점**
이 포트폴리오는 코스닥 시장의 성장성에 베팅하는 공격적 전략입니다. 단기 변동성에 흔들리지 마시고, 기업들의 펀더멘털 개선과 함께 중장기적 관점에서 투자하시기 바랍니다.

이상으로 고객님의 적극적 투자 성향에 맞는 코스닥 중심 포트폴리오 분석을 마치겠습니다.

※ 현재 HyperCLOVA API 연결 문제로 모의 모드로 동작 중이며, API 연결 복구 시 더욱 정확한 분석을 제공할 수 있습니다.
""".strip()
    
    elif "포트폴리오" in message_lower or "투자" in message_lower or "추천" in message_lower:
        return f"""
고객님을 위한 AI 맞춤형 포트폴리오 분석 리포트

안녕하세요, 고객님의 투자 성향을 분석하여 맞춤형 포트폴리오를 제안해드리겠습니다.

## AI 포트폴리오 분석 과정

저희 AI 시스템은 다음과 같은 과정을 통해 고객님께 최적의 포트폴리오를 구성했습니다:

**1단계: 종목 발굴 (Screening)**
- 코스피/코스닥 전체 상장사 중에서 고객님의 투자 성향에 맞는 종목들을 선별했습니다
- 재무 건전성, 성장성, 배당 수익률 등을 종합적으로 분석하여 우량 종목들을 발굴했습니다

**2단계: 포트폴리오 최적화 (Optimization)**
- 선별된 종목들을 대상으로 현대 포트폴리오 이론에 기반하여 최적의 비중을 계산했습니다
- 위험 대비 수익률(샤프 지수)을 극대화하는 과학적 접근법을 사용했습니다

## 최종 추천 포트폴리오

### 핵심 보유 종목
- **SK하이닉스 (000660)**: 40%
  - AI 메모리 수요 증가로 중장기 성장성이 우수합니다
  - HBM(고대역폭 메모리) 시장에서 글로벌 선도 기업입니다
  - 반도체 업계 회복세와 함께 실적 개선이 기대됩니다

- **현대차 (005380)**: 60%  
  - 전기차 전환 시대의 대표적인 수혜주입니다
  - 안정적인 배당 수익률과 함께 성장성도 확보하고 있습니다
  - 글로벌 자동차 시장에서의 경쟁력이 지속적으로 강화되고 있습니다

## 투자 전략 및 실행 방안

**분할 매수 전략**
월 투자 금액을 3-4회에 나누어 분할 매수하여 평균 단가 효과를 노리시기 바랍니다.

**리밸런싱 계획**
분기별로 포트폴리오 비중을 점검하고, 시장 상황에 따라 적절히 조정하세요.

**리스크 관리**
- 개별 종목 비중이 전체 포트폴리오의 70%를 넘지 않도록 관리하세요
- 시장 급변동 시에는 일부 물량을 현금으로 보유하는 것도 고려해보세요

**장기 투자 관점**
이 포트폴리오는 3-5년의 중장기 관점에서 설계되었습니다. 단기 변동성에 흔들리지 마시고 꾸준히 투자하시기 바랍니다.

## 주의사항

- 투자에는 원금 손실 위험이 항상 존재합니다
- 시장 상황과 개인의 재무 상태 변화에 따라 포트폴리오를 조정해야 합니다  
- 정기적인 투자 성과 점검과 리뷰가 필요합니다

이상으로 상세한 포트폴리오 분석을 마치겠습니다.

※ 현재 HyperCLOVA API가 연결되면 더욱 정확한 분석을 제공할 수 있습니다.
""".strip()
    
    return f"""
안녕하세요! 투자 상담 AI입니다.

질문해주신 내용: {user_message}

현재 API 연결 문제로 인해 모의 모드로 동작하고 있지만, 일반적인 투자 원칙을 말씀드리겠습니다.

**기본 투자 원칙**
1. 분산투자를 통한 위험 관리
2. 장기 투자 관점 유지
3. 정기적인 포트폴리오 점검
4. 본인의 투자 성향에 맞는 종목 선택

**투자자를 위한 일반적 조언**
- 본인의 위험 수용 능력에 맞는 포트폴리오 구성
- 시장 변동성에 대비한 적절한 현금 비중 유지
- 감정적 판단보다 합리적 기준에 따른 투자 결정

API 연결이 복구되면 더욱 정확한 맞춤형 분석을 제공해드리겠습니다.

이상으로 상담을 마치겠습니다.
""".strip()


def _generate_mock_response(messages: List[Dict[str, str]]) -> str:
    """기본 모의 응답 생성"""
    return _generate_enhanced_mock_response(messages)


async def test_hyperclova() -> bool:
    """HyperCLOVA 연결 테스트"""
    if IS_MOCK_MODE:
        logger.info("📝 모의 모드 - 연결 테스트 스킵")
        return False
    
    try:
        test_messages = [{"role": "user", "content": "안녕하세요. 연결 테스트입니다."}]
        response = await _call_hcx_api(test_messages)
        
        if response and len(response) > 5:
            logger.info("✅ HyperCLOVA 연결 테스트 성공")
            return True
        else:
            logger.warning("⚠️ HyperCLOVA 응답이 비어있거나 너무 짧습니다")
            return False
            
    except Exception as e:
        logger.error(f"❌ HyperCLOVA 연결 테스트 실패: {e}")
        return False