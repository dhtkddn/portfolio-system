#!/usr/bin/env python3
"""5단계 위험성향 시스템 다양한 시나리오 테스트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import asyncio
import json
from app.services.portfolio_enhanced import (
    SmartPortfolioAnalysisService, 
    RiskProfileType, 
    AssetAllocationGuideline,
    create_smart_portfolio
)
from app.services.portfolio_explanation import (
    generate_enhanced_portfolio_explanation,
    generate_risk_profile_summary
)
from app.services.stock_database import StockDatabase
from app.schemas import PortfolioInput

def test_risk_profile_classification():
    """위험성향 분류 테스트"""
    print("=== 위험성향 분류 테스트 ===")
    
    test_cases = [
        ("안전형", RiskProfileType.STABILITY_SEEKING),
        ("중립형", RiskProfileType.RISK_NEUTRAL),
        ("공격형", RiskProfileType.ACTIVE_INVESTMENT)
    ]
    
    for simple_profile, expected in test_cases:
        result = RiskProfileType.from_simple_profile(simple_profile)
        print(f"입력: {simple_profile} → 결과: {result.value} (예상: {expected.value})")
        assert result == expected, f"분류 오류: {simple_profile}"
    
    # 점수 기반 테스트
    score_cases = [
        (15, RiskProfileType.STABLE),
        (30, RiskProfileType.STABILITY_SEEKING),
        (50, RiskProfileType.RISK_NEUTRAL),
        (70, RiskProfileType.ACTIVE_INVESTMENT),
        (90, RiskProfileType.AGGRESSIVE)
    ]
    
    for score, expected in score_cases:
        result = RiskProfileType.from_score(score)
        print(f"점수: {score} → 결과: {result.value} (예상: {expected.value})")
        assert result == expected, f"점수 분류 오류: {score}"
    
    print("✅ 위험성향 분류 테스트 통과\n")

def test_asset_allocation_guidelines():
    """자산배분 가이드라인 테스트"""
    print("=== 자산배분 가이드라인 테스트 ===")
    
    for risk_type in RiskProfileType:
        guideline = AssetAllocationGuideline.GUIDELINES[risk_type]
        print(f"\n{risk_type.value}:")
        print(f"  주식: {guideline['stocks']['target']}% ({guideline['stocks']['min']}-{guideline['stocks']['max']}%)")
        print(f"  채권: {guideline['bonds']['target']}% ({guideline['bonds']['min']}-{guideline['bonds']['max']}%)")
        print(f"  현금: {guideline['cash']['target']}%")
        print(f"  설명: {guideline['description']}")
        print(f"  적합섹터: {', '.join(guideline['suitable_sectors'][:3])}...")
        print(f"  단일종목한도: {guideline['max_single_stock']}%")
        print(f"  선호시장: {guideline['preferred_market']}")
        
        # 합계 검증
        total = guideline['stocks']['target'] + guideline['bonds']['target'] + guideline['cash']['target']
        assert abs(total - 100) <= 5, f"자산배분 합계 오류: {total}%"
    
    print("\n✅ 자산배분 가이드라인 테스트 통과\n")

def create_test_scenarios():
    """테스트 시나리오 생성"""
    scenarios = [
        {
            "name": "20대 신입 직장인 (안정추구형)",
            "user_input": PortfolioInput(
                initial_capital=10000000,
                risk_appetite="안전형",
                investment_amount=10000000,
                investment_goal="장기저축",
                investment_period="5년 이상"
            ),
            "message": "안정적으로 투자하고 싶어요. 원금손실은 최대한 피하고 싶습니다.",
            "expected_risk_type": RiskProfileType.STABILITY_SEEKING
        },
        {
            "name": "30대 중견 직장인 (위험중립형)",
            "user_input": PortfolioInput(
                initial_capital=50000000,
                risk_appetite="중립형",
                investment_amount=50000000,
                investment_goal="자산증식",
                investment_period="3-5년"
            ),
            "message": "적당한 수익과 안정성을 모두 원해요. 코스피 대형주 위주로 부탁드립니다.",
            "expected_risk_type": RiskProfileType.RISK_NEUTRAL
        },
        {
            "name": "40대 고소득자 (적극투자형)",
            "user_input": PortfolioInput(
                initial_capital=100000000,
                risk_appetite="공격형",
                investment_amount=100000000,
                investment_goal="공격적성장",
                investment_period="1-3년"
            ),
            "message": "반도체와 바이오 중심으로 공격적인 포트폴리오를 원합니다.",
            "expected_risk_type": RiskProfileType.ACTIVE_INVESTMENT
        },
        {
            "name": "코스닥 성장주 선호 투자자",
            "user_input": PortfolioInput(
                initial_capital=30000000,
                risk_appetite="공격형",
                investment_amount=30000000,
                investment_goal="단기수익",
                investment_period="1년 이하"
            ),
            "message": "코스닥 게임주와 바이오 중심으로 구성해주세요. 높은 변동성도 괜찮습니다.",
            "expected_risk_type": RiskProfileType.ACTIVE_INVESTMENT
        }
    ]
    return scenarios

async def run_portfolio_analysis_test(scenario):
    """포트폴리오 분석 테스트 실행"""
    print(f"\n{'='*50}")
    print(f"시나리오: {scenario['name']}")
    print(f"{'='*50}")
    
    try:
        # 데이터베이스 연결
        db = StockDatabase()
        
        # 포트폴리오 분석 실행
        result = create_smart_portfolio(
            user_input=scenario['user_input'],
            db=db,
            original_message=scenario['message']
        )
        
        if "error" in result:
            print(f"❌ 분석 실패: {result['error']}")
            return False
        
        # 결과 분석
        risk_analysis = result.get('risk_profile_analysis', {})
        actual_risk_type = risk_analysis.get('risk_profile_type', 'N/A')
        
        print(f"📊 분석 결과:")
        print(f"  위험성향: {actual_risk_type}")
        print(f"  선별된 종목 수: {result.get('selected_tickers_count', 0)}")
        print(f"  시장 필터: {result.get('market_filter', 'N/A')}")
        
        # 가이드라인 정보
        guideline = risk_analysis.get('asset_allocation_guideline', {})
        if guideline:
            print(f"  권장 주식비중: {guideline.get('stocks_target', 'N/A')}%")
            print(f"  권장 섹터: {', '.join(guideline.get('suitable_sectors', [])[:3])}...")
            print(f"  선호 시장: {guideline.get('preferred_market', 'N/A')}")
        
        # 실제 포트폴리오 구성
        weights = result.get('weights', {})
        if weights:
            print(f"  실제 구성 ({len(weights)}개 종목):")
            for ticker, info in list(weights.items())[:5]:
                print(f"    {info['name']}: {info['weight']:.1%} ({info['sector']})")
        
        # 성과 지표
        performance = result.get('performance', {})
        if performance:
            print(f"  예상 연수익률: {performance.get('expected_annual_return', 0):.1%}")
            print(f"  연변동성: {performance.get('annual_volatility', 0):.1%}")
            print(f"  샤프비율: {performance.get('sharpe_ratio', 0):.3f}")
        
        # 준수성 검사
        compliance = risk_analysis.get('compliance_check', {})
        if compliance:
            print(f"  섹터 가이드라인 준수: {compliance.get('within_sector_guidelines', 'N/A')}")
            print(f"  단일종목 한도 준수: {compliance.get('single_stock_limit_compliance', 'N/A')}")
        
        # AI 설명 생성 테스트
        print(f"\n📝 AI 설명 생성 테스트:")
        try:
            explanation = await generate_enhanced_portfolio_explanation(result)
            print(f"설명 길이: {len(explanation)}자")
            print(f"설명 미리보기: {explanation[:200]}...")
        except Exception as e:
            print(f"❌ 설명 생성 실패: {e}")
        
        # 위험성향 요약
        risk_summary = generate_risk_profile_summary(actual_risk_type)
        print(f"\n📋 위험성향 요약:")
        print(risk_summary)
        
        print(f"✅ '{scenario['name']}' 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """메인 테스트 실행"""
    print("🚀 5단계 위험성향 시스템 종합 테스트 시작")
    print("="*60)
    
    # 1. 기본 기능 테스트
    test_risk_profile_classification()
    test_asset_allocation_guidelines()
    
    # 2. 시나리오 테스트
    scenarios = create_test_scenarios()
    success_count = 0
    
    for scenario in scenarios:
        success = await run_portfolio_analysis_test(scenario)
        if success:
            success_count += 1
        
        print("\n" + "-"*50)
        await asyncio.sleep(1)  # 잠시 대기
    
    # 3. 결과 요약
    print(f"\n🎯 테스트 결과 요약:")
    print(f"  총 시나리오: {len(scenarios)}개")
    print(f"  성공: {success_count}개")
    print(f"  실패: {len(scenarios) - success_count}개")
    print(f"  성공률: {success_count/len(scenarios)*100:.1f}%")
    
    if success_count == len(scenarios):
        print("\n🎉 모든 테스트 통과!")
    else:
        print(f"\n⚠️ {len(scenarios) - success_count}개 테스트 실패")

if __name__ == "__main__":
    asyncio.run(main())