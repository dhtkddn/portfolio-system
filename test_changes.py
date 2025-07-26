#!/usr/bin/env python3
"""API 응답 완성도 테스트 및 수정 적용 스크립트."""

import asyncio
import requests
import json
import time
from typing import Dict, Any
from dotenv import load_dotenv  # ✨ 1. 상단에 임포트 추가
from pathlib import Path 

def test_api_response_completeness():
    """API 응답 완성도 테스트."""
    
    base_url = "http://localhost:8008"
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "기본 채팅 테스트",
            "endpoint": "/ai/chat",
            "data": {
                "message": "월 100만원 투자 가능한 초보자인데 상세한 추천해주세요",
                "user_profile": {
                    "age": 30,
                    "investment_amount": 100,
                    "experience_level": "초보",
                    "risk_tolerance": "중립형"
                }
            }
        },
        {
            "name": "포트폴리오 추천 테스트",
            "endpoint": "/ai/recommendations",
            "data": {
                "message": "IT 업종 중심으로 성장성 높은 종목들로 포트폴리오 구성해주세요",
                "user_profile": {
                    "age": 35,
                    "investment_amount": 200,
                    "experience_level": "중급",
                    "risk_tolerance": "공격형"
                }
            }
        },
        {
            "name": "강화된 포트폴리오 추천",
            "endpoint": "/portfolio/enhanced-recommend",
            "data": {
                "tickers": ["005930.KS", "035420.KS", "051910.KS"],
                "age": 40,
                "experience": "중급",
                "risk_profile": "중립형",
                "investment_goal": "은퇴준비",
                "investment_period": "10년"
            }
        }
    ]
    
    print("🔍 API 응답 완성도 테스트 시작")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\n📡 {test_case['name']} 테스트")
        print("-" * 40)
        
        try:
            # API 호출
            start_time = time.time()
            
            response = requests.post(
                f"{base_url}{test_case['endpoint']}",
                json=test_case['data'],
                timeout=120  # 2분 타임아웃
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # 응답 분석
                analyze_response_completeness(result, elapsed_time)
                
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                print(f"오류 내용: {response.text[:300]}...")
                
        except requests.exceptions.Timeout:
            print("⏰ 타임아웃 발생 (2분 초과)")
        except requests.exceptions.ConnectionError:
            print("🚨 서버 연결 실패 - 서버가 실행 중인지 확인하세요")
            break
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")

def analyze_response_completeness(result: Dict[Any, Any], elapsed_time: float):
    """응답 완성도 분석."""
    
    print(f"⏱️ 응답 시간: {elapsed_time:.2f}초")
    
    # 주요 응답 필드 분석
    response_fields = ["message", "explanation", "detailed_explanation", "analysis_summary"]
    
    total_length = 0
    complete_responses = 0
    
    for field in response_fields:
        if field in result:
            content = result[field]
            length = len(content)
            total_length += length
            
            print(f"📝 {field}: {length:,}자")
            
            # 완성도 체크
            completion_indicators = [
                "이상으로", "마치겠습니다", "마무리하겠습니다", 
                "결론적으로", "정리하면", "감사합니다"
            ]
            
            incomplete_indicators = [
                "는$", "이$", "을$", "가$", "에$", "로$", "와$", "ETF는"
            ]
            
            is_complete = any(indicator in content[-200:] for indicator in completion_indicators)
            is_incomplete = any(content.endswith(indicator.replace("$", "")) for indicator in incomplete_indicators)
            
            if is_complete and not is_incomplete and length > 1000:
                print(f"  ✅ 완전한 응답 (완성 지시어 발견)")
                complete_responses += 1
            elif length > 2000:
                print(f"  ⚠️ 긴 응답이지만 완성 지시어 없음")
            else:
                print(f"  ❌ 불완전한 응답 (너무 짧거나 중간에 끊어짐)")
                
                # 끊어진 부분 표시
                if length > 50:
                    print(f"  마지막 부분: ...{content[-50:]}")
    
    # 전체 평가
    print(f"\n📊 전체 응답 길이: {total_length:,}자")
    print(f"🎯 완전한 응답 수: {complete_responses}/{len([f for f in response_fields if f in result])}")
    
    if total_length > 3000 and complete_responses > 0:
        print("✅ 응답 품질: 우수")
    elif total_length > 1500:
        print("⚠️ 응답 품질: 보통")
    else:
        print("❌ 응답 품질: 개선 필요")
    
    # 추천 종목이 있는 경우
    if "recommendations" in result and result["recommendations"]:
        print(f"📈 추천 종목 수: {len(result['recommendations'])}개")
        
        for i, rec in enumerate(result["recommendations"][:3], 1):
            print(f"  {i}. {rec.get('name', 'N/A')} ({rec.get('ticker', 'N/A')})")

def test_hyperclova_directly():
    """HyperCLOVA API 직접 테스트."""
    
    print("\n🔬 HyperCLOVA 직접 테스트")
    print("=" * 60)
    
    try:
        import sys
        import os
        
        # 프로젝트 루트 경로 추가
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        sys.path.insert(0, project_root)
        
        # HyperCLOVA 클라이언트 테스트
        async def run_hyperclova_test():
            from app.services.hyperclova_client import _call_hcx_async
            
            test_messages = [
                {
                    "role": "system",
                    "content": "당신은 투자 전문가입니다. 상세하고 완전한 답변을 제공하세요."
                },
                {
                    "role": "user", 
                    "content": """월 100만원 투자 가능한 초보자에게 상세한 포트폴리오를 추천해주세요.

다음을 모두 포함해서 최소 2000자 이상 상세하게 설명해주세요:
1. 추천 종목과 비중
2. 각 종목의 선정 이유
3. 투자 전략과 방법
4. 리스크 관리 방안
5. 실행 단계

반드시 "이상으로 상세한 답변을 마치겠습니다."로 끝내주세요."""
                }
            ]
            
            print("📤 HyperCLOVA API 호출 중...")
            start_time = time.time()
            
            try:
                response = await _call_hcx_async(test_messages)
                elapsed_time = time.time() - start_time
                
                print(f"✅ 응답 수신 완료: {elapsed_time:.2f}초")
                print(f"📏 응답 길이: {len(response):,}자")
                print(f"🔚 응답 끝부분: ...{response[-100:]}")
                
                # 완성도 체크
                completion_check = "이상으로" in response[-200:] or "마치겠습니다" in response[-200:]
                print(f"✅ 완성도: {'완전' if completion_check else '불완전'}")
                
                return response
                
            except Exception as e:
                print(f"❌ HyperCLOVA 호출 실패: {e}")
                return None
        
        # 비동기 함수 실행
        response = asyncio.run(run_hyperclova_test())
        
        if response and len(response) > 2000:
            print("🎉 HyperCLOVA 직접 테스트 성공!")
        else:
            print("⚠️ HyperCLOVA 응답이 짧거나 실패")
            
    except Exception as e:
        print(f"❌ HyperCLOVA 직접 테스트 실패: {e}")

def main():
    """메인 테스트 함수."""
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
    
    print("🧪 Portfolio AI 응답 완성도 종합 테스트")
    print("수정된 코드의 효과를 확인합니다.")
    print("=" * 80)
    
    # 1. API 응답 테스트
    test_api_response_completeness()
    
    # 2. HyperCLOVA 직접 테스트
    test_hyperclova_directly()
    
    # 3. 결론 및 권장사항
    print("\n" + "=" * 80)
    print("🎯 테스트 결론 및 권장사항")
    print("-" * 40)
    print("1. 응답 길이가 2000자 이상이면 ✅ 성공")
    print("2. '이상으로 마치겠습니다' 등 완성 지시어가 있으면 ✅ 완전")
    print("3. 중간에 끊어지거나 500자 미만이면 ❌ 실패")
    print()
    print("📋 문제 해결 체크리스트:")
    print("□ HyperCLOVA API 키가 올바르게 설정되었는가?")
    print("□ max_tokens이 충분히 큰가? (32000 이상 권장)")
    print("□ 시스템 프롬프트에 상세한 응답 요구사항이 있는가?")
    print("□ 응답 확장 로직이 작동하는가?")
    print("□ 타임아웃이 충분한가? (180초 이상)")

if __name__ == "__main__":
    main()