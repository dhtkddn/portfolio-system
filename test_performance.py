#!/usr/bin/env python3
"""
금융소비자보호법 준수 포트폴리오 시스템 성능 테스트
Performance Test for Financial Consumer Protection Act Compliant Portfolio System
"""

import asyncio
import time
import logging
import traceback
from typing import Dict, List, Any
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.schemas import PortfolioInput
from app.services.stock_database import StockDatabase
from app.services.portfolio_enhanced import create_smart_portfolio
from app.services.investor_protection import InvestorProtectionService, InvestorProfile, RiskLevel
from app.services.ai_agent import analyze_portfolio, _handle_portfolio_request

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceTestSuite:
    """포트폴리오 시스템 성능 테스트"""
    
    def __init__(self):
        self.test_results = {}
        self.db = StockDatabase()
        self.protection_service = InvestorProtectionService()
    
    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 금융소비자보호법 준수 포트폴리오 시스템 성능 테스트 시작\n")
        
        # 1. 데이터베이스 연결 테스트
        await self.test_database_connection()
        
        # 2. 투자자 보호 서비스 테스트
        await self.test_investor_protection_service()
        
        # 3. 포트폴리오 생성 성능 테스트
        await self.test_portfolio_creation_performance()
        
        # 4. 다양한 투자자 프로필 테스트
        await self.test_various_investor_profiles()
        
        # 5. API 응답 시간 테스트
        await self.test_api_response_time()
        
        # 6. 메모리 사용량 테스트
        await self.test_memory_usage()
        
        # 결과 출력
        self.print_test_summary()
    
    async def test_database_connection(self):
        """데이터베이스 연결 및 조회 성능 테스트"""
        print("📊 1. 데이터베이스 연결 테스트")
        
        start_time = time.time()
        
        try:
            # 기업 정보 조회
            company_info = self.db.get_company_info("005930")  # 삼성전자
            
            # 재무 정보 조회
            financials = self.db.get_financials("005930")
            
            # 전체 종목 조회
            stocks_df = self.db.get_all_stocks_for_screening()
            
            end_time = time.time()
            
            self.test_results["database_connection"] = {
                "status": "SUCCESS",
                "response_time": f"{end_time - start_time:.3f}초",
                "stocks_count": len(stocks_df),
                "company_info": company_info,
                "financials_keys": list(financials.keys())
            }
            
            print(f"   ✅ 성공 - {end_time - start_time:.3f}초")
            print(f"   📈 수집된 종목 수: {len(stocks_df)}개")
            print(f"   🏢 삼성전자 정보: {company_info.get('company_name', 'N/A')}")
            
        except Exception as e:
            self.test_results["database_connection"] = {
                "status": "FAILED",
                "error": str(e),
                "response_time": f"{time.time() - start_time:.3f}초"
            }
            print(f"   ❌ 실패: {e}")
        
        print()
    
    async def test_investor_protection_service(self):
        """투자자 보호 서비스 테스트"""
        print("🛡️ 2. 투자자 보호 서비스 테스트")
        
        start_time = time.time()
        
        try:
            # 테스트 투자자 프로필
            test_profile = InvestorProfile(
                age=35,
                investment_experience="3-5년",
                investment_goal="장기성장",
                risk_tolerance="보통",
                investment_amount=10000000,  # 1천만원
                total_assets=50000000,       # 5천만원
                income_level=60000000,       # 6천만원
                investment_ratio=0.2
            )
            
            # 투자자 유형 평가
            investor_type = self.protection_service.assess_investor_type(test_profile)
            
            # 위험 등급 계산
            risk_level = self.protection_service.calculate_portfolio_risk_level(0.15)  # 15% 변동성
            
            # 적합성 검증
            is_suitable, suitability_warnings = self.protection_service.check_suitability(
                investor_type, risk_level
            )
            
            # 적정성 검증
            is_appropriate, appropriateness_warnings = self.protection_service.check_appropriateness(
                test_profile, "보통"
            )
            
            # 집중도 위험 체크
            test_weights = {"005930.KS": 0.3, "000660.KS": 0.25, "035420.KS": 0.2, "기타": 0.25}
            concentration_warnings = self.protection_service.check_concentration_risk(test_weights)
            
            # 경고 메시지 생성
            warning_messages = self.protection_service.generate_warning_messages(risk_level)
            
            end_time = time.time()
            
            self.test_results["investor_protection"] = {
                "status": "SUCCESS",
                "response_time": f"{end_time - start_time:.3f}초",
                "investor_type": investor_type.value,
                "risk_level": risk_level.value,
                "is_suitable": is_suitable,
                "is_appropriate": is_appropriate,
                "warnings_count": len(suitability_warnings) + len(appropriateness_warnings) + len(concentration_warnings),
                "risk_warnings_count": len(warning_messages)
            }
            
            print(f"   ✅ 성공 - {end_time - start_time:.3f}초")
            print(f"   👤 투자자 유형: {investor_type.value}")
            print(f"   ⚠️ 위험 등급: {risk_level.value}")
            print(f"   ✔️ 적합성: {is_suitable}, 적정성: {is_appropriate}")
            print(f"   📋 총 경고 메시지: {len(warning_messages)}개")
            
        except Exception as e:
            self.test_results["investor_protection"] = {
                "status": "FAILED",
                "error": str(e),
                "response_time": f"{time.time() - start_time:.3f}초"
            }
            print(f"   ❌ 실패: {e}")
        
        print()
    
    async def test_portfolio_creation_performance(self):
        """포트폴리오 생성 성능 테스트"""
        print("💼 3. 포트폴리오 생성 성능 테스트")
        
        start_time = time.time()
        
        try:
            # 테스트 포트폴리오 입력
            portfolio_input = PortfolioInput(
                initial_capital=10000000,  # 1천만원
                risk_appetite="중립형",
                target_yield=12.0,
                investment_goal="장기투자",
                investment_period="5년",
                age=35,
                experience_level="중급",
                investment_amount=10000000,
                total_assets=50000000,
                income_level=60000000,
                original_message="미래에셋 관련 종목 포함해서 안정적인 포트폴리오 추천해주세요"
            )
            
            # 포트폴리오 생성
            result = create_smart_portfolio(portfolio_input, self.db, portfolio_input.original_message)
            
            end_time = time.time()
            
            if "error" not in result:
                weights = result.get("weights", {})
                performance = result.get("performance", {})
                investor_protection = result.get("investor_protection", {})
                
                self.test_results["portfolio_creation"] = {
                    "status": "SUCCESS",
                    "response_time": f"{end_time - start_time:.3f}초",
                    "portfolio_size": len(weights),
                    "expected_return": performance.get("expected_annual_return", 0),
                    "volatility": performance.get("annual_volatility", 0),
                    "sharpe_ratio": performance.get("sharpe_ratio", 0),
                    "risk_level": investor_protection.get("risk_level", "N/A"),
                    "has_protection_features": bool(investor_protection)
                }
                
                print(f"   ✅ 성공 - {end_time - start_time:.3f}초")
                print(f"   📊 포트폴리오 크기: {len(weights)}개 종목")
                print(f"   📈 예상 수익률: {performance.get('expected_annual_return', 0):.2%}")
                print(f"   📉 변동성: {performance.get('annual_volatility', 0):.2%}")
                print(f"   ⚖️ 샤프 비율: {performance.get('sharpe_ratio', 0):.3f}")
                print(f"   🛡️ 투자자 보호 기능: {'적용됨' if investor_protection else '미적용'}")
                
                # 종목 상위 5개 출력
                sorted_weights = sorted(weights.items(), key=lambda x: x[1]['weight'], reverse=True)
                print("   🏆 상위 종목:")
                for ticker, data in sorted_weights[:5]:
                    print(f"      - {data['name']} ({ticker}): {data['weight']:.1%}")
                
            else:
                self.test_results["portfolio_creation"] = {
                    "status": "FAILED",
                    "error": result.get("error", "Unknown error"),
                    "response_time": f"{end_time - start_time:.3f}초"
                }
                print(f"   ❌ 실패: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.test_results["portfolio_creation"] = {
                "status": "FAILED",
                "error": str(e),
                "response_time": f"{time.time() - start_time:.3f}초"
            }
            print(f"   ❌ 실패: {e}")
            print(f"   🔍 상세 오류:\n{traceback.format_exc()}")
        
        print()
    
    async def test_various_investor_profiles(self):
        """다양한 투자자 프로필 테스트"""
        print("👥 4. 다양한 투자자 프로필 테스트")
        
        test_profiles = [
            {
                "name": "보수적 투자자",
                "profile": PortfolioInput(
                    initial_capital=5000000,
                    risk_appetite="안전형",
                    age=55,
                    experience_level="초보",
                    investment_amount=5000000,
                    total_assets=100000000,
                    income_level=80000000,
                    original_message="안전한 대형주 위주로 포트폴리오 구성해주세요"
                )
            },
            {
                "name": "공격적 투자자", 
                "profile": PortfolioInput(
                    initial_capital=20000000,
                    risk_appetite="공격형",
                    age=28,
                    experience_level="고급",
                    investment_amount=20000000,
                    total_assets=30000000,
                    income_level=120000000,
                    original_message="성장주 위주로 고수익 포트폴리오 구성해주세요"
                )
            },
            {
                "name": "균형 투자자",
                "profile": PortfolioInput(
                    initial_capital=15000000,
                    risk_appetite="중립형",
                    age=40,
                    experience_level="중급",
                    investment_amount=15000000,
                    total_assets=80000000,
                    income_level=100000000,
                    original_message="코스피 코스닥 균형있게 구성해주세요"
                )
            }
        ]
        
        profile_results = {}
        
        for test_case in test_profiles:
            start_time = time.time()
            
            try:
                result = create_smart_portfolio(test_case["profile"], self.db, test_case["profile"].original_message)
                end_time = time.time()
                
                if "error" not in result:
                    investor_protection = result.get("investor_protection", {})
                    performance = result.get("performance", {})
                    
                    profile_results[test_case["name"]] = {
                        "status": "SUCCESS",
                        "response_time": f"{end_time - start_time:.3f}초",
                        "risk_level": investor_protection.get("risk_level", "N/A"),
                        "investor_type": investor_protection.get("investor_type", "N/A"),
                        "is_suitable": investor_protection.get("is_suitable", False),
                        "volatility": performance.get("annual_volatility", 0),
                        "expected_return": performance.get("expected_annual_return", 0)
                    }
                    
                    print(f"   ✅ {test_case['name']}: {end_time - start_time:.3f}초")
                    print(f"      👤 투자자 유형: {investor_protection.get('investor_type', 'N/A')}")
                    print(f"      ⚠️ 위험 등급: {investor_protection.get('risk_level', 'N/A')}")
                    print(f"      ✔️ 적합성: {investor_protection.get('is_suitable', False)}")
                    print(f"      📈 예상 수익률: {performance.get('expected_annual_return', 0):.2%}")
                    
                else:
                    profile_results[test_case["name"]] = {
                        "status": "FAILED",
                        "error": result.get("error", "Unknown error")
                    }
                    print(f"   ❌ {test_case['name']}: 실패 - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                profile_results[test_case["name"]] = {
                    "status": "FAILED", 
                    "error": str(e)
                }
                print(f"   ❌ {test_case['name']}: 실패 - {e}")
        
        self.test_results["various_profiles"] = profile_results
        print()
    
    async def test_api_response_time(self):
        """API 응답 시간 테스트"""
        print("🌐 5. API 응답 시간 테스트")
        
        test_messages = [
            "1천만원으로 안전한 포트폴리오 추천해주세요",
            "미래에셋 관련 종목 포함해서 균형 잡힌 포트폴리오 만들어주세요",
            "코스닥 성장주 위주로 2천만원 투자하고 싶어요"
        ]
        
        user_profile = {
            "investment_amount": 1000,  # 만원 단위
            "risk_tolerance": "중립형",
            "experience_level": "중급",
            "age": 35,
            "total_assets": 5000,
            "income_level": 60000000
        }
        
        api_results = {}
        
        for i, message in enumerate(test_messages, 1):
            start_time = time.time()
            
            try:
                result = await _handle_portfolio_request(message, user_profile)
                end_time = time.time()
                
                api_results[f"test_{i}"] = {
                    "status": "SUCCESS",
                    "response_time": f"{end_time - start_time:.3f}초",
                    "message": message,
                    "has_recommendations": bool(result.get("recommendations")),
                    "has_protection_info": bool(result.get("investor_protection")),
                    "recommendations_count": len(result.get("recommendations", []))
                }
                
                print(f"   ✅ 테스트 {i}: {end_time - start_time:.3f}초")
                print(f"      📝 요청: {message[:50]}...")
                print(f"      📊 추천 종목 수: {len(result.get('recommendations', []))}개")
                print(f"      🛡️ 투자자 보호 정보: {'포함' if result.get('investor_protection') else '미포함'}")
                
            except Exception as e:
                api_results[f"test_{i}"] = {
                    "status": "FAILED",
                    "error": str(e),
                    "message": message
                }
                print(f"   ❌ 테스트 {i}: 실패 - {e}")
        
        self.test_results["api_response"] = api_results
        print()
    
    async def test_memory_usage(self):
        """메모리 사용량 테스트"""
        print("💾 6. 메모리 사용량 테스트")
        
        try:
            import psutil
            process = psutil.Process()
            
            # 테스트 전 메모리 사용량
            memory_before = process.memory_info().rss / 1024 / 1024  # MB
            
            # 여러 포트폴리오 생성으로 메모리 테스트
            for i in range(5):
                portfolio_input = PortfolioInput(
                    initial_capital=10000000 + i * 1000000,
                    risk_appetite=["안전형", "중립형", "공격형"][i % 3],
                    age=30 + i * 5,
                    experience_level="중급",
                    investment_amount=10000000,
                    total_assets=50000000,
                    income_level=60000000,
                    original_message=f"테스트 {i+1} 포트폴리오"
                )
                
                result = create_smart_portfolio(portfolio_input, self.db, portfolio_input.original_message)
            
            # 테스트 후 메모리 사용량
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = memory_after - memory_before
            
            self.test_results["memory_usage"] = {
                "status": "SUCCESS",
                "memory_before_mb": f"{memory_before:.1f}MB",
                "memory_after_mb": f"{memory_after:.1f}MB", 
                "memory_increase_mb": f"{memory_diff:.1f}MB",
                "memory_efficient": memory_diff < 100  # 100MB 이하면 효율적
            }
            
            print(f"   ✅ 성공")
            print(f"   📊 테스트 전: {memory_before:.1f}MB")
            print(f"   📊 테스트 후: {memory_after:.1f}MB")
            print(f"   📈 증가량: {memory_diff:.1f}MB")
            print(f"   ✔️ 메모리 효율성: {'우수' if memory_diff < 100 else '보통'}")
            
        except ImportError:
            self.test_results["memory_usage"] = {
                "status": "SKIPPED",
                "reason": "psutil 라이브러리가 설치되지 않음"
            }
            print("   ⏭️ 건너뜀 (psutil 라이브러리 필요)")
        except Exception as e:
            self.test_results["memory_usage"] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"   ❌ 실패: {e}")
        
        print()
    
    def print_test_summary(self):
        """테스트 결과 요약 출력"""
        print("=" * 70)
        print("📋 테스트 결과 요약")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() 
                          if isinstance(result, dict) and result.get("status") == "SUCCESS")
        failed_tests = sum(1 for result in self.test_results.values() 
                          if isinstance(result, dict) and result.get("status") == "FAILED")
        skipped_tests = sum(1 for result in self.test_results.values() 
                           if isinstance(result, dict) and result.get("status") == "SKIPPED")
        
        print(f"전체 테스트: {total_tests}개")
        print(f"성공: {passed_tests}개 ✅")
        print(f"실패: {failed_tests}개 ❌") 
        print(f"건너뜀: {skipped_tests}개 ⏭️")
        print()
        
        # 상세 결과
        for test_name, result in self.test_results.items():
            if isinstance(result, dict):
                status_icon = {"SUCCESS": "✅", "FAILED": "❌", "SKIPPED": "⏭️"}.get(result.get("status"), "❓")
                print(f"{status_icon} {test_name}: {result.get('status')}")
                
                if result.get("response_time"):
                    print(f"   ⏱️ 응답시간: {result['response_time']}")
                if result.get("error"):
                    print(f"   ❗ 오류: {result['error']}")
            else:
                # various_profiles 같은 중첩된 결과
                print(f"📊 {test_name}:")
                for sub_test, sub_result in result.items():
                    status_icon = {"SUCCESS": "✅", "FAILED": "❌"}.get(sub_result.get("status"), "❓")
                    print(f"   {status_icon} {sub_test}: {sub_result.get('status')}")
        
        print()
        
        # 성능 통계
        response_times = []
        for result in self.test_results.values():
            if isinstance(result, dict) and result.get("response_time"):
                try:
                    time_str = result["response_time"].replace("초", "")
                    response_times.append(float(time_str))
                except:
                    continue
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            print("⚡ 성능 통계:")
            print(f"   평균 응답시간: {avg_time:.3f}초")
            print(f"   최대 응답시간: {max_time:.3f}초") 
            print(f"   최소 응답시간: {min_time:.3f}초")
        
        print("\n🎉 테스트 완료!")
        
        # 시스템 상태 평가
        if failed_tests == 0:
            print("🟢 시스템 상태: 우수 - 모든 테스트 통과")
        elif failed_tests <= 2:
            print("🟡 시스템 상태: 양호 - 일부 개선 필요")
        else:
            print("🔴 시스템 상태: 주의 - 문제 해결 필요")

async def main():
    """메인 테스트 실행"""
    test_suite = PerformanceTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())