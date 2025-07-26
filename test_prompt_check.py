#!/usr/bin/env python3
"""프롬프트 생성 확인 테스트"""

import asyncio
from app.services.ai_agent import _handle_financial_request, _extract_tickers_from_company_names
from app.services.stock_database import stock_database
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)


async def test_prompt_generation():
    """프롬프트 생성 과정 확인"""
    
    print("=== 프롬프트 생성 테스트 ===\n")
    
    # 1. 티커 추출 확인
    message = "안랩 재무제표 제공해줘"
    tickers = await _extract_tickers_from_company_names(message)
    print(f"추출된 티커: {tickers}")
    
    if tickers:
        ticker = tickers[0]
        
        # 2. 회사 정보 확인
        company_info = stock_database.get_company_info(ticker)
        print(f"회사 정보: {company_info}")
        
        # 3. 재무 데이터 확인
        financial_data = stock_database.get_financials(ticker)
        print(f"단일 재무 데이터: {financial_data}")
        
        # 4. 다년도 재무 데이터 확인
        multi_year_data = stock_database.get_multi_year_financials(ticker)
        print(f"\n다년도 재무 데이터 ({len(multi_year_data)}개년):")
        for data in multi_year_data:
            print(f"  - {data['year']}년: 매출 {data['revenue']/100000000:.0f}억원")
        
        # 5. 프롬프트 생성 (실제 ai_agent.py의 로직 재현)
        if multi_year_data:
            multi_year_summary = "**연도별 재무 성과 추이 (최신 3개년)**\\n"
            for i, year_data in enumerate(multi_year_data):
                year = year_data['year']
                rev = year_data['revenue']
                op = year_data['operating_profit'] 
                net = year_data['net_profit']
                
                # 전년 대비 증감률 계산
                growth_info = ""
                if i < len(multi_year_data) - 1:
                    prev_year_data = multi_year_data[i + 1]
                    revenue_growth = ((rev - prev_year_data['revenue']) / prev_year_data['revenue']) * 100
                    growth_info = f" (매출 전년대비 {revenue_growth:+.1f}%)"
                
                multi_year_summary += f"- **{year}년**: 매출 {rev/1000000000000:.1f}조원, 영업이익 {op/1000000000000:.1f}조원, 순이익 {net/1000000000000:.1f}조원{growth_info}\\n"
            
            latest_data = multi_year_data[0]
            revenue = latest_data['revenue']
            operating_profit = latest_data['operating_profit']
            net_profit = latest_data['net_profit']
            roe = (net_profit / revenue * 100) if revenue > 0 else 0
            latest_year = latest_data['year']
            
            print(f"\n생성될 프롬프트 시작 부분:")
            print(f"**{company_info.get('company_name', f'종목 {ticker}')}({ticker}) 재무제표 분석**")
            print(f"\\n## 기업 개요")
            print(f"- 종목: {company_info.get('company_name', f'종목 {ticker}')} ({ticker})")
            print(f"- 섹터: {company_info.get('sector', '기타')}")
            print(f"\\n## 📊 연도별 재무 데이터")
            print(multi_year_summary[:200] + "...")
    
    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    asyncio.run(test_prompt_generation())