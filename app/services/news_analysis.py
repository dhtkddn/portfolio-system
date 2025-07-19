"""뉴스 감성 분석 및 호재/악재 분류 서비스 (순환 import 해결)."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import aiohttp
import feedparser
from bs4 import BeautifulSoup

from app.services.hyperclova_client import _call_hcx_async
from app.services.stock_database import StockDatabase

logger = logging.getLogger(__name__)

@dataclass
class NewsItem:
    """뉴스 아이템 클래스."""
    title: str
    content: str
    url: str
    published_date: datetime
    source: str
    ticker: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    impact_level: Optional[str] = None
    key_factors: Optional[List[str]] = None

class NewsAnalysisService:
    """뉴스 감성 분석 및 투자 영향 평가 서비스."""
    
    def __init__(self):
        self.stock_db = StockDatabase()
        
        # 뉴스 소스 URL들
        self.news_sources = {
            "naver_finance": "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258",
            "hankyung": "https://www.hankyung.com/feed/economy",
            "mk": "https://www.mk.co.kr/rss/30000001/",
            "edaily": "https://www.edaily.co.kr/rss/rss_economy.xml"
        }
        
        # 감성 분석용 키워드
        self.positive_keywords = [
            "상승", "증가", "호재", "긍정", "성장", "확대", "개선", "투자", "매수",
            "신고점", "돌파", "급등", "강세", "상한가", "기대", "전망", "호황"
        ]
        
        self.negative_keywords = [
            "하락", "감소", "악재", "부정", "우려", "위험", "손실", "매도",
            "신저점", "급락", "약세", "하한가", "위기", "충격", "불안", "침체"
        ]
    
    async def analyze_stock_news(
        self,
        ticker: str,
        days: int = 7,
        max_articles: int = 50
    ) -> Dict:
        """특정 종목 관련 뉴스 분석."""
        
        try:
            # 1. 뉴스 수집
            news_items = await self._collect_stock_news(ticker, days, max_articles)
            
            # 2. 감성 분석
            analyzed_news = await self._analyze_news_sentiment(news_items)
            
            # 3. 호재/악재 분류
            classified_news = await self._classify_market_impact(analyzed_news, ticker)
            
            # 4. 투자 영향 평가
            investment_impact = await self._evaluate_investment_impact(classified_news, ticker)
            
            # 5. AI 종합 분석
            ai_summary = await self._generate_ai_news_summary(classified_news, ticker)
            
            return {
                "ticker": ticker,
                "analysis_period": f"최근 {days}일",
                "total_articles": len(classified_news),
                "news_items": [self._news_item_to_dict(item) for item in classified_news],
                "investment_impact": investment_impact,
                "sentiment_overview": self._calculate_sentiment_overview(classified_news),
                "ai_summary": ai_summary,
                "market_signals": self._extract_market_signals(classified_news),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"뉴스 분석 실패 {ticker}: {e}")
            raise
    
    async def analyze_market_news(
        self,
        sector: Optional[str] = None,
        days: int = 3,
        max_articles: int = 100
    ) -> Dict:
        """전체 시장 또는 섹터별 뉴스 분석."""
        
        try:
            # 1. 시장 뉴스 수집
            news_items = await self._collect_market_news(sector, days, max_articles)
            
            # 2. 뉴스 분석
            analyzed_news = await self._analyze_news_sentiment(news_items)
            
            # 3. 섹터별 영향 평가
            sector_impact = await self._analyze_sector_impact(analyzed_news, sector)
            
            # 4. 시장 트렌드 분석
            market_trends = await self._analyze_market_trends(analyzed_news)
            
            # 5. AI 시장 분석
            ai_market_analysis = await self._generate_ai_market_analysis(analyzed_news, sector)
            
            return {
                "analysis_target": sector or "전체 시장",
                "analysis_period": f"최근 {days}일",
                "total_articles": len(analyzed_news),
                "sector_impact": sector_impact,
                "market_trends": market_trends,
                "ai_analysis": ai_market_analysis,
                "key_themes": self._extract_key_themes(analyzed_news),
                "risk_factors": self._identify_risk_factors(analyzed_news),
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"시장 뉴스 분석 실패: {e}")
            raise
    
    def _news_item_to_dict(self, news_item: NewsItem) -> Dict:
        """NewsItem을 딕셔너리로 변환."""
        return {
            "title": news_item.title,
            "content": news_item.content,
            "url": news_item.url,
            "published_date": news_item.published_date.isoformat(),
            "source": news_item.source,
            "ticker": news_item.ticker,
            "sentiment_score": news_item.sentiment_score,
            "sentiment_label": news_item.sentiment_label,
            "impact_level": news_item.impact_level,
            "key_factors": news_item.key_factors
        }
    
    async def _collect_stock_news(
        self,
        ticker: str,
        days: int,
        max_articles: int
    ) -> List[NewsItem]:
        """특정 종목 관련 뉴스 수집."""
        
        # 종목명 조회
        company_name = await self._get_company_name(ticker)
        search_keywords = [company_name, ticker]
        
        news_items = []
        
        # 모의 뉴스 생성 (실제 환경에서는 뉴스 API 사용)
        mock_news = await self._generate_mock_news(ticker, company_name, days)
        news_items.extend(mock_news)
        
        return news_items[:max_articles]
    
    async def _collect_market_news(
        self,
        sector: Optional[str],
        days: int,
        max_articles: int
    ) -> List[NewsItem]:
        """시장 또는 섹터 뉴스 수집."""
        
        # 검색 키워드 설정
        if sector:
            search_keywords = [sector, f"{sector} 업종", f"{sector} 주식"]
        else:
            search_keywords = ["코스피", "코스닥", "주식시장", "증시"]
        
        news_items = []
        
        # 모의 뉴스 생성
        mock_news = await self._generate_mock_market_news(sector, days)
        news_items.extend(mock_news)
        
        return news_items[:max_articles]
    
    async def _generate_mock_news(self, ticker: str, company_name: str, days: int) -> List[NewsItem]:
        """모의 뉴스 생성 (테스트용)."""
        mock_news = []
        
        # 종목별 뉴스 템플릿
        news_templates = {
            "005930": [  # 삼성전자
                f"{company_name}, 3분기 실적 시장 예상치 상회",
                f"{company_name} 반도체 메모리 부문 회복세",
                f"{company_name} AI 칩 개발 투자 확대 발표",
                f"{company_name} 스마트폰 신제품 출시로 주가 상승"
            ],
            "000660": [  # SK하이닉스
                f"{company_name} HBM 메모리 수요 급증으로 매출 증가",
                f"{company_name} AI 메모리 반도체 시장 선점",
                f"{company_name} 중국 공장 가동률 상승"
            ],
            "035420": [  # 네이버
                f"{company_name} 클라우드 사업 성장세 지속",
                f"{company_name} AI 검색 서비스 고도화",
                f"{company_name} 웹툰 해외 진출 확대"
            ]
        }
        
        # 기본 뉴스 템플릿
        default_templates = [
            f"{company_name} 주가 상승세 지속",
            f"{company_name} 투자자 관심 증대",
            f"{company_name} 실적 개선 기대감",
            f"{company_name} 신사업 진출 소식"
        ]
        
        templates = news_templates.get(ticker, default_templates)
        
        for i, template in enumerate(templates):
            mock_news.append(NewsItem(
                title=template,
                content=f"{template}에 대한 상세 내용입니다. 시장 전문가들은 긍정적인 전망을 보이고 있습니다.",
                url=f"https://example.com/news/{ticker}_{i}",
                published_date=datetime.now() - timedelta(days=i),
                source="mock_news",
                ticker=ticker
            ))
        
        return mock_news
    
    async def _generate_mock_market_news(self, sector: Optional[str], days: int) -> List[NewsItem]:
        """모의 시장 뉴스 생성."""
        mock_news = []
        
        if sector == "반도체":
            templates = [
                "반도체 업종 회복세, AI 수요 증가로 호황",
                "메모리 반도체 가격 상승 추세",
                "반도체 장비업체들 수주 증가"
            ]
        elif sector == "바이오":
            templates = [
                "바이오 신약 개발 성과 잇따라",
                "제약업계 해외 진출 확대",
                "바이오 벤처 투자 활발"
            ]
        else:
            templates = [
                "코스피 상승세 지속, 외국인 매수 증가",
                "증시 호재 요인 부각",
                "주식시장 변동성 축소"
            ]
        
        for i, template in enumerate(templates):
            mock_news.append(NewsItem(
                title=template,
                content=f"{template}에 대한 시장 분석입니다.",
                url=f"https://example.com/market_news_{i}",
                published_date=datetime.now() - timedelta(days=i),
                source="mock_market_news"
            ))
        
        return mock_news
    
    async def _get_company_name(self, ticker: str) -> str:
        """종목 코드로 회사명 조회."""
        try:
            all_stocks = await self.stock_db.get_all_stocks()
            for stock in all_stocks:
                if stock.get('ticker') == ticker:
                    return stock.get('name', ticker)
            return ticker
        except:
            return ticker
    
    async def _analyze_news_sentiment(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """뉴스 감성 분석."""
        analyzed_news = []
        
        # 배치 처리로 성능 향상
        batch_size = 10
        for i in range(0, len(news_items), batch_size):
            batch = news_items[i:i + batch_size]
            
            # HyperCLOVA를 사용한 감성 분석
            batch_results = await self._batch_sentiment_analysis(batch)
            analyzed_news.extend(batch_results)
            
            await asyncio.sleep(0.5)  # API 제한 고려
        
        return analyzed_news
    
    async def _batch_sentiment_analysis(self, news_batch: List[NewsItem]) -> List[NewsItem]:
        """배치 단위 감성 분석."""
        
        # 뉴스 텍스트 준비
        news_texts = []
        for news in news_batch:
            combined_text = f"{news.title}. {news.content}"
            news_texts.append(combined_text)
        
        # HyperCLOVA 분석 요청
        context = f"""
