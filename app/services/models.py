

"""Pydantic models for portfolio service."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field, constr, RootModel


class PortfolioRequest(BaseModel):
    """Request payload for creating a portfolio."""
    tickers: List[constr(strip_whitespace=True, min_length=1)] = Field(
        ...,
        example=["005930.KS", "035420.KS"],
        description="종목 티커 리스트 (KRX 코드 또는 yfinance 코드)",
    )
    age: int = Field(..., ge=0, le=120, example=35, description="고객 나이")
    experience: str = Field(..., example="초보", description="투자 경험")
    risk_profile: str = Field(..., example="중립형", description="리스크 성향")
    investment_goal: str = Field(..., example="은퇴준비", description="투자 목표")
    investment_period: str = Field(..., example="10년", description="투자 기간")



class PortfolioWeights(RootModel[Dict[str, float]]):
    """자산별 비중 딕셔너리 (ticker → weight)."""
    pass


class PortfolioPerformance(BaseModel):
    """최적화 결과 성과 지표"""
    expected_annual_return: float = Field(..., example=0.08)
    annual_volatility: float = Field(..., example=0.15)
    sharpe_ratio: float = Field(..., example=0.53)


class PortfolioResponse(BaseModel):
    """Response payload with explanation."""
    weights: PortfolioWeights
    performance: PortfolioPerformance
    explanation: str