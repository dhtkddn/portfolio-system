#!/usr/bin/env python3
"""재무제표 처리 과정 상세 테스트"""

import asyncio
from app.services.ai_agent import _handle_financial_request
from app.services.stock_database import stock_database


async def test_financial_processing():
    """재무제표 처리 과정 테스트"""
    
    print("=== 재무제표 처리 과정 테스트 ===\n")
    
    # 1. 안랩 재무제표 처리
    print("1. 안랩 재무제표 처리")
    result1 = await _handle_financial_request("안랩 재무제표 제공해줘", None)
    
    # 메시지의 처음 부분 확인
    msg_start = result1['message'][:200]
    print(f"응답 시작 부분: {msg_start}...")
    
    # 데이터 소스 확인
    print(f"데이터 소스: {result1.get('data_source', 'N/A')}")
    
    # 안랩으로 인식했는지 확인
    if '안랩' in result1['message'] or 'AhnLab' in result1['message']:
        print("✅ 안랩으로 올바르게 인식됨")
    else:
        print("❌ 안랩으로 인식하지 못함")
    
    print("-" * 50)
    
    # 2. SK하이닉스 재무제표 처리
    print("\n2. SK하이닉스 재무제표 처리")
    result2 = await _handle_financial_request("하이닉스 재무제표 제공해달라", None)
    
    # 메시지의 처음 부분 확인
    msg_start2 = result2['message'][:200]
    print(f"응답 시작 부분: {msg_start2}...")
    
    # 데이터 소스 확인
    print(f"데이터 소스: {result2.get('data_source', 'N/A')}")
    
    # SK하이닉스로 인식했는지 확인
    if '하이닉스' in result2['message'] or 'SK하이닉스' in result2['message'] or 'SK hynix' in result2['message']:
        print("✅ SK하이닉스로 올바르게 인식됨")
    else:
        print("❌ SK하이닉스로 인식하지 못함")
        # 삼성전자로 잘못 인식했는지 확인
        if '삼성' in result2['message']:
            print("⚠️  삼성전자로 잘못 인식됨!")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(test_financial_processing())