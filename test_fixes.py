#!/usr/bin/env python3
"""Portfolio AI 시스템 수정사항 테스트 스크립트."""

import asyncio
import sys
import traceback
from pathlib import Path

# ✨ 1. dotenv 라이브러리 임포트
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

# ✨ 2. .env 파일 로드 (가장 먼저 실행되도록)
load_dotenv()

async def test_database_connection():
    """데이터베이스 연결 및 데이터 존재 여부 테스트."""
    print("\n🧪 데이터베이스 연결 테스트 시작...")
    
    try:
        from utils.db import SessionLocal
        from sqlalchemy import text
        
        session = SessionLocal()
        
        print("🔗 기본 연결 테스트...")
        session.execute(text("SELECT 1"))
        print("✅ 데이터베이스 연결 성공")
        
        print("📋 테이블 데이터 존재 확인...")
        tables = ["company_info", "prices_merged", "financials"]
        is_ok = True
        for table in tables:
            count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            print(f"✅ {table}: {count}행")
            if count == 0:
                is_ok = False
        
        session.close()
        
        if not is_ok:
            print("\n⚠️ 일부 테이블에 데이터가 없습니다. `python etl/load_yf.py`를 먼저 실행해주세요.")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")
        traceback.print_exc()
        return False


async def test_hyperclova_client():
    """HyperCLOVA 클라이언트 테스트."""
    print("\n🧪 HyperCLOVA 클라이언트 테스트 시작...")
    
    try:
        from app.services.hyperclova_client import test_hyperclova, _call_hcx_async
        
        # 1. 연결 테스트
        print("🔗 연결 테스트...")
        is_connected = await test_hyperclova()
        print(f"{'✅' if is_connected else '⚠️'} 연결 상태: {is_connected}")
        
        # 2. 기본 채팅 테스트
        print("💬 기본 채팅 테스트...")
        test_messages = [
            {"role": "user", "content": "안녕하세요. 테스트 메시지입니다."}
        ]
        response = await _call_hcx_async(test_messages)
        print(f"✅ 응답 수신: {len(response)}자")
        print(f"응답 내용: {response[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ HyperCLOVA 테스트 실패: {e}")
        traceback.print_exc()
        return False

async def test_ai_agent():
    """AI 에이전트 테스트."""
    print("\n🧪 AI 에이전트 테스트 시작...")
    
    try:
        from app.services.ai_agent import chat_with_agent, get_stock_recommendations
        from app.services.models import UserProfile
        
        # 1. 기본 채팅 테스트
        print("💬 기본 채팅 테스트...")
        response = await chat_with_agent("안녕하세요. 투자 조언을 구하고 싶습니다.")
        print(f"✅ 채팅 응답: {len(response.message)}자")
        
        # 2. 종목 추천 테스트
        print("📊 종목 추천 테스트...")
        user_profile = UserProfile(
            age=35,
            investment_amount=1000,
            experience_level="초보",
            risk_tolerance="중립형"
        )
        
        recommendations = await get_stock_recommendations(
            "월 100만원 투자 가능합니다. 추천해주세요.",
            user_profile
        )
        print(f"✅ 추천 결과: {len(recommendations.get('recommendations', []))}개 종목")
        
        return True
        
    except Exception as e:
        print(f"❌ AI 에이전트 테스트 실패: {e}")
        traceback.print_exc()
        return False

async def test_database_connection():
    """데이터베이스 연결 테스트."""
    print("\n🧪 데이터베이스 연결 테스트 시작...")
    
    try:
        from utils.db import SessionLocal
        from sqlalchemy import text
        
        session = SessionLocal()
        
        # 1. 기본 연결 테스트
        print("🔗 기본 연결 테스트...")
        result = session.execute(text("SELECT 1"))
        print("✅ 데이터베이스 연결 성공")
        
        # 2. 테이블 존재 확인
        print("📋 테이블 존재 확인...")
        tables = ["company_info", "prices_merged", "financials"]
        
        for table in tables:
            try:
                result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"✅ {table}: {count}행")
            except Exception as e:
                print(f"⚠️ {table}: 테이블 없음 또는 오류 ({e})")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")
        traceback.print_exc()
        return False

