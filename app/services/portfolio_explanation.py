"""5단계 위험성향 기반 포트폴리오 설명 생성"""

import logging
from typing import Dict, Any
from app.services.hyperclova_client import _call_hcx_async

logger = logging.getLogger(__name__)

RISK_PROFILE_EXPLANATIONS = {
    "안정형": {
        "profile_desc": "원금보전을 최우선으로 하며 안정적인 수익을 추구하는 투자성향",
        "allocation_rationale": "주식 5% 이하, 채권 85%, 현금 10%로 구성하여 원금손실 리스크를 최소화",
        "sector_focus": "유틸리티, 통신, 필수소비재 등 경기변동에 둔감한 방어적 섹터 우선",
        "risk_tolerance": "연 2-4% 수준의 안정적 수익률을 목표로 하며 원금손실을 극도로 회피"
    },
    "안정추구형": {
        "profile_desc": "안정성을 중시하되 일정 수준의 수익률을 추구하는 투자성향",
        "allocation_rationale": "주식 20%, 채권 70%, 현금 10%로 구성하여 안정성과 수익성의 균형 추구",
        "sector_focus": "금융, 보험, 전기전자, 화학 등 안정적인 대형주 위주로 구성",
        "risk_tolerance": "연 4-6% 수준의 수익률을 목표로 하며 제한적인 변동성 감수"
    },
    "위험중립형": {
        "profile_desc": "위험과 수익의 균형을 추구하는 중도적 투자성향",
        "allocation_rationale": "주식 45%, 채권 45%, 현금 10%로 구성하여 균형잡힌 포트폴리오 구축",
        "sector_focus": "전기전자, 화학, 자동차, 기계, 건설 등 다양한 섹터로 분산투자",
        "risk_tolerance": "연 6-8% 수준의 수익률을 목표로 하며 중간 수준의 변동성 감수"
    },
    "적극투자형": {
        "profile_desc": "적극적인 수익 추구를 위해 단기 변동성을 감수하는 투자성향",
        "allocation_rationale": "주식 70%, 채권 20%, 현금 10%로 구성하여 성장성 중심의 포트폴리오 구축",
        "sector_focus": "반도체, 이차전지, 바이오, IT, 게임 등 고성장 섹터 집중투자",
        "risk_tolerance": "연 8-12% 수준의 수익률을 목표로 하며 상당한 변동성 감수"
    },
    "공격투자형": {
        "profile_desc": "높은 수익률 추구를 위해 원금손실 위험을 감수하는 투자성향",
        "allocation_rationale": "주식 90%, 채권 10%로 구성하여 최대한의 성장성 추구",
        "sector_focus": "반도체, 바이오, 게임, 인터넷, 신재생에너지 등 혁신적 성장 섹터 집중",
        "risk_tolerance": "연 12%+ 수준의 수익률을 목표로 하며 높은 변동성과 원금손실 위험 감수"
    }
}

