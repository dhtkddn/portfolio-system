"""AI 에이전트 사용법 예시 및 테스트."""
import asyncio
import json
from typing import Dict, List

import requests
from app.services.models import ChatRequest, UserProfile

# API 서버 URL
API_BASE_URL = "http://localhost:8000"

class PortfolioAITester:
    """Portfolio AI 시스템 테스터."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
    
    def test_health_check(self) -> bool:
        """API 서버 상태 확인."""
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ 서버 연결 실패: {e}")
            return False
    
    def test_basic_chat(self) -> Dict:
        """기본 채팅 테스트."""
        print("\n🤖 기본 채팅 테스트")
        
        # 사용자 프로필
        user_profile = {
            "age": 35,
            "monthly_income": 400,
            "investment_amount": 1000,
            "experience_level": "초보",
            "risk_tolerance": "중립형",
            "investment_goal": "장기투자",
            "investment_period": "10년"
        }
        
        # 채팅 요청
        chat_request = {
            "message": "월 100만원 정도 투자할 수 있는 35세 직장인입니다. 투자 경험이 별로 없어서 안전하면서도 수익을 낼 수 있는 포트폴리오를 추천해주세요.",
            "user_profile": user_profile,
            "conversation_history": []
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/ai/chat",
                json=chat_request,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ AI 응답 성공")
                print(f"응답 길이: {len(result.get('message', ''))}자")
                print(f"추천 종목 수: {len(result.get('recommendations', []))}")
                
                # 추천 종목 출력
                if result.get('recommendations'):
                    print("\n📈 추천 종목:")
                    for rec in result['recommendations'][:3]:
                        print(f"  - {rec['name']} ({rec['ticker']}): {rec['reason'][:50]}...")
                
                return result
            else:
                print(f"❌ API 오류: {response.status_code}")
                print(response.text)
                return {}
                
        except Exception as e:
            print(f"❌ 요청 실패: {e}")
            return {}
    
    def test_stock_recommendations(self) -> Dict:
        """종목 추천 테스트."""
        print("\n📊 종목 추천 테스트")
        
        # 다양한 시나리오 테스트
        scenarios = [
            {
                "name": "보수적 투자자",
                "message": "안전한 대형주 위주로 포트폴리오를 구성하고 싶어요",
                "profile": {
                    "age": 45,
                    "investment_amount": 5000,
                    "experience_level": "중급",
                    "risk_tolerance": "안전형"
                }
            },
            {
                "name": "성장형 투자자", 
                "message": "젊은 나이니까 좀 더 공격적으로 성장주에 투자하고 싶습니다",
                "profile": {
                    "age": 28,
                    "investment_amount": 500,
                    "experience_level": "초보",
                    "risk_tolerance": "공격형"
                }
            },
            {
                "name": "테마 투자자",
                "message": "요즘 뜨고 있는 AI, 반도체 관련 주식에 투자하고 싶어요",
                "profile": {
                    "age": 32,
                    "investment_amount": 2000,
                    "experience_level": "중급",
                    "risk_tolerance": "중립형"
                }
            }
        ]
        
        results = []
        
        for scenario in scenarios:
            print(f"\n🎯 시나리오: {scenario['name']}")
            
            request_data = {
                "message": scenario["message"],
                "user_profile": scenario["profile"]
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/ai/recommendations",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 추천 성공: {len(result.get('recommendations', []))}개 종목")
                    
                    # 상위 3개 종목만 출력
                    if result.get('recommendations'):
                        for i, rec in enumerate(result['recommendations'][:3], 1):
                            print(f"  {i}. {rec['name']} - 비중: {rec['target_weight']:.1%}")
                    
                    results.append({
                        "scenario": scenario['name'],
                        "success": True,
                        "recommendations": result.get('recommendations', [])
                    })
                else:
                    print(f"❌ 추천 실패: {response.status_code}")
                    results.append({
                        "scenario": scenario['name'],
                        "success": False,
                        "error": response.text
                    })
                    
            except Exception as e:
                print(f"❌ 요청 실패: {e}")
                results.append({
                    "scenario": scenario['name'],
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def test_market_analysis(self) -> Dict:
        """시장 분석 테스트."""
        print("\n📈 시장 분석 테스트")
        
        analysis_requests = [
            {
                "analysis_type": "sector",
                "target": "반도체",
                "time_period": "3M"
            },
            {
                "analysis_type": "stock", 
                "target": "005930",  # 삼성전자
                "time_period": "6M"
            },
            {
                "analysis_type": "market",
                "target": "KOSPI",
                "time_period": "1Y"
            }
        ]
        
        results = []
        
        for req in analysis_requests:
            print(f"\n🔍 분석: {req['analysis_type']} - {req['target']}")
            
            try:
                response = requests.post(
                    f"{self.base_url}/ai/market-analysis",
                    json=req
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("✅ 분석 성공")
                    print(f"요약: {result.get('analysis_summary', '')[:100]}...")
                    
                    results.append({
                        "analysis": f"{req['analysis_type']}-{req['target']}",
                        "success": True,
                        "summary": result.get('analysis_summary', '')
                    })
                else:
                    print(f"❌ 분석 실패: {response.status_code}")
                    results.append({
                        "analysis": f"{req['analysis_type']}-{req['target']}",
                        "success": False,
                        "error": response.text
                    })
                    
            except Exception as e:
                print(f"❌ 요청 실패: {e}")
                results.append({
                    "analysis": f"{req['analysis_type']}-{req['target']}",
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def test_financial_analysis(self) -> Dict:
        """재무 분석 테스트."""
        print("\n💰 재무 분석 테스트")
        
        # 주요 종목들에 대한 재무 분석
        test_tickers = ["005930", "000660", "035420"]  # 삼성전자, SK하이닉스, 네이버
        
        results = []
        
        for ticker in test_tickers:
            print(f"\n📊 {ticker} 재무 분석")
            
            try:
                response = requests.post(
                    f"{self.base_url}/ai/financial-analysis",
                    params={
                        "ticker": ticker,
                        "user_question": "이 회사의 재무 상태가 어떤가요? 투자해도 될까요?"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("✅ 재무 분석 성공")
                    print(f"회사명: {result.get('company_name', 'N/A')}")
                    print(f"투자 등급: {result.get('investment_rating', 'N/A')}")
                    
                    results.append({
                        "ticker": ticker,
                        "success": True,
                        "rating": result.get('investment_rating', 'N/A')
                    })
                else:
                    print(f"❌ 분석 실패: {response.status_code}")
                    results.append({
                        "ticker": ticker,
                        "success": False,
                        "error": response.text
                    })
                    
            except Exception as e:
                print(f"❌ 요청 실패: {e}")
                results.append({
                    "ticker": ticker,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def test_conversation_flow(self) -> Dict:
        """대화형 상담 플로우 테스트."""
        print("\n💬 대화형 상담 플로우 테스트")
        
        # 연속된 대화 시뮬레이션
        conversation_history = []
        
        messages = [
            "안녕하세요! 주식 투자를 처음 시작하려고 하는데 도움을 받을 수 있나요?",
            "월 소득이 300만원 정도이고, 매월 50만원 정도 투자할 수 있어요.",
            "리스크는 너무 크지 않았으면 좋겠고, 장기적으로 안정적인 수익을 원해요.",
            "추천해주신 종목들 중에서 삼성전자가 정말 좋은 선택일까요?",
            "포트폴리오를 언제 리밸런싱해야 하나요?"
        ]
        
        user_profile = {
            "age": 30,
            "monthly_income": 300,
            "investment_amount": 50,
            "experience_level": "초보",
            "risk_tolerance": "안전형",
            "investment_goal": "장기투자",
            "investment_period": "10년 이상"
        }
        
        results = []
        
        for i, message in enumerate(messages, 1):
            print(f"\n👤 사용자 메시지 {i}: {message}")
            
            request_data = {
                "message": message,
                "user_profile": user_profile if i == 1 else None,  # 첫 번째만 프로필 전송
                "conversation_history": conversation_history
            }
            
            try:
                response = requests.post(
                    f"{self.base_url}/ai/chat",
                    json=request_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_message = result.get('message', '')
                    
                    print(f"🤖 AI 응답: {ai_message[:150]}...")
                    
                    # 대화 히스토리 업데이트
                    conversation_history.append({
                        "role": "user",
                        "content": message,
                        "timestamp": "2024-01-01T00:00:00"
                    })
                    conversation_history.append({
                        "role": "assistant", 
                        "content": ai_message,
                        "timestamp": "2024-01-01T00:00:00"
                    })
                    
                    # 최근 10개 메시지만 유지
                    if len(conversation_history) > 10:
                        conversation_history = conversation_history[-10:]
                    
                    results.append({
                        "turn": i,
                        "success": True,
                        "response_length": len(ai_message),
                        "has_recommendations": bool(result.get('recommendations'))
                    })
                    
                else:
                    print(f"❌ 응답 실패: {response.status_code}")
                    results.append({
                        "turn": i,
                        "success": False,
                        "error": response.text
                    })
                    break
                    
            except Exception as e:
                print(f"❌ 요청 실패: {e}")
                results.append({
                    "turn": i,
                    "success": False,
                    "error": str(e)
                })
                break
        
        return results
    
    def run_comprehensive_test(self) -> Dict:
        """전체 시스템 테스트 실행."""
        print("🚀 Portfolio AI 시스템 종합 테스트 시작")
        print("=" * 60)
        
        test_results = {
            "health_check": False,
            "basic_chat": {},
            "stock_recommendations": [],
            "market_analysis": [],
            "financial_analysis": [],
            "conversation_flow": [],
            "overall_success": False
        }
        
        # 1. 헬스 체크
        print("\n1️⃣ 서버 상태 확인")
        test_results["health_check"] = self.test_health_check()
        
        if not test_results["health_check"]:
            print("❌ 서버 연결 실패. 테스트 중단.")
            return test_results
        
        # 2. 기본 채팅 테스트
        print("\n2️⃣ 기본 채팅 기능 테스트")
        test_results["basic_chat"] = self.test_basic_chat()
        
        # 3. 종목 추천 테스트
        print("\n3️⃣ 종목 추천 기능 테스트")
        test_results["stock_recommendations"] = self.test_stock_recommendations()
        
        # 4. 시장 분석 테스트
        print("\n4️⃣ 시장 분석 기능 테스트")
        test_results["market_analysis"] = self.test_market_analysis()
        
        # 5. 재무 분석 테스트
        print("\n5️⃣ 재무 분석 기능 테스트")
        test_results["financial_analysis"] = self.test_financial_analysis()
        
        # 6. 대화형 상담 테스트
        print("\n6️⃣ 대화형 상담 플로우 테스트")
        test_results["conversation_flow"] = self.test_conversation_flow()
        
        # 전체 결과 평가
        success_count = 0
        total_tests = 0
        
        # 각 테스트 성공률 계산
        if test_results["basic_chat"]:
            success_count += 1
        total_tests += 1
        
        for test_group in ["stock_recommendations", "market_analysis", "financial_analysis", "conversation_flow"]:
            if test_results[test_group]:
                group_success = sum(1 for test in test_results[test_group] if test.get("success", False))
                group_total = len(test_results[test_group])
                if group_total > 0:
                    success_count += group_success / group_total
                total_tests += 1
        
        overall_success_rate = success_count / total_tests if total_tests > 0 else 0
        test_results["overall_success"] = overall_success_rate > 0.8
        
        # 최종 리포트
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)
        print(f"전체 성공률: {overall_success_rate:.1%}")
        print(f"서버 상태: {'✅ 정상' if test_results['health_check'] else '❌ 이상'}")
        print(f"기본 채팅: {'✅ 성공' if test_results['basic_chat'] else '❌ 실패'}")
        
        for test_name in ["stock_recommendations", "market_analysis", "financial_analysis", "conversation_flow"]:
            if test_results[test_name]:
                success_rate = sum(1 for t in test_results[test_name] if t.get("success", False)) / len(test_results[test_name])
                status = "✅ 성공" if success_rate > 0.8 else "⚠️ 부분성공" if success_rate > 0.5 else "❌ 실패"
                print(f"{test_name.replace('_', ' ').title()}: {status} ({success_rate:.1%})")
        
        if test_results["overall_success"]:
            print("\n🎉 전체 시스템이 정상적으로 동작합니다!")
        else:
            print("\n⚠️ 일부 기능에 문제가 있습니다. 로그를 확인해주세요.")
        
        return test_results


# 실사용 예시 함수들
def example_beginner_consultation():
    """초보자 투자 상담 예시."""
    print("\n👨‍💼 초보자 투자 상담 예시")
    
    # 실제 API 호출 예시
    request_data = {
        "message": "30대 직장인이고 매월 100만원씩 투자할 수 있습니다. 주식 투자는 처음인데 어떻게 시작하면 좋을까요?",
        "user_profile": {
            "age": 32,
            "monthly_income": 500,
            "investment_amount": 100,
            "experience_level": "초보",
            "risk_tolerance": "중립형",
            "investment_goal": "장기투자",
            "investment_period": "10년"
        }
    }
    
    # curl 명령어 예시 출력
    print("💻 curl 명령어 예시:")
    print(f"""
