#!/usr/bin/env python3
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

# 데이터베이스 연결
engine = create_engine('postgresql+psycopg2://pguser:pgpass@localhost:5432/portfolio')

print("=== PostgreSQL 데이터 현황 확인 ===")

# 1. 전체 종목 수 확인
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            market, 
            COUNT(*) as count,
            COUNT(CASE WHEN sector IS NOT NULL THEN 1 END) as with_sector
        FROM company_info 
        GROUP BY market 
        ORDER BY market
    """))
    
    print("\n1. 전체 종목 수:")
    for row in result:
        print(f"   {row[0]}: {row[1]}개 (섹터정보 {row[2]}개)")

# 2. 가격 데이터 현황
print("\n2. 가격 데이터 현황:")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT ticker) as unique_tickers,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            COUNT(*) as total_records
        FROM prices_merged
    """))
    
    row = result.fetchone()
    print(f"   종목 수: {row[0]}개")
    print(f"   데이터 기간: {row[1]} ~ {row[2]}")
    print(f"   총 레코드: {row[3]:,}개")

# 3. 최근 30일 데이터가 있는 종목
print("\n3. 최근 30일 데이터 현황:")
with engine.connect() as conn:
    thirty_days_ago = datetime.now() - timedelta(days=30)
    result = conn.execute(text("""
        SELECT 
            ci.market,
            COUNT(DISTINCT ci.ticker) as count
        FROM company_info ci
        INNER JOIN prices_merged pm ON ci.ticker = pm.ticker
        WHERE pm.date >= :date_threshold
        GROUP BY ci.market
        ORDER BY ci.market
    """), {"date_threshold": thirty_days_ago})
    
    for row in result:
        print(f"   {row[0]}: {row[1]}개")

# 4. 재무제표 데이터 현황
print("\n4. 재무제표 데이터 현황:")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(DISTINCT ticker) as unique_tickers,
            COUNT(*) as total_records,
            COUNT(CASE WHEN 매출액 IS NOT NULL THEN 1 END) as with_revenue
        FROM financials
    """))
    
    row = result.fetchone()
    print(f"   종목 수: {row[0]}개")
    print(f"   총 레코드: {row[1]}개")
    print(f"   매출액 데이터: {row[2]}개")

# 5. 실제 쿼리 테스트 (portfolio_enhanced.py와 동일)
print("\n5. 실제 쿼리 결과 (KOSDAQ):")
with engine.connect() as conn:
    result = conn.execute(text("""
        WITH stock_data AS (
            SELECT DISTINCT 
                ci.ticker,
                ci.corp_name as name,
                ci.market,
                ci.sector,
                COUNT(DISTINCT pm.date) as price_days,
                MAX(pm.date) as latest_price_date,
                AVG(pm.close) as avg_price,
                MAX(f.매출액) as revenue,
                MAX(f.영업이익) as operating_profit
            FROM company_info ci
            INNER JOIN prices_merged pm ON ci.ticker = pm.ticker
            LEFT JOIN financials f ON ci.ticker = f.ticker
            WHERE pm.date >= CURRENT_DATE - INTERVAL '30 days'
            AND ci.market = 'KOSDAQ'
            GROUP BY ci.ticker, ci.corp_name, ci.market, ci.sector
            HAVING COUNT(DISTINCT pm.date) >= 20
        )
        SELECT COUNT(*) as total_kosdaq_stocks FROM stock_data
    """))
    
    row = result.fetchone()
    print(f"   필터링된 코스닥 종목: {row[0]}개")

print("\n=== 확인 완료 ===")