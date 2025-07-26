# debug_truncation.py - 응답 잘림 문제 디버깅

import asyncio
import json
import logging
from app.services.hyperclova_client import hyperclova_client, _call_hcx_async

# 상세한 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_hyperclova_response_length():
    """HyperCLOVA 응답 길이 테스트"""
    
    test_messages = [
        {
            "role": "system", 
            "content": "당신은 투자 전문가입니다. 상세하고 완전한 답변을 제공하세요."
        },
        {
            "role": "user", 
            "content": "월 100만원 투자 가능한 초보자에게 상세한 포트폴리오를 추천하고 각 종목의 분석, 위험도, 투자 전략을 모두 포함해서 설명해주세요."
        }
    ]
    
    print("🔍 HyperCLOVA 직접 테스트 시작...")
    
    try:
        # 1. 기본 설정으로 테스트
        print("\n1️⃣ 기본 설정 테스트")
        response1 = await hyperclova_client.chat_completion(test_messages)
        print(f"응답 길이: {len(response1)}자")
        print(f"응답 끝부분: ...{response1[-100:]}")
        
        # 2. 더 많은 토큰으로 테스트
        print("\n2️⃣ 높은 토큰 수 테스트")
        response2 = await hyperclova_client.chat_completion(
            test_messages, 
            max_tokens=20000
        )
        print(f"응답 길이: {len(response2)}자")
        print(f"응답 끝부분: ...{response2[-100:]}")
        
        # 3. 응답 비교
        print(f"\n📊 응답 비교:")
        print(f"기본 설정: {len(response1)}자")
        print(f"높은 토큰: {len(response2)}자")
        print(f"차이: {len(response2) - len(response1)}자")
        
        # 4. 응답이 완전한지 확인
        completion_indicators = ["결론", "마무리", "요약", "이상입니다", "감사합니다"]
        
        for i, response in enumerate([response1, response2], 1):
            has_completion = any(indicator in response[-200:] for indicator in completion_indicators)
            print(f"응답 {i} 완성도: {'✅ 완전' if has_completion else '❌ 불완전'}")
        
        return response1, response2
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return None, None

async def test_api_endpoints():
    """API 엔드포인트별 응답 길이 테스트"""
    
    import requests
    
    base_url = "http://localhost:8008"
    
    # 테스트 데이터
    portfolio_data = {
        "tickers": ["005930.KS", "035420.KS"],
        "age": 35,
        "experience": "초보",
        "risk_profile": "중립형",
        "investment_goal": "은퇴준비", 
        "investment_period": "10년"
    }
    
    chat_data = {
        "message": "월 100만원 투자 가능한 초보자에게 상세한 포트폴리오를 추천해주세요",
        "user_profile": {
            "age": 35,
            "investment_amount": 100,
            "experience_level": "초보",
            "risk_tolerance": "중립형"
        }
    }
    
    print("\n🔍 API 엔드포인트 테스트...")
    
    endpoints = [
        ("/portfolio/enhanced-recommend", portfolio_data),
        ("/ai/chat", chat_data)
    ]
    
    for endpoint, data in endpoints:
        try:
            print(f"\n📡 {endpoint} 테스트")
            
            response = requests.post(
                f"{base_url}{endpoint}",
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 응답 길이 분석
                if "explanation" in result:
                    explanation_len = len(result["explanation"])
                    print(f"  explanation: {explanation_len}자")
                    print(f"  끝부분: ...{result['explanation'][-50:]}")
                
                if "detailed_explanation" in result:
                    detailed_len = len(result["detailed_explanation"])
                    print(f"  detailed_explanation: {detailed_len}자")
                    print(f"  끝부분: ...{result['detailed_explanation'][-50:]}")
                
                if "message" in result:
                    message_len = len(result["message"])
                    print(f"  message: {message_len}자")
                    print(f"  끝부분: ...{result['message'][-50:]}")
                    
                # 완성도 체크
                full_text = ""
                if "explanation" in result:
                    full_text += result["explanation"]
                if "detailed_explanation" in result:
                    full_text += result["detailed_explanation"]
                if "message" in result:
                    full_text += result["message"]
                
                completion_indicators = ["결론", "마무리", "요약", "이상입니다", "감사합니다", "."""]
                has_completion = any(indicator in full_text[-100:] for indicator in completion_indicators)
                print(f"  완성도: {'✅ 완전' if has_completion else '❌ 불완전'}")
                
            else:
                print(f"  ❌ HTTP {response.status_code}: {response.text[:200]}")
                
        except Exception as e:
            print(f"  ❌ 요청 실패: {e}")

async def main():
    """메인 디버깅 함수"""
    
    print("🔧 Portfolio AI 응답 잘림 문제 디버깅")
    print("=" * 60)
    
    # 1. HyperCLOVA 직접 테스트
    await test_hyperclova_response_length()
    
    # 2. API 엔드포인트 테스트
    await test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("🎯 디버깅 완료!")

if __name__ == "__main__":
    asyncio.run(main())