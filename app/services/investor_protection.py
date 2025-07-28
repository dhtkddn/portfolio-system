"""
금융소비자보호법 준수를 위한 투자자 보호 모듈
Financial Consumer Protection Act Compliance Module
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """투자 위험 등급"""
    VERY_HIGH = "매우높음"  # 초고위험
    HIGH = "높음"         # 고위험
    MEDIUM_HIGH = "다소높음" # 중위험
    MEDIUM = "보통"       # 중위험
    LOW = "낮음"         # 저위험
    VERY_LOW = "매우낮음"  # 초저위험

class InvestorType(Enum):
    """투자자 유형"""
    STABILITY = "안정형"      # 원금보존 추구
    CONSERVATIVE = "안정추구형" # 안정적 수익 추구
    BALANCED = "위험중립형"    # 균형 투자
    GROWTH = "적극투자형"      # 높은 수익 추구
    AGGRESSIVE = "공격투자형"  # 초고수익 추구

@dataclass
class InvestorProfile:
    """투자자 프로필 (적합성 평가용)"""
    age: int
    investment_experience: str  # "없음", "1년미만", "1-3년", "3-5년", "5년이상"
    investment_goal: str       # "단기수익", "장기성장", "노후대비", "자산보전"
    risk_tolerance: str        # "매우낮음", "낮음", "보통", "높음", "매우높음"
    investment_amount: float
    total_assets: float
    income_level: float
    investment_ratio: float    # 총자산 대비 투자금액 비율

class InvestorProtectionService:
    """금융소비자보호법 준수를 위한 투자자 보호 서비스"""
    
    def __init__(self):
        self.risk_warnings = {
            RiskLevel.VERY_HIGH: [
                "⚠️ 이 포트폴리오는 매우 높은 위험을 포함하고 있습니다.",
                "원금 손실 가능성이 매우 높으며, 투자금액 전액 손실도 가능합니다.",
                "변동성이 매우 커 단기간에 큰 손실이 발생할 수 있습니다."
            ],
            RiskLevel.HIGH: [
                "⚠️ 이 포트폴리오는 높은 위험을 포함하고 있습니다.",
                "원금 손실 가능성이 있으며, 상당한 손실이 발생할 수 있습니다.",
                "시장 상황에 따라 수익률 변동이 클 수 있습니다."
            ],
            RiskLevel.MEDIUM_HIGH: [
                "⚠️ 이 포트폴리오는 다소 높은 위험을 포함하고 있습니다.",
                "원금 손실 가능성이 있으며, 일부 손실이 발생할 수 있습니다.",
                "중장기 투자를 권장합니다."
            ],
            RiskLevel.MEDIUM: [
                "이 포트폴리오는 중간 수준의 위험을 포함하고 있습니다.",
                "제한적인 원금 손실 가능성이 있습니다.",
                "안정성과 수익성의 균형을 추구합니다."
            ],
            RiskLevel.LOW: [
                "이 포트폴리오는 낮은 위험 수준을 유지합니다.",
                "원금 손실 가능성이 낮으나 완전히 배제할 수는 없습니다.",
                "안정적인 수익을 추구합니다."
            ],
            RiskLevel.VERY_LOW: [
                "이 포트폴리오는 매우 낮은 위험 수준을 유지합니다.",
                "원금 보존을 최우선으로 합니다.",
                "수익률은 제한적일 수 있습니다."
            ]
        }
    
    def assess_investor_type(self, profile: InvestorProfile) -> InvestorType:
        """투자자 유형 평가 (적합성 원칙)"""
        score = 0
        
        # 나이 평가
        if profile.age < 30:
            score += 3
        elif profile.age < 40:
            score += 2
        elif profile.age < 50:
            score += 1
        elif profile.age < 60:
            score += 0
        else:
            score -= 1
        
        # 투자 경험 평가
        experience_scores = {
            "없음": -1,
            "1년미만": 0,
            "1-3년": 1,
            "3-5년": 2,
            "5년이상": 3
        }
        score += experience_scores.get(profile.investment_experience, 0)
        
        # 위험 감수 성향
        risk_scores = {
            "매우낮음": -2,
            "낮음": -1,
            "보통": 0,
            "높음": 2,
            "매우높음": 3
        }
        score += risk_scores.get(profile.risk_tolerance, 0)
        
        # 투자 비율 평가
        if profile.investment_ratio > 0.5:
            score -= 1  # 과도한 투자는 위험
        elif profile.investment_ratio < 0.1:
            score += 1  # 여유 자금 투자
        
        # 최종 투자자 유형 결정
        if score <= -2:
            return InvestorType.STABILITY
        elif score <= 0:
            return InvestorType.CONSERVATIVE
        elif score <= 3:
            return InvestorType.BALANCED
        elif score <= 5:
            return InvestorType.GROWTH
        else:
            return InvestorType.AGGRESSIVE
    
    def check_suitability(self, investor_type: InvestorType, portfolio_risk: RiskLevel) -> Tuple[bool, List[str]]:
        """적합성 검증 (6대 판매원칙 - 적합성원칙)"""
        warnings = []
        is_suitable = True
        
        # 투자자 유형별 허용 위험 수준
        allowed_risks = {
            InvestorType.STABILITY: [RiskLevel.VERY_LOW, RiskLevel.LOW],
            InvestorType.CONSERVATIVE: [RiskLevel.VERY_LOW, RiskLevel.LOW, RiskLevel.MEDIUM],
            InvestorType.BALANCED: [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.MEDIUM_HIGH],
            InvestorType.GROWTH: [RiskLevel.MEDIUM, RiskLevel.MEDIUM_HIGH, RiskLevel.HIGH],
            InvestorType.AGGRESSIVE: [RiskLevel.MEDIUM_HIGH, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        }
        
        if portfolio_risk not in allowed_risks[investor_type]:
            is_suitable = False
            warnings.append(f"⚠️ 귀하의 투자성향({investor_type.value})에 비해 포트폴리오 위험도({portfolio_risk.value})가 적합하지 않습니다.")
            warnings.append("투자 결정 전 충분한 검토가 필요합니다.")
        
        return is_suitable, warnings
    
    def check_appropriateness(self, profile: InvestorProfile, portfolio_complexity: str) -> Tuple[bool, List[str]]:
        """적정성 검증 (6대 판매원칙 - 적정성원칙)"""
        warnings = []
        is_appropriate = True
        
        # 복잡한 상품에 대한 경험 부족 체크
        if portfolio_complexity == "복잡" and profile.investment_experience in ["없음", "1년미만"]:
            is_appropriate = False
            warnings.append("⚠️ 이 포트폴리오는 복잡한 금융상품을 포함하고 있어 투자 경험이 부족한 투자자에게는 적정하지 않을 수 있습니다.")
            warnings.append("전문가 상담을 권장합니다.")
        
        # 투자금액 대비 총자산 비율 체크
        if profile.investment_ratio > 0.3:
            warnings.append("⚠️ 총 자산 대비 투자 비율이 30%를 초과합니다. 분산 투자를 고려하세요.")
        
        return is_appropriate, warnings
    
    def generate_investment_explanation(self, portfolio_data: Dict) -> Dict[str, str]:
        """투자 설명서 생성 (6대 판매원칙 - 설명의무)"""
        explanation = {
            "개요": self._generate_overview(portfolio_data),
            "주요위험": self._generate_risk_description(portfolio_data),
            "수익구조": self._generate_return_structure(portfolio_data),
            "비용": self._generate_cost_structure(portfolio_data),
            "투자자유의사항": self._generate_investor_notes()
        }
        return explanation
    
    def _generate_overview(self, portfolio_data: Dict) -> str:
        """포트폴리오 개요 생성"""
        num_stocks = len(portfolio_data.get("weights", {}))
        expected_return = portfolio_data.get("performance", {}).get("expected_annual_return", 0)
        volatility = portfolio_data.get("performance", {}).get("annual_volatility", 0)
        
        return f"""
