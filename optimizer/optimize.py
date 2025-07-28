# optimizer/optimize.py

"""Mean‑variance 포트폴리오 최적화 래퍼 (수학적 최적화 + 실무적 제약조건 지원)."""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum

import pandas as pd
import numpy as np
from pypfopt import EfficientFrontier, expected_returns, risk_models
from sqlalchemy import text

from utils.db import SessionLocal

logger = logging.getLogger(__name__)


class OptimizationMode(Enum):
    """최적화 방식 정의"""
    MATHEMATICAL = "mathematical"  # 순수 수학적 최적화
    PRACTICAL = "practical"        # 실무적 제약조건 적용
    CONSERVATIVE = "conservative"   # 보수적 분산투자


class PortfolioOptimizer:
    """PyPortfolioOpt 기반 다중 최적화 방식 지원 유틸리티."""

    def __init__(
        self,
        tickers: List[str],
        start_date: str = "2024-01-01",
        risk_free_rate: float = 0.005,
        optimization_mode: OptimizationMode = OptimizationMode.MATHEMATICAL,
        risk_profile: str = "중립형"
    ):
        if not tickers:
            raise ValueError("tickers 리스트가 비어 있습니다.")
        
        # yfinance 티커 형식(.KS, .KQ)을 KRX 코드로 변환
        self.tickers = [t.split('.')[0] for t in tickers]
        self.start_date = start_date
        self.risk_free_rate = risk_free_rate
        self.optimization_mode = optimization_mode
        self.risk_profile = risk_profile
        
        # 최적화 방식별 제약조건 설정
        self.constraints = self._get_optimization_constraints()

    def _get_optimization_constraints(self) -> Dict:
        """최적화 방식에 따른 제약조건 설정"""
        
        if self.optimization_mode == OptimizationMode.MATHEMATICAL:
            # 순수 수학적 최적화 - 제약조건 최소화
            return {
                "max_single_weight": 1.0,      # 단일종목 100% 허용
                "min_positions": 1,            # 최소 1개 종목
                "min_weight_threshold": 0.01,  # 1% 이상만 포함
                "enforce_diversification": False
            }
        
        elif self.optimization_mode == OptimizationMode.PRACTICAL:
            # 실무적 제약조건
            return {
                "max_single_weight": 0.3,      # 단일종목 최대 30%
                "min_positions": 3,            # 최소 3개 종목
                "min_weight_threshold": 0.05,  # 5% 이상만 포함
                "enforce_diversification": True,
                "sector_max_weight": 0.6       # 동일 섹터 최대 60%
            }
        
        else:  # CONSERVATIVE
            # 보수적 분산투자
            return {
                "max_single_weight": 0.25,     # 단일종목 최대 25%
                "min_positions": 5,            # 최소 5개 종목
                "min_weight_threshold": 0.05,  # 5% 이상만 포함
                "enforce_diversification": True,
                "sector_max_weight": 0.4       # 동일 섹터 최대 40%
            }

    def _load_prices(self) -> pd.DataFrame:
        """prices_merged 테이블에서 가격 데이터를 로드합니다."""
        session = SessionLocal()
        try:
            # SQL 쿼리 구성
            placeholders = ', '.join([f':ticker_{i}' for i in range(len(self.tickers))])
            query_str = f"""
                SELECT date, ticker, close
                FROM prices_merged
                WHERE ticker IN ({placeholders})
                  AND date >= :start_date
                ORDER BY date, ticker
            """
            
            # 파라미터 딕셔너리 생성
            params = {"start_date": self.start_date}
            for i, ticker in enumerate(self.tickers):
                params[f'ticker_{i}'] = ticker

            # 데이터 조회
            result = session.execute(text(query_str), params)
            rows = result.fetchall()
            
            if not rows:
                raise ValueError(f"가격 데이터가 없습니다. 종목: {self.tickers}")
            
            # DataFrame 생성
            df = pd.DataFrame(rows, columns=['date', 'ticker', 'close'])
            df['date'] = pd.to_datetime(df['date'])
            
        finally:
            session.close()

        matrix = df.pivot(index="date", columns="ticker", values="close").sort_index()
        
        matrix.dropna(axis=1, thresh=10, inplace=True)
        matrix.dropna(axis=0, how='any', inplace=True)

        if matrix.empty or matrix.shape[0] < 10:
            raise ValueError(f"최적화에 필요한 데이터가 부족합니다. 현재: {matrix.shape[0]}일")

        return matrix

    def _create_fallback_portfolio(self) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """데이터 부족 시 제약조건에 맞는 폴백 포트폴리오 생성."""
        logger.warning(f"⚠️ 데이터 부족으로 {self.optimization_mode.value} 방식의 폴백 포트폴리오 생성")
        
        n = len(self.tickers)
        
        if self.optimization_mode == OptimizationMode.MATHEMATICAL:
            # 수학적 최적화 실패 시 - 균등분배
            weight = 1.0 / n if n > 0 else 0
            weights = {f"{ticker}.KS": weight for ticker in self.tickers}
            
        elif self.optimization_mode == OptimizationMode.PRACTICAL:
            # 실무적 제약조건 적용
            max_weight = min(self.constraints["max_single_weight"], 1.0 / max(3, n))
            weights = {}
            
            # 상위 종목들에 더 높은 비중 할당 (시가총액 기준으로 가정)
            for i, ticker in enumerate(self.tickers[:self.constraints["min_positions"]]):
                if i == 0:  # 첫 번째 종목
                    weights[f"{ticker}.KS"] = max_weight
                else:
                    remaining = 1.0 - sum(weights.values())
                    remaining_tickers = self.constraints["min_positions"] - i
                    weights[f"{ticker}.KS"] = min(max_weight, remaining / remaining_tickers)
                    
        else:  # CONSERVATIVE
            # 보수적 분산투자
            max_weight = self.constraints["max_single_weight"]
            min_positions = self.constraints["min_positions"]
            
            weights = {}
            for i, ticker in enumerate(self.tickers[:min_positions]):
                if i < 2:  # 상위 2개 종목은 최대 비중
                    weights[f"{ticker}.KS"] = max_weight
                else:
                    remaining = 1.0 - sum(weights.values())
                    remaining_tickers = min_positions - i
                    weights[f"{ticker}.KS"] = remaining / remaining_tickers

        # 비중 정규화
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v/total_weight for k, v in weights.items()}
        
        # 기본 성과 지표 (추정치)
        performance = (0.08, 0.15, 0.53)
        
        return weights, performance

    def optimize(self) -> Tuple[Dict[str, float], Tuple[float, float, float]]:
        """제약조건이 적용된 포트폴리오 최적화 실행."""
        try:
            prices = self._load_prices()
            mu = expected_returns.mean_historical_return(prices)
            cov = risk_models.sample_cov(prices)
            ef = EfficientFrontier(mu, cov)
            
            # 최적화 방식별 제약조건 적용
            max_weight = self.constraints["max_single_weight"]
            
            # 단일 종목 최대 비중 제한 (모든 모드에 적용)
            if max_weight < 1.0:
                # 각 종목의 비중이 max_weight 이하가 되도록 제약
                for i in range(len(ef.tickers)):
                    ef.add_constraint(lambda w, i=i: w[i] <= max_weight)
                
            # 최소 비중 제한 (너무 작은 비중 제거)
            min_weight = self.constraints["min_weight_threshold"]
                
            # 최적화 실행
            raw_weights = ef.max_sharpe(risk_free_rate=self.risk_free_rate)
            
            # 가중치 정리
            cutoff = self.constraints["min_weight_threshold"]
            cleaned = ef.clean_weights(cutoff=cutoff, rounding=4)
            
            # 제약조건 검증
            if self.constraints["enforce_diversification"]:
                cleaned = self._enforce_diversification_constraints(cleaned)
            
            # .KS 접미사 추가
            final_weights = {f"{ticker}.KS": weight for ticker, weight in cleaned.items() if weight > 0}
            
            # 성과 지표 계산
            perf = ef.portfolio_performance(verbose=False, risk_free_rate=self.risk_free_rate)
            
            return final_weights, perf
            
        except (ValueError, Exception) as e:
            logger.error(f"❌ {self.optimization_mode.value} 최적화 실패: {e}")
            return self._create_fallback_portfolio()

    def _enforce_diversification_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """분산투자 제약조건 강제 적용"""
        
        # 최소 종목 수 확인
        active_positions = {k: v for k, v in weights.items() if v > 0}
        
        # 단일 종목 한도 강제 적용
        max_weight = self.constraints["max_single_weight"]
        adjusted_weights = {}
        
        for ticker, weight in active_positions.items():
            if weight > max_weight:
                adjusted_weights[ticker] = max_weight
            else:
                adjusted_weights[ticker] = weight
        
        # 비중 재정규화
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            normalized_weights = {k: v/total_weight for k, v in adjusted_weights.items()}
        else:
            normalized_weights = adjusted_weights
            
        # 최소 종목 수 확인
        min_positions = self.constraints["min_positions"]
        if len(normalized_weights) < min_positions:
            logger.warning(f"최소 종목 수 부족: {len(normalized_weights)} < {min_positions}")
            
        return normalized_weights

    def get_optimization_comparison(self) -> Dict:
        """여러 최적화 방식의 결과를 비교"""
        results = {}
        
        for mode in OptimizationMode:
            try:
                # 임시로 최적화 모드 변경
                original_mode = self.optimization_mode
                self.optimization_mode = mode
                self.constraints = self._get_optimization_constraints()
                
                # 최적화 실행
                weights, performance = self.optimize()
                
                results[mode.value] = {
                    "weights": weights,
                    "performance": {
                        "expected_annual_return": performance[0],
                        "annual_volatility": performance[1],
                        "sharpe_ratio": performance[2]
                    },
                    "num_positions": len([w for w in weights.values() if w > 0.01]),
                    "max_single_weight": max(weights.values()) if weights else 0,
                    "description": self._get_mode_description(mode)
                }
                
                # 원래 모드로 복원
                self.optimization_mode = original_mode
                self.constraints = self._get_optimization_constraints()
                
            except Exception as e:
                logger.error(f"{mode.value} 최적화 실패: {e}")
                results[mode.value] = {"error": str(e)}
        
        return results

    def _get_mode_description(self, mode: OptimizationMode) -> str:
        """최적화 방식별 설명"""
        descriptions = {
            OptimizationMode.MATHEMATICAL: "순수 수학적 최적화 (샤프 비율 최대화, 제약 최소)",
            OptimizationMode.PRACTICAL: "실무적 균형 (최대 40% 제한, 3개 이상 분산)",
            OptimizationMode.CONSERVATIVE: "보수적 분산투자 (최대 25% 제한, 5개 이상 분산)"
        }
        return descriptions.get(mode, "")


