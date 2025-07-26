#!/usr/bin/env python3
"""재무제표 조회 테스트 스크립트"""

import asyncio
from app.services.ai_agent import chat_with_agent
from app.services.stock_database import stock_database


async def test_financial_requests():
    """재무제표 요청 테스트"""
    
    print("=== 재무제표 조회 테스트 시작 ===\n")
    
    # 테스트 1: 안랩 재무제표
    print("1. 안랩 재무제표 요청")
    result1 = await chat_with_agent("안랩 재무제표 제공해줘")
    print(f"응답 (첫 200자): {result1['message'][:200]}...")
    print("-" * 50)
    
    # 테스트 2: SK하이닉스 재무제표
    print("\n2. SK하이닉스 재무제표 요청")
    result2 = await chat_with_agent("하이닉스 재무제표 제공해달라")
    print(f"응답 (첫 200자): {result2['message'][:200]}...")
    print("-" * 50)
    
    # 테스트 3: 직접 데이터 확인
    print("\n3. 직접 데이터베이스 조회")
    
    # 안랩 데이터
    ahnlab_data = stock_database.get_multi_year_financials('053800')
    print(f"\n안랩(053800) 재무 데이터: {len(ahnlab_data)}개년")
    for data in ahnlab_data[:2]:  # 최근 2년만 표시
        print(f"  - {data['year']}년: 매출 {data['revenue']/100000000:.0f}억원")
    
    # SK하이닉스 데이터
    sk_data = stock_database.get_multi_year_financials('000660')
    print(f"\nSK하이닉스(000660) 재무 데이터: {len(sk_data)}개년")
    for data in sk_data[:2]:  # 최근 2년만 표시
        print(f"  - {data['year']}년: 매출 {data['revenue']/1000000000000:.1f}조원")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(test_financial_requests())