본 포트폴리오는 총 {num_stocks}개의 주식으로 구성되어 있으며,
예상 연간 수익률은 {expected_return:.2%}, 
연간 변동성은 {volatility:.2%}입니다.

과거 수익률이 미래 수익을 보장하지 않으며,
시장 상황에 따라 손실이 발생할 수 있습니다.
"""
    
    def _generate_risk_description(self, portfolio_data: Dict) -> str:
        """주요 위험 설명"""
        return """
1. 시장위험: 주식시장 전체의 변동에 따른 손실 위험
2. 개별종목위험: 특정 기업의 실적 악화 등으로 인한 손실 위험
3. 유동성위험: 거래량 부족으로 원하는 시점에 매매가 어려울 위험
4. 환율위험: 해외주식 포함 시 환율 변동에 따른 손실 위험
5. 신용위험: 기업 부도 등으로 인한 원금 손실 위험
"""
    
    def _generate_return_structure(self, portfolio_data: Dict) -> str:
        """수익 구조 설명"""
        return """
본 포트폴리오의 수익은 다음과 같이 발생합니다:
1. 배당수익: 보유 주식의 배당금
2. 자본차익: 주가 상승에 따른 매매차익
3. 환차익: 해외주식의 경우 환율 변동에 따른 추가 손익

