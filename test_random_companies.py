#!/usr/bin/env python3
"""무작위 기업 재무제표 조회 테스트"""

import asyncio
from app.services.ai_agent import chat_with_agent


async def test_random_companies():
    """하드코딩되지 않은 기업들 테스트"""
    
    test_companies = [
        ("에스오일", "010950", "정유 대기업"),
        ("에코프로비엠", "247540", "이차전지 소재 기업"),
        ("동아엘텍", "088130", "전자부품 제조업체"),
        ("숲", "067160", "인터넷 방송 플랫폼"),
        ("위즈코프", "038620", "IT 솔루션 기업")
    ]
    
    print("=== 무작위 기업 재무제표 테스트 ===\n")
    
    for company_name, ticker, description in test_companies:
        print(f"\n{'='*60}")
        print(f"테스트: {company_name} ({ticker}) - {description}")
        print(f"{'='*60}")
        
        # 회사명으로 요청
        result = await chat_with_agent(f"{company_name} 재무제표 보여줘")
        
        # 응답 확인
        response = result.get('message', '')
        
        # 올바른 기업으로 인식했는지 확인
        if company_name in response or ticker in response:
            print(f"✅ {company_name}으로 올바르게 인식됨")
            print(f"응답 일부: {response[:300]}...")
        else:
            print(f"❌ {company_name}을 인식하지 못함")
            print(f"응답: {response[:200]}...")
        
        # 잠시 대기 (API 부하 방지)
        await asyncio.sleep(1)
    
    print("\n\n=== 티커 코드로 직접 요청 테스트 ===")
    
    # 티커 코드로 직접 요청
    test_ticker = "088130"  # 동아엘텍
    result = await chat_with_agent(f"{test_ticker} 재무제표 분석해줘")
    
    if "동아엘텍" in result.get('message', '') or test_ticker in result.get('message', ''):
        print(f"✅ 티커 {test_ticker}로 올바르게 인식됨")
    else:
        print(f"❌ 티커 {test_ticker}를 인식하지 못함")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(test_random_companies())