async def generate_enhanced_portfolio_explanation(portfolio_result: Dict[str, Any]) -> str:
    """5단계 위험성향 기반 포트폴리오 설명 생성"""
    
    try:
        # 포트폴리오 결과에서 데이터 추출
        weights = portfolio_result.get("weights", {})
        performance = portfolio_result.get("performance", {})
        risk_analysis = portfolio_result.get("risk_profile_analysis", {})
        portfolio_stats = portfolio_result.get("portfolio_stats", {})
        
        risk_profile_type = risk_analysis.get("risk_profile_type", "위험중립형")
        guideline = risk_analysis.get("asset_allocation_guideline", {})
        compliance = risk_analysis.get("compliance_check", {})
        
        # 위험성향 설명 가져오기
        profile_info = RISK_PROFILE_EXPLANATIONS.get(risk_profile_type, RISK_PROFILE_EXPLANATIONS["위험중립형"])
        
        # 종목별 정보 구성
        stock_details = []
        for ticker, info in weights.items():
            stock_details.append(f"- {info['name']}({ticker}): {info['weight']:.1%} (섹터: {info['sector']}, 시장: {info['market']})")
        
        # 섹터 분포 정보
        sector_dist = portfolio_stats.get("sector_distribution", {})
        sector_info = [f"- {sector}: {weight:.1%}" for sector, weight in sector_dist.items()]
        
        # 재무제표 정보 추가 구성
        financial_info = []
        for ticker, info in weights.items():
            try:
                # 간단한 재무 정보 조회 시도
                financial_info.append(f"- {info['name']}({ticker}): 섹터 {info['sector']}, 시가총액 대형주")
            except:
                financial_info.append(f"- {info['name']}({ticker}): 섹터 {info['sector']}")

        context = f"""
다음 포트폴리오에 대해 5단계 위험성향 분류 기준에 따라 상세한 설명을 해주세요:

**투자자 위험성향 분석:**
- 분류: {risk_profile_type}
- 특징: {profile_info['profile_desc']}
- 위험허용도: {profile_info['risk_tolerance']}

**자산배분 가이드라인:**
- 권장 주식 비중: {guideline.get('stocks_target', 'N/A')}%
- 권장 채권 비중: {guideline.get('bonds_target', 'N/A')}%
- 투자 철학: {guideline.get('description', 'N/A')}
- 권장 섹터: {', '.join(guideline.get('suitable_sectors', []))}
- 단일 종목 한도: {guideline.get('max_single_stock_limit', 'N/A')}%

**실제 포트폴리오 구성:**
{chr(10).join(stock_details)}

**종목별 재무 특성:**
{chr(10).join(financial_info)}

**섹터 분산:**
{chr(10).join(sector_info)}

**예상 성과:**
- 연수익률: {performance.get('expected_annual_return', 0):.1%}
- 연변동성: {performance.get('annual_volatility', 0):.1%}  
- 샤프비율: {performance.get('sharpe_ratio', 0):.3f}

**가이드라인 준수 여부:**
- 섹터 가이드라인 준수: {'예' if compliance.get('within_sector_guidelines', False) else '아니오'}
- 단일 종목 한도 준수: {'예' if compliance.get('single_stock_limit_compliance', False) else '아니오'}

다음 내용을 포함해서 설명해주세요:
1. 위험성향에 따른 포트폴리오 구성 근거
2. 자산배분 가이드라인 대비 적합성 분석  
3. 각 종목 선택 이유 (재무건전성 및 섹터별 관점)
4. 재무제표 기반 종목별 투자 매력도
5. 기대수익률과 리스크 분석
6. 투자 시 주의사항 및 모니터링 포인트
"""

        system_prompt = f"""
당신은 20년 경력의 투자 전문가입니다.
5단계 위험성향 분류 체계({risk_profile_type})에 기반하여 포트폴리오를 설명해주세요.

다음 원칙을 준수하여 설명하세요:
1. 투자자의 위험성향에 맞는 근거 중심 설명
2. 증권사 자산배분 가이드라인 준수 여부 명시
3. 금융소비자보호법에 따른 투자위험 고지
4. 개인 투자판단의 중요성 강조
5. 구체적이고 실용적인 조언 제공

설명은 전문적이면서도 이해하기 쉽게 작성해주세요.
특정 증권사 이름은 언급하지 마세요.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        explanation = await _call_hcx_async(messages)
        
        # 중복 제거 - 같은 내용이 반복되는 경우 첫 번째만 반환
        if explanation and len(explanation) > 500:
            # 텍스트를 절반으로 나누어 중복 확인
            mid_point = len(explanation) // 2
            first_half = explanation[:mid_point].strip()
            second_half = explanation[mid_point:].strip()
            
            # 첫 번째 절반이 두 번째 절반에 포함되면 중복으로 판단
            if len(first_half) > 200 and first_half in second_half:
                return first_half
                
        return explanation
        
    except Exception as e:
        logger.error(f"강화된 포트폴리오 설명 생성 실패: {e}")
        return f"포트폴리오 설명 생성에 실패했습니다. 오류: {str(e)}"

def generate_risk_profile_summary(risk_profile_type: str) -> str:
    """위험성향별 간단 요약"""
    profile_info = RISK_PROFILE_EXPLANATIONS.get(risk_profile_type, RISK_PROFILE_EXPLANATIONS["위험중립형"])
    
    return f"""
**{risk_profile_type} 투자자 특징:**
- {profile_info['profile_desc']}
- 자산배분: {profile_info['allocation_rationale']}
- 섹터 선호: {profile_info['sector_focus']}
- 위험허용도: {profile_info['risk_tolerance']}
"""