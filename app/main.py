"""FastAPI 엔트리포인트."""
from __future__ import annotations

from fastapi import FastAPI

from app.services.models import PortfolioRequest, PortfolioResponse
from app.services.portfolio import create_portfolio_with_explanation

app = FastAPI(title="Portfolio API")


@app.post("/portfolio/recommend", response_model=PortfolioResponse)
async def recommend(payload: PortfolioRequest):
    """
    포트폴리오 추천 + HyperCLOVA 설명 API.

    Request  → PortfolioRequest 스키마
    Response → PortfolioResponse 스키마
    """
    result = await create_portfolio_with_explanation(
        tickers=payload.tickers,
        age=payload.age,
        experience=payload.experience,
        risk_profile=payload.risk_profile,
        investment_goal=payload.investment_goal,
        investment_period=payload.investment_period,
    )
    return result