# debug_yfinance.py - yfinance 데이터 구조 확인용

import yfinance as yf
import pandas as pd

print("🔍 yfinance 데이터 구조 디버깅")
print("=" * 50)

# 삼성전자 데이터 확인
ticker = "005930.KS"
print(f"📊 {ticker} 데이터 구조 분석...")

try:
    # yfinance 다운로드
    data = yf.download(ticker, start="2024-01-01", end="2025-07-31", progress=False)
    
    print(f"✅ 다운로드 성공!")
    print(f"📏 Shape: {data.shape}")
    print(f"🏷️ Columns: {list(data.columns)}")
    print(f"📅 Index: {data.index}")
    print(f"📅 Index name: {data.index.name}")
    print(f"📅 Index type: {type(data.index)}")
    
    print("\n📋 첫 5행 데이터:")
    print(data.head())
    
    print("\n🔄 reset_index() 후:")
    data_reset = data.reset_index()
    print(f"📏 Shape: {data_reset.shape}")
    print(f"🏷️ Columns: {list(data_reset.columns)}")
    print("📋 첫 3행:")
    print(data_reset.head(3))
    
    print("\n🔄 소문자 변환 후:")
    data_reset.columns = [str(col).lower().strip() for col in data_reset.columns]
    print(f"🏷️ Columns: {list(data_reset.columns)}")
    
    # 실제 변환 테스트
    print("\n🧪 데이터 변환 테스트:")
    data_reset['ticker'] = '005930'
    data_reset['source'] = 'yfinance'
    
    # 날짜 컬럼 찾기
    possible_date_names = ['date', 'datetime', 'timestamp', 'time']
    date_column = None
    
    for col in data_reset.columns:
        if any(date_name in col.lower() for date_name in possible_date_names):
            date_column = col
            print(f"✅ 날짜 컬럼 발견: {date_column}")
            break
    
    if date_column is None:
        print("❌ 날짜 컬럼을 찾을 수 없음")
        # 첫 번째 컬럼이 날짜인지 확인
        if len(data_reset.columns) > 0:
            first_col = data_reset.columns[0]
            print(f"🔍 첫 번째 컬럼 확인: {first_col}")
            try:
                pd.to_datetime(data_reset[first_col].iloc[0])
                print(f"✅ 첫 번째 컬럼이 날짜 형태: {first_col}")
                date_column = first_col
            except Exception as e:
                print(f"❌ 첫 번째 컬럼이 날짜가 아님: {e}")
    
    if date_column:
        print(f"🎯 사용할 날짜 컬럼: {date_column}")
        
        # 날짜 변환 테스트
        try:
            data_reset['date'] = pd.to_datetime(data_reset[date_column]).dt.date
            print("✅ 날짜 변환 성공!")
            print(f"📅 변환된 날짜 샘플: {data_reset['date'].head(3).tolist()}")
        except Exception as e:
            print(f"❌ 날짜 변환 실패: {e}")
    
    print("\n🎯 최종 컬럼 상태:")
    print(f"🏷️ Columns: {list(data_reset.columns)}")
    
except Exception as e:
    print(f"❌ 전체 과정 실패: {e}")
    import traceback
    traceback.print_exc()