다음 주식 관련 뉴스들의 감성을 분석해주세요. 각 뉴스에 대해 다음 형식으로 답변해주세요:

뉴스1: [호재/중립/악재] (점수: -100~100) - 핵심 키워드
뉴스2: [호재/중립/악재] (점수: -100~100) - 핵심 키워드
...

분석할 뉴스들:
{chr(10).join([f"뉴스{i+1}: {text}" for i, text in enumerate(news_texts)])}
"""
        
        system_prompt = """
당신은 주식 시장 전문 애널리스트입니다. 
뉴스의 투자 영향도를 정확히 분석하여 다음 기준으로 분류해주세요:

- 호재: 주가 상승에 긍정적 영향 (점수 1~100)
- 중립: 주가에 큰 영향 없음 (점수 -10~10)  
- 악재: 주가 하락에 부정적 영향 (점수 -100~-1)

핵심 키워드는 투자 판단에 중요한 단어 3개 이내로 제시해주세요.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            ai_response = await _call_hcx_async(messages)
            
            # AI 응답 파싱
            analyzed_batch = self._parse_sentiment_response(ai_response, news_batch)
            return analyzed_batch
            
        except Exception as e:
            logger.error(f"배치 감성 분석 실패: {e}")
            
            # 폴백: 키워드 기반 감성 분석
            return self._fallback_sentiment_analysis(news_batch)
    
    def _parse_sentiment_response(self, ai_response: str, news_batch: List[NewsItem]) -> List[NewsItem]:
        """AI 감성 분석 응답 파싱."""
        
        lines = ai_response.strip().split('\n')
        
        for i, news in enumerate(news_batch):
            try:
                if i < len(lines):
                    line = lines[i]
                    
                    # 감성 라벨 추출
                    if "호재" in line:
                        news.sentiment_label = "호재"
                    elif "악재" in line:
                        news.sentiment_label = "악재"
                    else:
                        news.sentiment_label = "중립"
                    
                    # 점수 추출
                    score_match = re.search(r'점수:\s*(-?\d+)', line)
                    if score_match:
                        news.sentiment_score = float(score_match.group(1))
                    else:
                        news.sentiment_score = 0.0
                    
                    # 키워드 추출
                    keyword_match = re.search(r'-\s*(.+)$', line)
                    if keyword_match:
                        keywords = [k.strip() for k in keyword_match.group(1).split(',')]
                        news.key_factors = keywords[:3]
                    
                    # 영향도 설정
                    if abs(news.sentiment_score) >= 50:
                        news.impact_level = "high"
                    elif abs(news.sentiment_score) >= 20:
                        news.impact_level = "medium"
                    else:
                        news.impact_level = "low"
                
            except Exception as e:
                logger.debug(f"감성 분석 파싱 실패 {i}: {e}")
                
                # 폴백 분석
                news = self._fallback_single_sentiment(news)
        
        return news_batch
    
    def _fallback_sentiment_analysis(self, news_batch: List[NewsItem]) -> List[NewsItem]:
        """폴백 감성 분석 (키워드 기반)."""
        
        for news in news_batch:
            news = self._fallback_single_sentiment(news)
        
        return news_batch
    
    def _fallback_single_sentiment(self, news: NewsItem) -> NewsItem:
        """개별 뉴스 폴백 감성 분석."""
        
        combined_text = f"{news.title} {news.content}".lower()
        
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in combined_text)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in combined_text)
        
        if positive_count > negative_count:
            news.sentiment_label = "호재"
            news.sentiment_score = min(positive_count * 20, 80)
            news.impact_level = "medium"
        elif negative_count > positive_count:
            news.sentiment_label = "악재"
            news.sentiment_score = -min(negative_count * 20, 80)
            news.impact_level = "medium"
        else:
            news.sentiment_label = "중립"
            news.sentiment_score = 0
            news.impact_level = "low"
        
        # 키워드 추출
        found_keywords = []
        for keyword in self.positive_keywords + self.negative_keywords:
            if keyword in combined_text:
                found_keywords.append(keyword)
        
        news.key_factors = found_keywords[:3]
        
        return news
    
    async def _classify_market_impact(self, news_items: List[NewsItem], ticker: str) -> List[NewsItem]:
        """시장 영향도 분류."""
        
        for news in news_items:
            # 뉴스 중요도 평가
            importance_score = self._calculate_news_importance(news, ticker)
            
            # 영향도 재조정
            if importance_score > 0.7:
                if news.impact_level != "high":
                    news.impact_level = "high"
                    news.sentiment_score *= 1.5  # 중요 뉴스는 영향도 증가
            elif importance_score < 0.3:
                news.impact_level = "low"
                news.sentiment_score *= 0.7  # 덜 중요한 뉴스는 영향도 감소
        
        return news_items
    
    def _calculate_news_importance(self, news: NewsItem, ticker: str) -> float:
        """뉴스 중요도 계산."""
        
        importance = 0.5  # 기본값
        
        title_lower = news.title.lower()
        content_lower = news.content.lower()
        
        # 종목명 직접 언급 시 중요도 증가
        company_name = ticker  # 실제로는 회사명 조회 필요
        if company_name.lower() in title_lower:
            importance += 0.3
        
        # 중요 키워드 포함 시 중요도 증가
        important_keywords = [
            "실적", "어닝", "배당", "합병", "인수", "상장", "상폐",
            "제재", "승인", "특허", "계약", "투자", "자금조달"
        ]
        
        for keyword in important_keywords:
            if keyword in title_lower or keyword in content_lower:
                importance += 0.1
        
        return min(importance, 1.0)
    
    async def _evaluate_investment_impact(self, news_items: List[NewsItem], ticker: str) -> Dict:
        """투자 영향 평가."""
        
        if not news_items:
            return {"overall_sentiment": "중립", "confidence": 0}
        
        # 전체 감성 점수 계산
        total_score = sum(news.sentiment_score for news in news_items if news.sentiment_score)
        avg_score = total_score / len(news_items) if news_items else 0
        
        # 호재/악재 개수
        positive_news = [n for n in news_items if n.sentiment_label == "호재"]
        negative_news = [n for n in news_items if n.sentiment_label == "악재"]
        neutral_news = [n for n in news_items if n.sentiment_label == "중립"]
        
        # 전체 감성 판단
        if avg_score > 20:
            overall_sentiment = "호재"
        elif avg_score < -20:
            overall_sentiment = "악재"
        else:
            overall_sentiment = "중립"
        
        # 신뢰도 계산 (뉴스 수와 일관성 기반)
        confidence = min(len(news_items) / 10 * 0.5 + 0.3, 1.0)
        
        # 주요 이슈 추출
        key_issues = self._extract_key_issues(news_items)
        
        # 투자 추천 생성
        investment_recommendation = self._generate_investment_recommendation(
            overall_sentiment, avg_score, confidence
        )
        
        return {
            "overall_sentiment": overall_sentiment,
            "average_score": round(avg_score, 2),
            "confidence": round(confidence, 2),
            "positive_count": len(positive_news),
            "negative_count": len(negative_news),
            "neutral_count": len(neutral_news),
            "key_issues": key_issues,
            "investment_recommendation": investment_recommendation
        }
    
    def _extract_key_issues(self, news_items: List[NewsItem]) -> List[Dict]:
        """주요 이슈 추출."""
        
        # 키워드 빈도 분석
        keyword_counts = {}
        for news in news_items:
            if news.key_factors:
                for keyword in news.key_factors:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # 상위 키워드들을 이슈로 구성
        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        key_issues = []
        for keyword, count in top_keywords:
            # 해당 키워드가 포함된 뉴스들의 평균 감성
            related_news = [n for n in news_items if n.key_factors and keyword in n.key_factors]
            avg_sentiment = sum(n.sentiment_score for n in related_news) / len(related_news)
            
            key_issues.append({
                "issue": keyword,
                "frequency": count,
                "sentiment_impact": round(avg_sentiment, 2),
                "impact_type": "호재" if avg_sentiment > 10 else "악재" if avg_sentiment < -10 else "중립"
            })
        
        return key_issues
    
    def _generate_investment_recommendation(self, sentiment: str, score: float, confidence: float) -> str:
        """투자 추천 의견 생성."""
        
        if confidence < 0.3:
            return "정보 부족으로 판단 보류"
        
        if sentiment == "호재" and score > 40:
            return "적극 매수 고려"
        elif sentiment == "호재" and score > 20:
            return "매수 관심"
        elif sentiment == "악재" and score < -40:
            return "매도 검토"
        elif sentiment == "악재" and score < -20:
            return "관망 권장"
        else:
            return "중립적 관점 유지"
    
    async def _generate_ai_news_summary(self, news_items: List[NewsItem], ticker: str) -> str:
        """AI 기반 뉴스 종합 분석."""
        
        # 주요 뉴스들만 선별 (상위 10개)
        top_news = sorted(news_items, key=lambda x: abs(x.sentiment_score or 0), reverse=True)[:10]
        
        news_summary = []
        for i, news in enumerate(top_news, 1):
            summary = f"{i}. [{news.sentiment_label}] {news.title}"
            if news.key_factors:
                summary += f" (키워드: {', '.join(news.key_factors[:2])})"
            news_summary.append(summary)
        
        context = f"""
종목 코드: {ticker}
분석 기간: 최근 7일
총 뉴스 수: {len(news_items)}개

주요 뉴스 목록:
{chr(10).join(news_summary)}

위 뉴스들을 종합하여 다음 관점에서 분석해주세요:

1. **주요 이슈 요약**
   - 가장 중요한 호재/악재 요인
   - 시장에 미치는 영향도 평가

2. **투자 관점 분석**
   - 단기 주가 영향 전망
   - 중장기 투자 관점에서의 의미
   
3. **리스크 요인**
   - 주의해야 할 부정적 요소
   - 불확실성 요인들

4. **투자 전략 제언**
   - 현재 상황에서의 투자 접근법
   - 향후 주목해야 할 포인트

객관적이고 균형잡힌 분석을 제공해주세요.
"""
        
        system_prompt = """
당신은 증권 애널리스트이자 뉴스 분석 전문가입니다.
뉴스 정보를 바탕으로 객관적이고 전문적인 투자 분석을 제공하세요.

분석 원칙:
1. 감정적 판단보다 사실 기반 분석
2. 긍정적/부정적 요소 균형적 제시
3. 투자 위험 요소 명확히 고지
4. 구체적이고 실행 가능한 조언
5. 시장 변동성과 불확실성 고려

절대 투자 수익을 보장하지 말고, 모든 분석은 참고용임을 명시하세요.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            ai_summary = await _call_hcx_async(messages)
            return ai_summary
        except Exception as e:
            logger.error(f"AI 뉴스 요약 생성 실패: {e}")
            return f"뉴스 분석을 완료했으나 AI 요약 생성에 실패했습니다. 오류: {str(e)}"
    
    def _calculate_sentiment_overview(self, news_items: List[NewsItem]) -> Dict:
        """감성 개요 계산."""
        
        if not news_items:
            return {}
        
        sentiments = [n.sentiment_score for n in news_items if n.sentiment_score is not None]
        
        if not sentiments:
            return {}
        
        import numpy as np
        
        return {
            "average_sentiment": round(sum(sentiments) / len(sentiments), 2),
            "max_positive": max(sentiments),
            "max_negative": min(sentiments),
            "sentiment_volatility": round(np.std(sentiments), 2),
            "positive_ratio": len([s for s in sentiments if s > 10]) / len(sentiments),
            "negative_ratio": len([s for s in sentiments if s < -10]) / len(sentiments)
        }
    
    def _extract_market_signals(self, news_items: List[NewsItem]) -> List[Dict]:
        """시장 신호 추출."""
        
        signals = []
        
        # 강한 호재/악재 신호
        strong_signals = [n for n in news_items if abs(n.sentiment_score or 0) > 50]
        
        for news in strong_signals[:5]:  # 상위 5개
            signals.append({
                "signal_type": "강한 " + news.sentiment_label,
                "title": news.title,
                "impact_score": news.sentiment_score,
                "key_factors": news.key_factors,
                "published_date": news.published_date.strftime('%Y-%m-%d %H:%M')
            })
        
        return signals
    
    async def _analyze_sector_impact(self, news_items: List[NewsItem], sector: Optional[str]) -> Dict:
        """섹터별 영향 분석."""
        
        # 섹터별 뉴스 분류 (임시 구현)
        sector_news = {}
        
        for news in news_items:
            # 뉴스에서 섹터 키워드 추출
            detected_sectors = self._detect_sectors_from_news(news)
            
            for detected_sector in detected_sectors:
                if detected_sector not in sector_news:
                    sector_news[detected_sector] = []
                sector_news[detected_sector].append(news)
        
        # 섹터별 감성 분석
        sector_analysis = {}
        for sector_name, sector_news_list in sector_news.items():
            if len(sector_news_list) >= 2:  # 최소 2개 이상 뉴스
                avg_sentiment = sum(n.sentiment_score for n in sector_news_list) / len(sector_news_list)
                
                sector_analysis[sector_name] = {
                    "news_count": len(sector_news_list),
                    "average_sentiment": round(avg_sentiment, 2),
                    "sentiment_label": "호재" if avg_sentiment > 10 else "악재" if avg_sentiment < -10 else "중립"
                }
        
        return sector_analysis
    
    def _detect_sectors_from_news(self, news: NewsItem) -> List[str]:
        """뉴스에서 섹터 감지."""
        
        sector_keywords = {
            "반도체": ["반도체", "메모리", "DRAM", "NAND", "웨이퍼"],
            "바이오": ["바이오", "제약", "신약", "임상", "의료"],
            "게임": ["게임", "엔터테인먼트", "모바일게임", "PC게임"],
            "금융": ["은행", "증권", "보험", "카드", "핀테크"],
            "자동차": ["자동차", "전기차", "배터리", "모빌리티"],
            "건설": ["건설", "부동산", "아파트", "재개발"],
            "화학": ["화학", "정유", "석유화학", "플라스틱"],
            "철강": ["철강", "제철", "강재", "철광석"],
            "조선": ["조선", "해운", "선박", "해양플랜트"]
        }
        
        detected = []
        combined_text = f"{news.title} {news.content}".lower()
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                detected.append(sector)
        
        return detected
    
    async def _analyze_market_trends(self, news_items: List[NewsItem]) -> Dict:
        """시장 트렌드 분석."""
        
        # 시간별 트렌드
        recent_24h = [n for n in news_items if 
                     (datetime.now() - n.published_date).total_seconds() < 24*3600]
        recent_week = news_items
        
        trends = {
            "24h_sentiment": self._calculate_period_sentiment(recent_24h),
            "week_sentiment": self._calculate_period_sentiment(recent_week),
            "momentum": self._calculate_momentum(news_items),
            "key_themes": self._extract_key_themes(news_items),
            "market_mood": self._assess_market_mood(news_items)
        }
        
        return trends
    
    def _calculate_period_sentiment(self, news_items: List[NewsItem]) -> Dict:
        """기간별 감성 계산."""
        
        if not news_items:
            return {"average": 0, "count": 0}
        
        sentiments = [n.sentiment_score for n in news_items if n.sentiment_score is not None]
        
        return {
            "average": round(sum(sentiments) / len(sentiments), 2) if sentiments else 0,
            "count": len(sentiments)
        }
    
    def _calculate_momentum(self, news_items: List[NewsItem]) -> str:
        """시장 모멘텀 계산."""
        
        if len(news_items) < 4:
            return "불명확"
        
        # 최근과 이전 뉴스 비교
        sorted_news = sorted(news_items, key=lambda x: x.published_date, reverse=True)
        
        recent_half = sorted_news[:len(sorted_news)//2]
        earlier_half = sorted_news[len(sorted_news)//2:]
        
        recent_avg = sum(n.sentiment_score for n in recent_half if n.sentiment_score) / len(recent_half)
        earlier_avg = sum(n.sentiment_score for n in earlier_half if n.sentiment_score) / len(earlier_half)
        
        if recent_avg > earlier_avg + 10:
            return "상승"
        elif recent_avg < earlier_avg - 10:
            return "하락"
        else:
            return "횡보"
    
    def _extract_key_themes(self, news_items: List[NewsItem]) -> List[str]:
        """주요 테마 추출."""
        
        all_keywords = []
        for news in news_items:
            if news.key_factors:
                all_keywords.extend(news.key_factors)
        
        # 빈도 기반 상위 테마
        from collections import Counter
        keyword_counts = Counter(all_keywords)
        
        return [keyword for keyword, count in keyword_counts.most_common(5)]
    
    def _assess_market_mood(self, news_items: List[NewsItem]) -> str:
        """시장 분위기 평가."""
        
        if not news_items:
            return "중립"
        
        avg_sentiment = sum(n.sentiment_score for n in news_items if n.sentiment_score) / len(news_items)
        
        if avg_sentiment > 30:
            return "매우 긍정적"
        elif avg_sentiment > 10:
            return "긍정적"
        elif avg_sentiment < -30:
            return "매우 부정적"
        elif avg_sentiment < -10:
            return "부정적"
        else:
            return "중립적"
    
    def _identify_risk_factors(self, news_items: List[NewsItem]) -> List[Dict]:
        """리스크 요인 식별."""
        
        risk_keywords = [
            "제재", "규제", "조사", "소송", "벌금", "손실", "적자", 
            "하락", "위험", "우려", "불안", "충격", "위기"
        ]
        
        risk_factors = []
        
        for news in news_items:
            if news.sentiment_label == "악재":
                combined_text = f"{news.title} {news.content}".lower()
                
                for risk_keyword in risk_keywords:
                    if risk_keyword in combined_text:
                        risk_factors.append({
                            "risk_type": risk_keyword,
                            "news_title": news.title,
                            "impact_score": news.sentiment_score,
                            "date": news.published_date.strftime('%Y-%m-%d')
                        })
                        break
        
        return risk_factors[:5]  # 상위 5개
    
    async def _generate_ai_market_analysis(self, news_items: List[NewsItem], sector: Optional[str]) -> str:
        """AI 시장 분석 생성."""
        
        # 주요 뉴스 요약
        top_news = sorted(news_items, key=lambda x: abs(x.sentiment_score or 0), reverse=True)[:15]
        
        news_summary = []
        for i, news in enumerate(top_news, 1):
            summary = f"{i}. [{news.sentiment_label}] {news.title}"
            news_summary.append(summary)
        
        target = sector or "전체 주식시장"
        
        context = f"""