단, 주가 하락 시 자본손실이 발생할 수 있으며,
배당금은 기업 실적에 따라 변동하거나 지급되지 않을 수 있습니다.
"""
    
    def _generate_cost_structure(self, portfolio_data: Dict) -> str:
        """비용 구조 설명"""
        return """
투자 시 발생하는 주요 비용:
1. 매매수수료: 주식 매매 시 증권사에 지급하는 수수료 (약 0.015~0.3%)
2. 증권거래세: 주식 매도 시 부과되는 세금 (코스피 0.08%, 코스닥 0.15%)
3. 양도소득세: 주식 양도차익에 대한 세금 (대주주 등 조건에 따라 상이)
4. 기타 제비용: 예탁결제원 수수료 등

※ 실제 비용은 거래 증권사 및 거래 조건에 따라 달라질 수 있습니다.
"""
    
    def _generate_investor_notes(self) -> str:
        """투자자 유의사항"""
        return """
[투자자 권리 및 유의사항]

1. 청약철회권: 일정 조건 하에서 계약 체결 후 철회 가능
2. 위법계약해지권: 금융회사의 법 위반 시 계약 해지 가능
3. 자료열람요구권: 분쟁 시 관련 자료 열람 요구 가능

[필수 확인사항]
- 투자설명서를 반드시 읽고 이해한 후 투자하시기 바랍니다.
- 투자원금의 손실 가능성을 충분히 인지하시기 바랍니다.
- 예금자보호 대상이 아님을 확인하시기 바랍니다.
- 과거 수익률이 미래 수익을 보장하지 않습니다.

[분쟁 발생 시 연락처]
- 금융감독원: 1332
- 한국금융투자협회: 02-2003-9000
"""
    
    def calculate_portfolio_risk_level(self, volatility: float, max_drawdown: float = None) -> RiskLevel:
        """포트폴리오 위험 등급 산정"""
        # 변동성 기준 위험 등급
        if volatility > 0.40:  # 40% 이상
            return RiskLevel.VERY_HIGH
        elif volatility > 0.25:  # 25% 이상
            return RiskLevel.HIGH
        elif volatility > 0.15:  # 15% 이상
            return RiskLevel.MEDIUM_HIGH
        elif volatility > 0.10:  # 10% 이상
            return RiskLevel.MEDIUM
        elif volatility > 0.05:  # 5% 이상
            return RiskLevel.LOW
        else:
            return RiskLevel.VERY_LOW
    
    def generate_warning_messages(self, risk_level: RiskLevel) -> List[str]:
        """위험 등급별 경고 메시지 생성"""
        return self.risk_warnings.get(risk_level, [])
    
    def check_concentration_risk(self, weights: Dict[str, float]) -> List[str]:
        """집중도 위험 체크"""
        warnings = []
        
        # 단일 종목 집중도 체크
        for ticker, weight in weights.items():
            if weight > 0.2:  # 20% 초과
                warnings.append(f"⚠️ {ticker} 종목의 비중이 {weight:.1%}로 과도하게 높습니다. 분산투자를 권장합니다.")
        
        # 상위 3개 종목 집중도
        sorted_weights = sorted(weights.values(), reverse=True)
        if len(sorted_weights) >= 3:
            top3_concentration = sum(sorted_weights[:3])
            if top3_concentration > 0.6:  # 60% 초과
                warnings.append(f"⚠️ 상위 3개 종목 비중이 {top3_concentration:.1%}로 집중되어 있습니다.")
        
        return warnings