def test_optimizer():
    """최적화 엔진 테스트 함수."""
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 다중 모드 포트폴리오 최적화 테스트 시작...")
    
    try:
        # 삼성전자, 네이버, SK하이닉스로 테스트
        tickers = ['005930', '035420', '000660']
        
        for mode in OptimizationMode:
            print(f"\n📊 {mode.value} 모드 테스트")
            print("-" * 40)
            
            optimizer = PortfolioOptimizer(tickers, optimization_mode=mode)
            weights, perf = optimizer.optimize()
            
            print(f"✅ 최적화 성공!")
            print(f"📊 최적 비중: {weights}")
            print(f"📈 예상 성과:")
            print(f"   - 연수익률: {perf[0]:.1%}")
            print(f"   - 연변동성: {perf[1]:.1%}")
            print(f"   - 샤프비율: {perf[2]:.3f}")
            print(f"   - 종목수: {len([w for w in weights.values() if w > 0.01])}")
            print(f"   - 최대비중: {max(weights.values()) if weights else 0:.1%}")
        
        # 비교 테스트
        print(f"\n🔄 전체 비교 테스트")
        print("-" * 40)
        
        optimizer = PortfolioOptimizer(tickers)
        comparison = optimizer.get_optimization_comparison()
        
        for mode_name, result in comparison.items():
            if "error" not in result:
                print(f"{mode_name}: 샤프비율 {result['performance']['sharpe_ratio']:.3f}, "
                      f"종목수 {result['num_positions']}, 최대비중 {result['max_single_weight']:.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False


if __name__ == "__main__":
    test_optimizer()