curl -X POST "{API_BASE_URL}/ai/chat" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(request_data, ensure_ascii=False, indent=2)}'
""")


def example_advanced_portfolio():
    """고급 포트폴리오 분석 예시."""
    print("\n📊 고급 포트폴리오 분석 예시")
    
    # 종목 추천 요청
    recommendation_data = {
        "message": "IT 업종에 집중 투자하고 싶습니다. ESG 경영을 잘하는 기업들로 포트폴리오를 구성해주세요.",
        "user_profile": {
            "age": 40,
            "investment_amount": 5000,
            "experience_level": "고급",
            "risk_tolerance": "공격형",
            "preferred_sectors": ["IT", "반도체", "인터넷"],
            "investment_goal": "고수익 추구"
        }
    }
    
    print("💻 종목 추천 API 호출 예시:")
    print(f"""
curl -X POST "{API_BASE_URL}/ai/recommendations" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(recommendation_data, ensure_ascii=False, indent=2)}'
""")


def main():
    """메인 테스트 실행."""
    print("🤖 Portfolio AI 시스템 테스트 및 사용법 가이드")
    print("=" * 70)
    
    # 테스터 인스턴스 생성
    tester = PortfolioAITester()
    
    # 종합 테스트 실행
    results = tester.run_comprehensive_test()
    
    # 사용법 예시
    print("\n📚 사용법 예시")
    print("=" * 70)
    
    example_beginner_consultation()
    example_advanced_portfolio()
    
    print("\n🔗 주요 API 엔드포인트:")
    print(f"- 대화형 상담: POST {API_BASE_URL}/ai/chat")
    print(f"- 종목 추천: POST {API_BASE_URL}/ai/recommendations") 
    print(f"- 시장 분석: POST {API_BASE_URL}/ai/market-analysis")
    print(f"- 재무 분석: POST {API_BASE_URL}/ai/financial-analysis")
    print(f"- 기존 포트폴리오: POST {API_BASE_URL}/portfolio/recommend")
    
    print(f"\n📖 API 문서: {API_BASE_URL}/docs")
    
    # 결과를 JSON 파일로 저장
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 테스트 결과가 test_results.json에 저장되었습니다.")


if __name__ == "__main__":
    main()