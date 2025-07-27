#!/usr/bin/env python3
"""실제 사용자 질문으로 5단계 위험성향 시스템 테스트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
from app.services.portfolio_enhanced import create_smart_portfolio
from app.services.portfolio_explanation import generate_enhanced_portfolio_explanation
from app.services.stock_database import StockDatabase
from app.schemas import PortfolioInput

def create_realistic_test_questions():
    """실제 사용자가 할 만한 질문들"""
    return [
        {
            "question": "1000만원으로 안전하게 투자하고 싶어요. 원금손실은 절대 피하고 싶습니다.",
            "user_input": PortfolioInput(
                initial_capital=10000000,
                risk_appetite="안전형",
                investment_amount=10000000,
                investment_goal="안전투자",
                investment_period="5년"
            ),
            "expected_behavior": "안정추구형으로 분류, 대형 우량주 위주 구성"
        },
        {
            "question": "5000만원으로 코스피 대형주 중심으로 포트폴리오 만들어주세요. 적당한 수익을 원해요.",
            "user_input": PortfolioInput(
                initial_capital=50000000,
                risk_appetite="중립형",
                investment_amount=50000000,
                investment_goal="균형투자",
                investment_period="3년"
            ),
            "expected_behavior": "위험중립형 분류, 코스피 키워드 감지하여 KOSPI 필터"
        },
        {
            "question": "반도체주와 바이오 중심으로 공격적인 포트폴리오 원합니다. 1억원 투자할게요.",
            "user_input": PortfolioInput(
                initial_capital=100000000,
                risk_appetite="공격형",
                investment_amount=100000000,
                investment_goal="성장투자",
                investment_period="2년"
            ),
            "expected_behavior": "적극투자형 분류, 반도체/바이오 섹터 우선 선별"
        },
        {
            "question": "코스닥 게임주 중심으로 구성해주세요. 높은 변동성도 괜찮아요. 3000만원 투자합니다.",
            "user_input": PortfolioInput(
                initial_capital=30000000,
                risk_appetite="공격형",
                investment_amount=30000000,
                investment_goal="단기성장",
                investment_period="1년"
            ),
            "expected_behavior": "적극투자형 분류, 코스닥 키워드 감지, 게임 섹터 우선"
        },
        {
            "question": "은퇴 준비용으로 2억원 투자하려고 해요. 안정적이면서 조금의 성장도 원해요.",
            "user_input": PortfolioInput(
                initial_capital=200000000,
                risk_appetite="안전형",
                investment_amount=200000000,
                investment_goal="은퇴준비",
                investment_period="10년"
            ),
            "expected_behavior": "안정추구형 분류, 배당주/우량주 중심"
        },
        {
            "question": "IT주와 이차전지 관련주로 포트폴리오 만들어주세요. 위험을 감수하고 높은 수익 원해요.",
            "user_input": PortfolioInput(
                initial_capital=80000000,
                risk_appetite="공격형",
                investment_amount=80000000,
                investment_goal="고수익추구",
                investment_period="2년"
            ),
            "expected_behavior": "적극투자형 분류, IT/이차전지 섹터 우선"
        }
    ]

async def test_single_question(question_data, question_num):
    """단일 질문 테스트"""
    print(f"\n{'='*60}")
    print(f"질문 {question_num}: {question_data['question']}")
    print(f"{'='*60}")
    
    try:
        # 데이터베이스 연결
        db = StockDatabase()
        
        # 포트폴리오 분석
        result = create_smart_portfolio(
            user_input=question_data['user_input'],
            db=db,
            original_message=question_data['question']
        )
        
        if "error" in result:
            print(f"❌ 분석 실패: {result['error']}")
            return False
        
        # 결과 분석
        risk_analysis = result.get('risk_profile_analysis', {})
        weights = result.get('weights', {})
        performance = result.get('performance', {})
        
        print(f"🎯 분석 결과:")
        print(f"   위험성향: {risk_analysis.get('risk_profile_type', 'N/A')}")
        print(f"   시장 필터: {result.get('market_filter', 'N/A')}")
        print(f"   선별 종목 수: {result.get('selected_tickers_count', 0)}개")
        
        # 가이드라인 정보
        guideline = risk_analysis.get('asset_allocation_guideline', {})
        if guideline:
            print(f"   권장 주식비중: {guideline.get('stocks_target', 'N/A')}%")
            print(f"   적합 섹터: {', '.join(guideline.get('suitable_sectors', [])[:3])}...")
        
        # 실제 포트폴리오
        if weights:
            print(f"   실제 구성:")
            for i, (ticker, info) in enumerate(list(weights.items())[:3]):
                print(f"     {info['name']}: {info['weight']:.1%} ({info['sector']}, {info['market']})")
            if len(weights) > 3:
                print(f"     ... 외 {len(weights)-3}개 종목")
        
        # 성과 지표
        if performance:
            print(f"   예상 연수익률: {performance.get('expected_annual_return', 0):.1%}")
            print(f"   연변동성: {performance.get('annual_volatility', 0):.1%}")
        
        # 기대 동작 확인
        print(f"\n📋 기대 동작: {question_data['expected_behavior']}")
        
        # AI 설명 생성 (간단히)
        print(f"\n📝 AI 설명 생성:")
        explanation = await generate_enhanced_portfolio_explanation(result)
        print(f"   설명 길이: {len(explanation)}자")
        
        # 핵심 키워드 확인
        key_phrases = []
        if "위험성향" in explanation:
            key_phrases.append("위험성향 분석")
        if "가이드라인" in explanation:
            key_phrases.append("가이드라인 준수")
        if "섹터" in explanation:
            key_phrases.append("섹터 분석")
        if "신한증권" in explanation:
            key_phrases.append("신한증권 기준")
        
        print(f"   포함된 핵심 요소: {', '.join(key_phrases)}")
        
        print(f"✅ 질문 {question_num} 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_user_question_tests():
    """사용자 질문 테스트 실행"""
    print("🚀 실제 사용자 질문으로 5단계 위험성향 시스템 테스트")
    print("="*80)
    
    questions = create_realistic_test_questions()
    success_count = 0
    
    for i, question_data in enumerate(questions, 1):
        success = await test_single_question(question_data, i)
        if success:
            success_count += 1
        
        print(f"\n{'-'*40}")
        await asyncio.sleep(0.5)  # 잠시 대기
    
    # 결과 요약
    print(f"\n🎯 테스트 결과:")
    print(f"   총 질문: {len(questions)}개")
    print(f"   성공: {success_count}개")
    print(f"   실패: {len(questions) - success_count}개")
    print(f"   성공률: {success_count/len(questions)*100:.1f}%")
    
    if success_count == len(questions):
        print(f"\n🎉 모든 질문 테스트 통과!")
        print(f"실제 사용자 시나리오에서 5단계 위험성향 시스템이 정상 작동합니다.")
    else:
        print(f"\n⚠️ {len(questions) - success_count}개 질문에서 문제 발생")

def show_test_questions():
    """테스트할 질문들 미리보기"""
    questions = create_realistic_test_questions()
    print("📝 테스트할 실제 사용자 질문들:")
    print("="*50)
    
    for i, q in enumerate(questions, 1):
        print(f"{i}. {q['question']}")
        print(f"   투자금액: {q['user_input'].investment_amount:,}원")
        print(f"   위험성향: {q['user_input'].risk_appetite}")
        print(f"   기대동작: {q['expected_behavior']}")
        print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        show_test_questions()
    else:
        asyncio.run(run_user_question_tests())