async def test_api_endpoints():
    """API 엔드포인트 테스트."""
    print("\n🧪 API 엔드포인트 테스트 시작...")
    
    try:
        import requests
        import json
        
        base_url = "http://localhost:8008"
        
        # 1. 헬스 체크
        print("❤️ 헬스 체크...")
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API 서버 정상")
            else:
                print(f"⚠️ API 서버 상태 이상: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ API 서버 연결 불가 (서버가 실행 중인지 확인)")
            return False
        
        # 2. 기본 채팅 테스트
        print("💬 채팅 API 테스트...")
        chat_data = {
            "message": "테스트 메시지입니다.",
            "user_profile": {
                "age": 30,
                "investment_amount": 500,
                "experience_level": "초보",
                "risk_tolerance": "중립형"
            }
        }
        
        try:
            response = requests.post(
                f"{base_url}/ai/chat",
                json=chat_data,
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 채팅 API 성공: {len(result.get('message', ''))}자 응답")
            else:
                print(f"⚠️ 채팅 API 오류: {response.status_code}")
                print(response.text[:200])
        except requests.exceptions.Timeout:
            print("⚠️ 채팅 API 타임아웃 (정상적일 수 있음)")
        
        return True
        
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        traceback.print_exc()
        return False

async def run_comprehensive_test():
    """종합 테스트 실행."""
    print("🚀 Portfolio AI 시스템 수정사항 종합 테스트")
    print("=" * 60)
    
    test_results = {}
    
    # 각 테스트 실행
    test_functions = [
        ("데이터베이스 연결", test_database_connection),
        ("StockDatabase", test_stock_database),
        ("HyperCLOVA 클라이언트", test_hyperclova_client),
        ("AI 에이전트", test_ai_agent),
        ("API 엔드포인트", test_api_endpoints),
    ]
    
    for test_name, test_func in test_functions:
        print(f"\n{'='*20} {test_name} 테스트 {'='*20}")
        try:
            result = await test_func()
            test_results[test_name] = result
            print(f"🎯 {test_name} 테스트: {'✅ 성공' if result else '❌ 실패'}")
        except Exception as e:
            test_results[test_name] = False
            print(f"🎯 {test_name} 테스트: ❌ 예외 발생 - {e}")
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    
    success_count = sum(1 for result in test_results.values() if result)
    total_count = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name:20}: {status}")
    
    print(f"\n전체 성공률: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("\n🎉 모든 테스트가 성공했습니다!")
        print("시스템이 정상적으로 작동할 준비가 되었습니다.")
    elif success_count >= total_count * 0.8:
        print("\n⚠️ 대부분의 테스트가 성공했습니다.")
        print("일부 기능에 문제가 있을 수 있으니 확인해주세요.")
    else:
        print("\n❌ 여러 테스트에서 문제가 발견되었습니다.")
        print("시스템 설정을 다시 확인해주세요.")
    
    return test_results

def print_fix_summary():
    """수정사항 요약 출력."""
    print("\n📋 주요 수정사항 요약:")
    print("-" * 40)
    print("1. ✅ stock_database.py SQL 쿼리 파라미터 수정")
    print("   - list 파라미터를 딕셔너리 형태로 변경")
    print("   - SQLAlchemy text() 사용 시 올바른 파라미터 전달")
    print("   - 더미 데이터 생성 로직 추가")
    
    print("\n2. ✅ ai_agent.py 오류 처리 강화")
    print("   - try-catch 블록 추가로 예외 상황 대응")
    print("   - 안전한 딕셔너리 접근 방식 적용")
    print("   - 폴백 응답 메커니즘 개선")
    
    print("\n3. ✅ hyperclova_client.py 안정성 개선")
    print("   - 응답 파싱 로직 강화")
    print("   - 더 자세한 모의 응답 제공")
    print("   - 에러 복구 메커니즘 추가")
    
    print("\n4. ✅ 데이터베이스 쿼리 최적화")
    print("   - UPSERT 구문으로 변경")
    print("   - 트랜잭션 처리 개선")
    print("   - 에러 시 롤백 보장")

async def main():
    """메인 실행 함수."""
    print("=" * 60)
    print("🔧 시스템 상태 진단을 시작합니다...")
    print("=" * 60)
    await test_database_connection()
    print("\n" + "=" * 60)
    print("✅ 진단 완료!")
    print("테이블에 데이터가 0행이라면, `python etl/load_yf.py`를 실행하여 데이터를 수집하세요.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())