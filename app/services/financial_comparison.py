"""재무제표 비교 및 시각화 서비스."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
import numpy as np

from app.services.portfolio import _call_hcx_async
from app.services.stock_database import StockDatabase
from utils.db import SessionLocal
from sqlalchemy import text

# 한글 폰트 설정
plt.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'AppleGothic']
plt.rcParams['axes.unicode_minus'] = False

logger = logging.getLogger(__name__)

class FinancialComparisonService:
    """재무제표 비교 및 시각화 서비스."""
    
    def __init__(self):
        self.stock_db = StockDatabase()
        self.session = SessionLocal()
        # 색상 팔레트
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    async def compare_companies_financial(
        self,
        company_codes: List[str],
        years: int = 3,
        user_question: str = None
    ) -> Dict:
        """기업간 재무제표 비교 분석."""
        
        try:
            # 1. 재무 데이터 수집
            financial_data = await self._collect_multi_company_financials(company_codes, years)
            
            # 2. 차트 생성
            charts = await self._generate_comparison_charts(financial_data, company_codes)
            
            # 3. AI 분석 생성
            ai_analysis = await self._generate_ai_comparison_analysis(
                financial_data, company_codes, user_question
            )
            
            # 4. 투자 인사이트 생성
            investment_insights = await self._generate_investment_insights(
                financial_data, company_codes
            )
            
            return {
                "companies": company_codes,
                "analysis_period": f"최근 {years}년",
                "financial_data": financial_data,
                "charts": charts,
                "ai_analysis": ai_analysis,
                "investment_insights": investment_insights,
                "summary_table": self._create_summary_table(financial_data, company_codes),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"재무 비교 분석 실패: {e}")
            raise
    
    async def _collect_multi_company_financials(
        self, 
        company_codes: List[str], 
        years: int
    ) -> Dict:
        """여러 기업의 재무 데이터 수집."""
        
        financial_data = {}
        
        for code in company_codes:
            try:
                # 회사명 조회
                company_name = await self._get_company_name(code)
                
                # 재무 데이터 조회
                query = """
                    SELECT year, 매출액, 영업이익, 당기순이익
                    FROM financials
                    WHERE ticker = %s
                    ORDER BY year DESC
                    LIMIT %s
                """
                
                result = self.session.execute(text(query), [code, years])
                raw_data = result.fetchall()
                
                if not raw_data:
                    # yfinance에서 데이터 시도
                    yf_data = await self._get_yfinance_financials(code)
                    raw_data = yf_data
                
                # 데이터 구조화
                structured_data = {
                    "company_name": company_name,
                    "ticker": code,
                    "years": [row[0] for row in raw_data],
                    "revenue": [row[1] / 100000000 if row[1] else 0 for row in raw_data],  # 억원 단위
                    "operating_profit": [row[2] / 100000000 if row[2] else 0 for row in raw_data],
                    "net_profit": [row[3] / 100000000 if row[3] else 0 for row in raw_data],
                }
                
                # 비율 계산
                structured_data["operating_margin"] = [
                    (op / rev * 100) if rev > 0 else 0 
                    for op, rev in zip(structured_data["operating_profit"], structured_data["revenue"])
                ]
                
                structured_data["net_margin"] = [
                    (np / rev * 100) if rev > 0 else 0
                    for np, rev in zip(structured_data["net_profit"], structured_data["revenue"])
                ]
                
                # 성장률 계산
                structured_data["revenue_growth"] = self._calculate_growth_rates(structured_data["revenue"])
                structured_data["profit_growth"] = self._calculate_growth_rates(structured_data["net_profit"])
                
                financial_data[code] = structured_data
                
            except Exception as e:
                logger.error(f"재무 데이터 수집 실패 {code}: {e}")
                financial_data[code] = {
                    "company_name": f"종목 {code}",
                    "error": str(e)
                }
        
        return financial_data
    
    async def _get_company_name(self, ticker: str) -> str:
        """종목 코드로 회사명 조회."""
        try:
            query = "SELECT corp_name FROM company_info WHERE ticker = %s"
            result = self.session.execute(text(query), [ticker])
            row = result.fetchone()
            return row[0] if row else f"종목 {ticker}"
        except:
            return f"종목 {ticker}"
    
    async def _get_yfinance_financials(self, ticker: str) -> List[Tuple]:
        """yfinance에서 재무 데이터 조회."""
        try:
            import yfinance as yf
            
            yf_ticker = f"{ticker}.KS"
            stock = yf.Ticker(yf_ticker)
            
            # 재무제표 조회
            financials = stock.financials
            
            if financials.empty:
                return []
            
            # 최근 3년 데이터 추출
            results = []
            for col in financials.columns[:3]:  # 최근 3년
                year = col.year
                revenue = self._safe_get_yf_value(financials, 'Total Revenue', col)
                operating_income = self._safe_get_yf_value(financials, 'Operating Income', col)
                net_income = self._safe_get_yf_value(financials, 'Net Income', col)
                
                results.append((year, revenue, operating_income, net_income))
            
            return results
            
        except Exception as e:
            logger.error(f"yfinance 재무 데이터 조회 실패 {ticker}: {e}")
            return []
    
    def _safe_get_yf_value(self, df, key, col):
        """yfinance 데이터에서 안전하게 값 추출."""
        try:
            if key in df.index:
                value = df.loc[key, col]
                return float(value) if pd.notna(value) else 0
            return 0
        except:
            return 0
    
    def _calculate_growth_rates(self, values: List[float]) -> List[float]:
        """성장률 계산."""
        if len(values) < 2:
            return [0.0] * len(values)
        
        growth_rates = [0.0]  # 첫 번째 년도는 0%
        
        for i in range(1, len(values)):
            if values[i] > 0:  # 이전 년도 값
                growth = ((values[i-1] - values[i]) / values[i]) * 100
                growth_rates.append(round(growth, 2))
            else:
                growth_rates.append(0.0)
        
        return growth_rates
    
    async def _generate_comparison_charts(
        self, 
        financial_data: Dict, 
        company_codes: List[str]
    ) -> Dict:
        """비교 차트 생성."""
        
        charts = {}
        
        try:
            # 1. 매출액 비교 차트
            charts["revenue_comparison"] = await self._create_revenue_chart(financial_data, company_codes)
            
            # 2. 수익성 비교 차트
            charts["profitability_comparison"] = await self._create_profitability_chart(financial_data, company_codes)
            
            # 3. 성장률 비교 차트
            charts["growth_comparison"] = await self._create_growth_chart(financial_data, company_codes)
            
            # 4. 종합 비교 레이더 차트
            charts["radar_comparison"] = await self._create_radar_chart(financial_data, company_codes)
            
            # 5. 트렌드 분석 차트
            charts["trend_analysis"] = await self._create_trend_chart(financial_data, company_codes)
            
        except Exception as e:
            logger.error(f"차트 생성 실패: {e}")
            charts["error"] = str(e)
        
        return charts
    
    async def _create_revenue_chart(self, financial_data: Dict, company_codes: List[str]) -> str:
        """매출액 비교 차트 생성."""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 매출액 추이 차트
        for i, code in enumerate(company_codes):
            data = financial_data.get(code, {})
            if "years" in data and "revenue" in data:
                ax1.plot(data["years"], data["revenue"], 
                        marker='o', linewidth=2, label=data["company_name"],
                        color=self.colors[i % len(self.colors)])
        
        ax1.set_title("매출액 추이 비교", fontsize=14, fontweight='bold')
        ax1.set_xlabel("연도")
        ax1.set_ylabel("매출액 (억원)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 최신년도 매출액 바차트
        latest_revenues = []
        company_names = []
        
        for code in company_codes:
            data = financial_data.get(code, {})
            if "revenue" in data and data["revenue"]:
                latest_revenues.append(data["revenue"][0])  # 최신년도
                company_names.append(data["company_name"])
            else:
                latest_revenues.append(0)
                company_names.append(data.get("company_name", code))
        
        bars = ax2.bar(range(len(company_names)), latest_revenues, 
                      color=self.colors[:len(company_names)])
        ax2.set_title("최신년도 매출액 비교", fontsize=14, fontweight='bold')
        ax2.set_ylabel("매출액 (억원)")
        ax2.set_xticks(range(len(company_names)))
        ax2.set_xticklabels(company_names, rotation=45)
        
        # 바차트 위에 수치 표시
        for bar, value in zip(bars, latest_revenues):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{value:,.0f}억', ha='center', va='bottom')
        
        plt.tight_layout()
        return self._save_chart_as_base64(fig)
    
    async def _create_profitability_chart(self, financial_data: Dict, company_codes: List[str]) -> str:
        """수익성 비교 차트 생성."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 영업이익률 추이
        for i, code in enumerate(company_codes):
            data = financial_data.get(code, {})
            if "years" in data and "operating_margin" in data:
                ax1.plot(data["years"], data["operating_margin"],
                        marker='s', linewidth=2, label=data["company_name"],
                        color=self.colors[i % len(self.colors)])
        
        ax1.set_title("영업이익률 추이", fontsize=12, fontweight='bold')
        ax1.set_ylabel("영업이익률 (%)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 순이익률 추이
        for i, code in enumerate(company_codes):
            data = financial_data.get(code, {})
            if "years" in data and "net_margin" in data:
                ax2.plot(data["years"], data["net_margin"],
                        marker='^', linewidth=2, label=data["company_name"],
                        color=self.colors[i % len(self.colors)])
        
        ax2.set_title("순이익률 추이", fontsize=12, fontweight='bold')
        ax2.set_ylabel("순이익률 (%)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 최신년도 영업이익 비교
        latest_op_profits = []
        company_names = []
        
        for code in company_codes:
            data = financial_data.get(code, {})
            if "operating_profit" in data and data["operating_profit"]:
                latest_op_profits.append(data["operating_profit"][0])
                company_names.append(data["company_name"])
            else:
                latest_op_profits.append(0)
                company_names.append(data.get("company_name", code))
        
        bars = ax3.bar(range(len(company_names)), latest_op_profits,
                      color=self.colors[:len(company_names)])
        ax3.set_title("영업이익 비교", fontsize=12, fontweight='bold')
        ax3.set_ylabel("영업이익 (억원)")
        ax3.set_xticks(range(len(company_names)))
        ax3.set_xticklabels(company_names, rotation=45)
        
        # 4. 수익성 히트맵
        profitability_matrix = []
        metrics = ["영업이익률", "순이익률"]
        
        for code in company_codes:
            data = financial_data.get(code, {})
            if "operating_margin" in data and "net_margin" in data:
                row = [
                    data["operating_margin"][0] if data["operating_margin"] else 0,
                    data["net_margin"][0] if data["net_margin"] else 0
                ]
                profitability_matrix.append(row)
            else:
                profitability_matrix.append([0, 0])
        
        im = ax4.imshow(profitability_matrix, cmap='RdYlGn', aspect='auto')
        ax4.set_title("수익성 히트맵", fontsize=12, fontweight='bold')
        ax4.set_xticks(range(len(metrics)))
        ax4.set_xticklabels(metrics)
        ax4.set_yticks(range(len(company_names)))
        ax4.set_yticklabels(company_names)
        
        # 히트맵에 수치 표시
        for i in range(len(company_names)):
            for j in range(len(metrics)):
                text = ax4.text(j, i, f'{profitability_matrix[i][j]:.1f}%',
                               ha="center", va="center", color="black", fontweight='bold')
        
        plt.colorbar(im, ax=ax4)
        plt.tight_layout()
        return self._save_chart_as_base64(fig)
    
    async def _create_growth_chart(self, financial_data: Dict, company_codes: List[str]) -> str:
        """성장률 비교 차트 생성."""
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 매출 성장률 비교
        for i, code in enumerate(company_codes):
            data = financial_data.get(code, {})
            if "years" in data and "revenue_growth" in data:
                ax1.bar([f"{data['company_name']}\n{year}" for year in data["years"][1:]], 
                       data["revenue_growth"][1:],  # 첫 번째 제외
                       alpha=0.7, color=self.colors[i % len(self.colors)])
        
        ax1.set_title("매출 성장률 비교", fontsize=14, fontweight='bold')
        ax1.set_ylabel("성장률 (%)")
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
        
        # 순이익 성장률 비교
        for i, code in enumerate(company_codes):
            data = financial_data.get(code, {})
            if "years" in data and "profit_growth" in data:
                ax2.bar([f"{data['company_name']}\n{year}" for year in data["years"][1:]], 
                       data["profit_growth"][1:],  # 첫 번째 제외
                       alpha=0.7, color=self.colors[i % len(self.colors)])
        
        ax2.set_title("순이익 성장률 비교", fontsize=14, fontweight='bold')
        ax2.set_ylabel("성장률 (%)")
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        return self._save_chart_as_base64(fig)
    
    async def _create_radar_chart(self, financial_data: Dict, company_codes: List[str]) -> str:
        """레이더 차트 생성."""
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # 평가 지표들
        metrics = ['매출규모', '영업이익률', '순이익률', '매출성장률', '이익성장률']
        
        # 각 기업별 데이터 정규화
        for i, code in enumerate(company_codes[:4]):  # 최대 4개 기업
            data = financial_data.get(code, {})
            if "error" in data:
                continue
            
            # 지표값 계산 (0-100 스케일로 정규화)
            values = []
            
            # 매출규모 (상대적)
            if "revenue" in data and data["revenue"]:
                max_revenue = max([financial_data[c].get("revenue", [0])[0] 
                                 for c in company_codes if "revenue" in financial_data.get(c, {})])
                revenue_score = (data["revenue"][0] / max_revenue * 100) if max_revenue > 0 else 0
                values.append(revenue_score)
            else:
                values.append(0)
            
            # 영업이익률
            if "operating_margin" in data and data["operating_margin"]:
                values.append(min(data["operating_margin"][0], 100))  # 최대 100%로 제한
            else:
                values.append(0)
            
            # 순이익률
            if "net_margin" in data and data["net_margin"]:
                values.append(min(data["net_margin"][0], 100))
            else:
                values.append(0)
            
            # 매출성장률 (최근 3년 평균)
            if "revenue_growth" in data and data["revenue_growth"]:
                avg_growth = sum(data["revenue_growth"][1:]) / len(data["revenue_growth"][1:])
                values.append(max(0, min(avg_growth + 50, 100)))  # -50% ~ 50% 범위를 0-100으로 변환
            else:
                values.append(50)
            
            # 이익성장률 (최근 3년 평균)
            if "profit_growth" in data and data["profit_growth"]:
                avg_profit_growth = sum(data["profit_growth"][1:]) / len(data["profit_growth"][1:])
                values.append(max(0, min(avg_profit_growth + 50, 100)))
            else:
                values.append(50)
            
            # 레이더 차트 그리기
            angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
            values += values[:1]  # 닫힌 도형을 위해 첫 번째 값 추가
            angles += angles[:1]
            
            ax.plot(angles, values, 'o-', linewidth=2, label=data["company_name"],
                   color=self.colors[i % len(self.colors)])
            ax.fill(angles, values, alpha=0.25, color=self.colors[i % len(self.colors)])
        
        # 차트 설정
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metrics)
        ax.set_ylim(0, 100)
        ax.set_title("기업 종합 경쟁력 비교\n(레이더 차트)", size=16, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.grid(True)
        
        plt.tight_layout()
        return self._save_chart_as_base64(fig)
    
    async def _create_trend_chart(self, financial_data: Dict, company_codes: List[str]) -> str:
        """트렌드 분석 차트 생성."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. 매출 vs 영업이익 상관관계
        for i, code in enumerate(company_codes):
            data = financial_data.get(code, {})
            if "revenue" in data and "operating_profit" in data:
                ax1.scatter(data["revenue"], data["operating_profit"],
                           s=100, alpha=0.7, label=data["company_name"],
                           color=self.colors[i % len(self.colors)])
        
        ax1.set_title("매출 vs 영업이익 상관관계", fontsize=12, fontweight='bold')
        ax1.set_xlabel("매출액 (억원)")
        ax1.set_ylabel("영업이익 (억원)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 기업별 수익구조 분석 (스택 바차트)
        metrics = ['매출액', '영업이익', '순이익']
        bottom_values = np.zeros(len(company_codes))
        
        latest_data = {
            '매출액': [],
            '영업이익': [],
            '순이익': []
        }
        
        for code in company_codes:
            data = financial_data.get(code, {})
            latest_data['매출액'].append(data.get("revenue", [0])[0] if data.get("revenue") else 0)
            latest_data['영업이익'].append(data.get("operating_profit", [0])[0] if data.get("operating_profit") else 0)
            latest_data['순이익'].append(data.get("net_profit", [0])[0] if data.get("net_profit") else 0)
        
        company_names = [financial_data[code]["company_name"] for code in company_codes]
        
        ax2.bar(company_names, latest_data['매출액'], label='매출액', color=self.colors[0], alpha=0.8)
        ax2.bar(company_names, latest_data['영업이익'], label='영업이익', color=self.colors[1], alpha=0.8)
        ax2.bar(company_names, latest_data['순이익'], label='순이익', color=self.colors[2], alpha=0.8)
        
        ax2.set_title("수익구조 비교", fontsize=12, fontweight='bold')
        ax2.set_ylabel("금액 (억원)")
        ax2.legend()
        plt.setp(ax2.get_xticklabels(), rotation=45)
        
        # 3. 시간에 따른 수익성 개선도
        for i, code in enumerate(company_codes):
            data = financial_data.get(code, {})
            if "years" in data and "operating_margin" in data and "net_margin" in data:
                # 수익성 개선 점수 (영업이익률 + 순이익률의 합)
                improvement_scores = [op + net for op, net in 
                                    zip(data["operating_margin"], data["net_margin"])]
                ax3.plot(data["years"], improvement_scores, 
                        marker='D', linewidth=2, label=data["company_name"],
                        color=self.colors[i % len(self.colors)])
        
        ax3.set_title("수익성 개선 추이", fontsize=12, fontweight='bold')
        ax3.set_xlabel("연도")
        ax3.set_ylabel("수익성 점수 (영업이익률 + 순이익률)")
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 효율성 분석 (매출 대비 이익 효율성)
        efficiency_scores = []
        for code in company_codes:
            data = financial_data.get(code, {})
            if "revenue" in data and "net_profit" in data and data["revenue"]:
                # 최근 3년 평균 효율성
                efficiencies = [np / rev if rev > 0 else 0 
                              for np, rev in zip(data["net_profit"], data["revenue"])]
                avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0
                efficiency_scores.append(avg_efficiency * 100)
            else:
                efficiency_scores.append(0)
        
        bars = ax4.barh(range(len(company_names)), efficiency_scores,
                       color=self.colors[:len(company_names)])
        ax4.set_title("평균 수익 효율성", fontsize=12, fontweight='bold')
        ax4.set_xlabel("순이익률 (%)")
        ax4.set_yticks(range(len(company_names)))
        ax4.set_yticklabels(company_names)
        
        # 효율성 수치 표시
        for bar, score in zip(bars, efficiency_scores):
            ax4.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    f'{score:.1f}%', va='center')
        
        plt.tight_layout()
        return self._save_chart_as_base64(fig)
    
    def _save_chart_as_base64(self, fig) -> str:
        """차트를 base64 문자열로 저장."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        return f"data:image/png;base64,{image_base64}"
    
    async def _generate_ai_comparison_analysis(
        self,
        financial_data: Dict,
        company_codes: List[str],
        user_question: str
    ) -> str:
        """AI 기반 재무제표 비교 분석."""
        
        # 분석용 컨텍스트 구성
        context = f"""
**재무제표 비교 분석 요청**

사용자 질문: {user_question or "재무제표를 비교 분석해주세요"}

**비교 대상 기업들:**
{json.dumps(financial_data, ensure_ascii=False, indent=2)}

위 재무 데이터를 바탕으로 다음 관점에서 상세히 분석해주세요:

1. **재무 건전성 비교**
   - 각 기업의 매출 규모와 성장 추이
   - 수익성 지표 (영업이익률, 순이익률) 비교
   - 재무 안정성 평가

2. **성장성 분석**
   - 매출 및 이익 성장률 비교
   - 성장 지속 가능성 평가
   - 미래 성장 전망

3. **수익성 및 효율성**
   - 각 기업의 수익 창출 능력
   - 비용 관리 효율성
   - 투자 대비 수익률

4. **투자 관점에서의 비교**
   - 각 기업의 투자 매력도
   - 리스크 대비 수익 평가
   - 포트폴리오 편입 시 고려사항

5. **종합 평가 및 순위**
   - 종합적인 기업 경쟁력 순위
   - 각 기업의 강점과 약점
   - 투자 추천 의견

구체적인 수치와 근거를 제시하며, 객관적이고 전문적인 분석을 해주세요.
"""
        
        system_prompt = """
당신은 재무 분석 전문가이자 투자 애널리스트입니다.
20년 이상의 경력을 가지고 있으며, CPA와 CFA 자격을 보유하고 있습니다.

재무제표 분석 시 다음 원칙을 따라주세요:
1. 정량적 데이터에 기반한 객관적 분석
2. 업종 특성과 시장 환경 고려
3. 과거 실적과 미래 전망의 균형적 평가
4. 투자 리스크와 기회 요인 명시
5. 실무진과 투자자가 이해하기 쉬운 설명

절대 투자 수익을 보장하지 말고, 모든 분석은 참고용임을 명시하세요.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            ai_analysis = await _call_hcx_async(messages)
            return ai_analysis
        except Exception as e:
            logger.error(f"AI 분석 생성 실패: {e}")
            return f"재무제표 비교 분석을 시도했으나 AI 분석 생성에 실패했습니다. 오류: {str(e)}"
    
    async def _generate_investment_insights(
        self,
        financial_data: Dict,
        company_codes: List[str]
    ) -> Dict:
        """투자 인사이트 생성."""
        
        insights = {
            "best_performer": None,
            "growth_leader": None,
            "value_pick": None,
            "risk_assessment": {},
            "investment_recommendations": []
        }
        
        try:
            # 최고 수익성 기업
            best_margin = 0
            for code in company_codes:
                data = financial_data.get(code, {})
                if "net_margin" in data and data["net_margin"]:
                    if data["net_margin"][0] > best_margin:
                        best_margin = data["net_margin"][0]
                        insights["best_performer"] = {
                            "company": data["company_name"],
                            "ticker": code,
                            "net_margin": best_margin
                        }
            
            # 성장률 리더
            best_growth = -999
            for code in company_codes:
                data = financial_data.get(code, {})
                if "revenue_growth" in data and data["revenue_growth"]:
                    avg_growth = sum(data["revenue_growth"][1:]) / len(data["revenue_growth"][1:])
                    if avg_growth > best_growth:
                        best_growth = avg_growth
                        insights["growth_leader"] = {
                            "company": data["company_name"],
                            "ticker": code,
                            "avg_growth": best_growth
                        }
            
            # 리스크 평가
            for code in company_codes:
                data = financial_data.get(code, {})
                if "revenue" in data and data["revenue"]:
                    # 매출 변동성으로 리스크 평가
                    revenue_volatility = self._calculate_volatility(data["revenue"])
                    risk_level = "높음" if revenue_volatility > 20 else "보통" if revenue_volatility > 10 else "낮음"
                    
                    insights["risk_assessment"][code] = {
                        "company": data["company_name"],
                        "risk_level": risk_level,
                        "volatility": revenue_volatility
                    }
            
            # 투자 추천
            for code in company_codes:
                data = financial_data.get(code, {})
                if "company_name" in data:
                    recommendation = "관심 종목"  # 기본값
                    
                    # 수익성과 성장성 기반 추천 로직
                    if ("net_margin" in data and data["net_margin"] and data["net_margin"][0] > 10 and
                        "revenue_growth" in data and data["revenue_growth"]):
                        """재무제표 비교 및 시각화 서비스."""
from __future__ import annotations

import asyncio
import base64
import io
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
import numpy as np

from app.services.portfolio import _call_hcx_async
from app.services.stock_database import StockDatabase
from utils.db import SessionLocal
from sqlalchemy import text

# 한글 폰트 설정
plt.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'AppleGothic']
plt.rcParams['axes.unicode_minus'] = False

logger = logging.getLogger(__name__)

class FinancialComparisonService:
    """재무제표 비교 및 시각화 서비스."""
    
    def __init__(self):
        self.stock_db = StockDatabase()
        self.session = SessionLocal()
        # 색상 팔레트
        self.colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    async def compare_companies_financial(
        self,
        company_codes: List[str],
        years: int = 3,
        user_question: str = None
    ) -> Dict:
        """기업간 재무제표 비교 분석."""
        
        try:
            # 1. 재무 데이터 수집
            financial_data = await self._collect_multi_company_financials(company_codes, years)
            
            # 2. 차트 생성
            charts = await self._generate_comparison_charts(financial_data, company_codes)
            
            # 3. AI 분석 생성
            ai_analysis = await self._generate_ai_comparison_analysis(
                financial_data, company_codes, user_question
            )
            
            # 4. 투자 인사이트 생성
            investment_insights = await self._generate_investment_insights(
                financial_data, company_codes
            )
            
            return {
                "companies": company_codes,
                "analysis_period": f"최근 {years}년",
                "financial_data": financial_data,
                "charts": charts,
                "ai_analysis": ai_analysis,
                "investment_insights": investment_insights,
                "summary_table": self._create_summary_table(financial_data, company_codes),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"재무 비교 분석 실패: {e}")
            raise
    
    async def _collect_multi_company_financials(
        self, 
        company_codes: List[str], 
        years: int
    ) -> Dict:
        """여러 기업의 재무 데이터 수집."""
        
        financial_data = {}
        
        for code in company_codes:
            try:
                # 회사명 조회
                company_name = await self._get_company_name(code)
                
                # 재무 데이터 조회
                query = """
                    SELECT year, 매출액, 영업이익, 당기순이익
                    FROM financials
                    WHERE ticker = %s
                    ORDER BY year DESC
                    LIMIT %s
                """
                
                result = self.session.execute(text(query), [code, years])
                raw_data = result.fetchall()
                
                if not raw_data:
                    # yfinance에서 데이터 시도
                    yf_data = await self._get_yfinance_financials(code)
                    raw_data = yf_data
                
                # 데이터 구조화
                structured_data = {
                    "company_name": company_name,
                    "ticker": code,
                    "years": [row[0] for row in raw_data],
                    "revenue": [row[1] / 100000000 if row[1] else 0 for row in raw_data],  # 억원 단위
                    "operating_profit": [row[2] / 100000000 if row[2] else 0 for row in raw_data],
                    "net_profit": [row[3] / 100000000 if row[3] else 0 for row in raw_data],
                }
                
                # 비율 계산
                structured_data["operating_margin"] = [
                    (op / rev * 100) if rev > 0 else 0 
                    for op, rev in zip(structured_data["operating_profit"], structured_data["revenue"])
                ]