분석 대상: {target}
분석 기간: 최근 3일
총 뉴스 수: {len(news_items)}개

주요 뉴스 헤드라인:
{chr(10).join(news_summary)}

위 뉴스들을 바탕으로 {target}의 현재 상황을 분석해주세요:

1. **시장 현황 진단**
   - 전반적인 시장 분위기
   - 주요 이슈와 관심사

2. **투자 환경 분석**
   - 긍정적 요인들
   - 부정적 요인들
   - 불확실성 요소

3. **섹터별 영향**
   - 수혜 업종과 피해 업종
   - 업종간 차별화 요인

4. **향후 전망**
   - 단기 시장 방향성
   - 주요 관전 포인트

5. **투자 전략**
   - 현 시점 투자 접근법
   - 리스크 관리 방안

전문적이고 객관적인 시각으로 분석해주세요.
"""
        
        system_prompt = """
당신은 시장 분석 전문가이자 투자 전략가입니다.
뉴스와 시장 동향을 종합하여 투자자들에게 유용한 인사이트를 제공하세요.

분석 원칙:
1. 객관적 사실에 기반한 분석
2. 다각도 관점에서의 균형잡힌 평가
3. 시장 리스크와 기회 요인 명시
4. 실무적이고 구체적인 조언
5. 시장의 불확실성과 변동성 고려

투자 의견은 참고용이며, 투자자 개인의 판단이 중요함을 명시하세요.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
        
        try:
            market_analysis = await _call_hcx_async(messages)
            return market_analysis
        except Exception as e:
            logger.error(f"AI 시장 분석 생성 실패: {e}")
            return f"시장 뉴스 분석을 완료했으나 AI 종합 분석 생성에 실패했습니다. 오류: {str(e)}"


# 전역 인스턴스
news_analysis_service = NewsAnalysisService()