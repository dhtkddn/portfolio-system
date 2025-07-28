#!/usr/bin/env python3
"""
실제 사용 시나리오 테스트 - 답변 형식, 근거 제시, 재무제표 비교, 생소한 종목 처리
Real Usage Scenario Tests - Response Format, Evidence, Financial Statement Comparison, Obscure Stocks
"""

import asyncio
import time
import logging
import json
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_agent import _handle_portfolio_request, chat_with_agent
from app.services.stock_database import StockDatabase

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealScenarioTestSuite:
    """실제 사용 시나리오 테스트"""
    
    def __init__(self):
        self.db = StockDatabase()
        self.test_results = {}
    
    async def run_all_tests(self):
        """모든 실제 시나리오 테스트 실행"""
        print("🚀 실제 사용 시나리오 테스트 시작\n")
        print("=" * 80)
        
        # 1. 재무제표 비교 질문 테스트
        await self.test_financial_comparison_questions()
        
        # 2. 재무제표 개별 질문 테스트  
        await self.test_individual_financial_questions()
        
        # 3. 포트폴리오 생성 질문 테스트
        await self.test_portfolio_creation_questions()
        
        # 4. 생소한 종목 처리 테스트
        await self.test_obscure_stocks()
        
        # 5. 답변 형식 및 띄어쓰기 테스트
        await self.test_response_formatting()
        
        # 결과 출력
        self.print_comprehensive_results()
    
    async def test_financial_comparison_questions(self):
        """재무제표 비교 질문 테스트"""
        print("📊 1. 재무제표 비교 질문 테스트")
        print("-" * 50)
        
        test_cases = [
            {
                "name": "대형주 재무비교",
                "message": "삼성전자와 SK하이닉스의 2024년 재무제표를 비교해서 어느 회사가 더 투자매력적인지 분석해주세요. 매출액, 영업이익, 당기순이익을 근거로 설명해주세요.",
                "expected_companies": ["삼성전자", "SK하이닉스"]
            },
            {
                "name": "업종별 재무비교", 
                "message": "네이버와 카카오의 최근 3년간 재무성과를 비교분석해주세요. 성장성과 수익성 지표를 중심으로 상세히 설명해주세요.",
                "expected_companies": ["네이버", "카카오"]
            },
            {
                "name": "미래에셋 관련 비교",
                "message": "미래에셋증권과 미래에셋생명보험의 2024년 재무실적을 비교해주세요. 영업이익과 당기순이익을 중심으로 분석해주세요.",
                "expected_companies": ["미래에셋증권", "미래에셋생명보험"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 테스트 {i}: {test_case['name']}")
            print(f"질문: {test_case['message']}")
            print("응답:")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                # 재무제표 비교 질문 처리
                user_profile = {
                    "investment_amount": 1000,
                    "risk_tolerance": "중립형",
                    "experience_level": "중급",
                    "age": 35
                }
                
                result = await chat_with_agent(test_case["message"], user_profile)
                end_time = time.time()
                
                # 응답 분석
                response_text = result.get("message", "")
                
                # 띄어쓰기 및 문단 구성 체크
                paragraph_count = response_text.count('\n\n')
                sentence_count = response_text.count('.')
                
                # 회사명 언급 체크
                mentioned_companies = []
                for company in test_case["expected_companies"]:
                    if company in response_text:
                        mentioned_companies.append(company)
                
                # 재무수치 근거 체크
                financial_terms = ["매출액", "영업이익", "당기순이익", "원", "조", "억"]
                financial_mentions = sum(1 for term in financial_terms if term in response_text)
                
                print(response_text)
                print()
                print(f"📊 분석 결과:")
                print(f"   응답시간: {end_time - start_time:.2f}초")
                print(f"   응답 길이: {len(response_text)}자")
                print(f"   문단 수: {paragraph_count + 1}개")
                print(f"   문장 수: 약 {sentence_count}개")
                print(f"   언급된 회사: {mentioned_companies}")
                print(f"   재무용어 언급: {financial_mentions}회")
                
                self.test_results[f"financial_comparison_{i}"] = {
                    "status": "SUCCESS",
                    "response_time": f"{end_time - start_time:.2f}초",
                    "response_length": len(response_text),
                    "paragraph_count": paragraph_count + 1,
                    "companies_mentioned": mentioned_companies,
                    "financial_terms_count": financial_mentions,
                    "has_proper_formatting": paragraph_count >= 2
                }
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                self.test_results[f"financial_comparison_{i}"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
            
            print("=" * 80)
    
    async def test_individual_financial_questions(self):
        """개별 재무제표 질문 테스트"""
        print("\n💰 2. 개별 재무제표 질문 테스트")
        print("-" * 50)
        
        test_cases = [
            {
                "name": "삼성전자 재무현황",
                "message": "삼성전자의 2024년 재무실적이 어떻게 되나요? 매출액과 영업이익, 순이익을 구체적인 숫자로 알려주세요.",
                "ticker": "005930"
            },
            {
                "name": "현대차 성장성",
                "message": "현대자동차의 최근 3년간 매출 성장률은 어떻게 되나요? 2022년, 2023년, 2024년 매출액을 비교해서 성장 추이를 분석해주세요.",
                "ticker": "005380"
            },
            {
                "name": "LG화학 수익성",
                "message": "LG화학의 영업이익률이 어느 정도인지 알고 싶어요. 2024년 매출액 대비 영업이익 비율과 업계 평균과 비교해서 설명해주세요.",
                "ticker": "051910"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 테스트 {i}: {test_case['name']}")
            print(f"질문: {test_case['message']}")
            print("응답:")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                user_profile = {
                    "investment_amount": 1000,
                    "risk_tolerance": "중립형",
                    "experience_level": "중급",
                    "age": 35
                }
                
                result = await chat_with_agent(test_case["message"], user_profile)
                end_time = time.time()
                
                response_text = result.get("message", "")
                
                # 숫자/데이터 근거 체크
                import re
                numbers = re.findall(r'[\d,]+(?:\.\d+)?(?:조|억|만|원|%)', response_text)
                years_mentioned = re.findall(r'20\d{2}년?', response_text)
                
                print(response_text)
                print()
                print(f"📊 분석 결과:")
                print(f"   응답시간: {end_time - start_time:.2f}초")
                print(f"   응답 길이: {len(response_text)}자")
                print(f"   구체적 수치: {len(numbers)}개 ({numbers[:5]}...)")
                print(f"   연도 언급: {len(years_mentioned)}개 ({years_mentioned})")
                
                self.test_results[f"individual_financial_{i}"] = {
                    "status": "SUCCESS",
                    "response_time": f"{end_time - start_time:.2f}초",
                    "response_length": len(response_text),
                    "numbers_mentioned": len(numbers),
                    "years_mentioned": len(years_mentioned),
                    "has_concrete_data": len(numbers) >= 3
                }
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                self.test_results[f"individual_financial_{i}"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
            
            print("=" * 80)
    
    async def test_portfolio_creation_questions(self):
        """포트폴리오 생성 질문 테스트"""
        print("\n📈 3. 포트폴리오 생성 질문 테스트")
        print("-" * 50)
        
        test_cases = [
            {
                "name": "미래에셋 포함 포트폴리오",
                "message": "5천만원으로 미래에셋 관련 종목을 포함해서 안정적인 포트폴리오를 구성해주세요. 각 종목별 투자 비중과 선정 이유를 자세히 설명해주세요.",
                "profile": {
                    "investment_amount": 5000,
                    "risk_tolerance": "안전형",
                    "experience_level": "초보",
                    "age": 45,
                    "total_assets": 20000,
                    "income_level": 80000000
                }
            },
            {
                "name": "성장주 중심 포트폴리오",
                "message": "2천만원으로 코스닥 성장주 위주의 공격적인 포트폴리오를 만들어주세요. 향후 3년간 성장 가능성이 높은 종목들로 구성하고, 각 종목의 성장 근거를 제시해주세요.",
                "profile": {
                    "investment_amount": 2000,
                    "risk_tolerance": "공격형",
                    "experience_level": "고급",
                    "age": 30,
                    "total_assets": 5000,
                    "income_level": 120000000
                }
            },
            {
                "name": "대형주 중심 균형 포트폴리오",
                "message": "1억원으로 코스피 대형주 중심의 균형잡힌 포트폴리오를 구성해주세요. 배당수익과 장기 성장을 동시에 추구할 수 있는 종목들로 구성하고, 투자자 보호 관련 주의사항도 함께 알려주세요.",
                "profile": {
                    "investment_amount": 10000,
                    "risk_tolerance": "중립형",
                    "experience_level": "중급",
                    "age": 40,
                    "total_assets": 30000,
                    "income_level": 100000000
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 테스트 {i}: {test_case['name']}")
            print(f"질문: {test_case['message']}")
            print("응답:")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                result = await _handle_portfolio_request(test_case["message"], test_case["profile"])
                end_time = time.time()
                
                response_text = result.get("message", "")
                recommendations = result.get("recommendations", [])
                investor_protection = result.get("investor_protection", {})
                
                # 포트폴리오 구성 분석
                total_weight = sum(rec.get("target_weight", 0) for rec in recommendations)
                stock_names = [rec.get("name", "N/A") for rec in recommendations]
                
                # 투자자 보호 정보 체크
                protection_warnings = investor_protection.get("warnings", {})
                total_warnings = sum(len(warnings) for warnings in protection_warnings.values())
                
                print(response_text)
                
                if recommendations:
                    print("\n💼 추천 포트폴리오:")
                    for rec in recommendations:
                        name = rec.get("name", "N/A")
                        weight = rec.get("target_weight", 0)
                        reason = rec.get("reason", "N/A")
                        print(f"   • {name}: {weight:.1%}")
                        print(f"     이유: {reason[:100]}...")
                
                if investor_protection:
                    print(f"\n🛡️ 투자자 보호:")
                    print(f"   위험등급: {investor_protection.get('risk_level', 'N/A')}")
                    print(f"   투자자유형: {investor_protection.get('investor_type', 'N/A')}")
                    print(f"   적합성: {investor_protection.get('is_suitable', 'N/A')}")
                    print(f"   경고사항: {total_warnings}개")
                
                print()
                print(f"📊 분석 결과:")
                print(f"   응답시간: {end_time - start_time:.2f}초")
                print(f"   응답 길이: {len(response_text)}자")
                print(f"   추천 종목 수: {len(recommendations)}개")
                print(f"   총 투자비중: {total_weight:.1%}")
                print(f"   투자자보호 경고: {total_warnings}개")
                
                self.test_results[f"portfolio_creation_{i}"] = {
                    "status": "SUCCESS",
                    "response_time": f"{end_time - start_time:.2f}초",
                    "response_length": len(response_text),
                    "recommendations_count": len(recommendations),
                    "total_weight": total_weight,
                    "protection_warnings": total_warnings,
                    "has_investor_protection": bool(investor_protection)
                }
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                self.test_results[f"portfolio_creation_{i}"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
            
            print("=" * 80)
    
    async def test_obscure_stocks(self):
        """생소한 종목 처리 테스트"""
        print("\n🔍 4. 생소한 종목 처리 테스트")
        print("-" * 50)
        
        # DB에서 생소한 종목들 찾기
        try:
            stocks_df = self.db.get_all_stocks_for_screening()
            # 시가총액이 낮거나 일반적이지 않은 종목들 선별
            obscure_stocks = stocks_df[
                (~stocks_df['name'].str.contains('삼성|LG|SK|현대|네이버|카카오', na=False)) &
                (stocks_df['market'] == 'KOSDAQ')
            ].head(5)
            
            test_cases = []
            for _, stock in obscure_stocks.iterrows():
                test_cases.append({
                    "name": f"{stock['name']} 분석",
                    "message": f"{stock['name']}({stock['ticker']})의 재무현황과 투자매력도를 분석해주세요. 이 회사의 주요 사업분야와 최근 실적을 구체적으로 설명해주세요.",
                    "ticker": stock['ticker'],
                    "company_name": stock['name']
                })
            
        except Exception as e:
            print(f"⚠️ 생소한 종목 선별 실패: {e}")
            # 대체 테스트 케이스
            test_cases = [
                {
                    "name": "크리스탈신소재 분석",
                    "message": "크리스탈신소재의 재무현황과 투자매력도를 분석해주세요. 이 회사의 주요 사업분야와 최근 실적을 구체적으로 설명해주세요.",
                    "ticker": "900250",
                    "company_name": "크리스탈신소재"
                }
            ]
        
        for i, test_case in enumerate(test_cases[:3], 1):  # 상위 3개만 테스트
            print(f"\n📋 테스트 {i}: {test_case['name']}")
            print(f"질문: {test_case['message']}")
            print("응답:")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                user_profile = {
                    "investment_amount": 1000,
                    "risk_tolerance": "중립형",
                    "experience_level": "중급",
                    "age": 35
                }
                
                result = await chat_with_agent(test_case["message"], user_profile)
                end_time = time.time()
                
                response_text = result.get("message", "")
                
                # 회사 정보 제공 여부 체크
                company_mentioned = test_case["company_name"] in response_text
                has_business_info = any(term in response_text for term in ["사업", "업종", "제품", "서비스"])
                has_financial_data = any(term in response_text for term in ["매출", "영업이익", "당기순이익"])
                
                print(response_text)
                print()
                print(f"📊 분석 결과:")
                print(f"   응답시간: {end_time - start_time:.2f}초")
                print(f"   응답 길이: {len(response_text)}자")
                print(f"   회사명 언급: {company_mentioned}")
                print(f"   사업정보 포함: {has_business_info}")
                print(f"   재무정보 포함: {has_financial_data}")
                
                self.test_results[f"obscure_stock_{i}"] = {
                    "status": "SUCCESS",
                    "response_time": f"{end_time - start_time:.2f}초",
                    "response_length": len(response_text),
                    "company_mentioned": company_mentioned,
                    "has_business_info": has_business_info,
                    "has_financial_data": has_financial_data
                }
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                self.test_results[f"obscure_stock_{i}"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
            
            print("=" * 80)
    
    async def test_response_formatting(self):
        """답변 형식 및 띄어쓰기 테스트"""
        print("\n📝 5. 답변 형식 및 띄어쓰기 테스트")
        print("-" * 50)
        
        test_cases = [
            {
                "name": "복합 질문 처리",
                "message": "삼성전자의 2024년 실적을 분석하고, 향후 투자 전망도 함께 알려주세요. 그리고 5천만원으로 삼성전자를 포함한 포트폴리오도 추천해주세요.",
                "check_points": ["실적분석", "투자전망", "포트폴리오추천"]
            },
            {
                "name": "긴 답변 형식",
                "message": "한국 반도체 업계의 현황과 전망을 상세히 분석해주세요. 삼성전자, SK하이닉스의 경쟁력 비교와 함께 글로벌 시장에서의 위치, 향후 5년간 성장 가능성, 투자 시 주의사항을 모두 포함해서 설명해주세요.",
                "check_points": ["업계현황", "경쟁력비교", "글로벌위치", "성장가능성", "주의사항"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 테스트 {i}: {test_case['name']}")
            print(f"질문: {test_case['message']}")
            print("응답:")
            print("-" * 40)
            
            start_time = time.time()
            
            try:
                user_profile = {
                    "investment_amount": 5000,
                    "risk_tolerance": "중립형",
                    "experience_level": "중급",
                    "age": 35
                }
                
                result = await chat_with_agent(test_case["message"], user_profile)
                end_time = time.time()
                
                response_text = result.get("message", "")
                
                # 형식 분석
                paragraphs = response_text.split('\n\n')
                paragraph_count = len([p for p in paragraphs if p.strip()])
                
                # 체크포인트 확인
                covered_points = []
                for point in test_case["check_points"]:
                    if any(keyword in response_text for keyword in [point[:2], point[:3]]):
                        covered_points.append(point)
                
                # 문장 구조 분석
                sentences = response_text.split('.')
                avg_sentence_length = sum(len(s.strip()) for s in sentences if s.strip()) / max(len(sentences), 1)
                
                # 띄어쓰기 품질 (간단한 휴리스틱)
                words = response_text.split()
                long_words = [w for w in words if len(w) > 10]  # 띄어쓰기 누락 가능성
                
                print(response_text[:1000] + "..." if len(response_text) > 1000 else response_text)
                print()
                print(f"📊 형식 분석 결과:")
                print(f"   응답시간: {end_time - start_time:.2f}초")
                print(f"   전체 길이: {len(response_text)}자")
                print(f"   문단 수: {paragraph_count}개")
                print(f"   평균 문장 길이: {avg_sentence_length:.1f}자")
                print(f"   다룬 주제: {len(covered_points)}/{len(test_case['check_points'])}개")
                print(f"   주제 목록: {covered_points}")
                print(f"   긴 단어 수: {len(long_words)}개 (띄어쓰기 체크)")
                
                self.test_results[f"formatting_{i}"] = {
                    "status": "SUCCESS",
                    "response_time": f"{end_time - start_time:.2f}초",
                    "response_length": len(response_text),
                    "paragraph_count": paragraph_count,
                    "covered_points": len(covered_points),
                    "total_points": len(test_case["check_points"]),
                    "avg_sentence_length": avg_sentence_length,
                    "formatting_quality": "good" if paragraph_count >= 3 else "needs_improvement"
                }
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                self.test_results[f"formatting_{i}"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
            
            print("=" * 80)
    
    def print_comprehensive_results(self):
        """종합 결과 출력"""
        print("\n" + "=" * 80)
        print("📋 실제 사용 시나리오 테스트 종합 결과")
        print("=" * 80)
        
        # 전체 통계
        total_tests = len(self.test_results)
        success_tests = sum(1 for r in self.test_results.values() if r.get("status") == "SUCCESS")
        failed_tests = total_tests - success_tests
        
        print(f"\n📊 전체 통계:")
        print(f"   총 테스트: {total_tests}개")
        print(f"   성공: {success_tests}개 ✅")
        print(f"   실패: {failed_tests}개 ❌")
        print(f"   성공률: {success_tests/total_tests*100:.1f}%")
        
        # 카테고리별 결과
        categories = {
            "financial_comparison": "재무제표 비교",
            "individual_financial": "개별 재무질문", 
            "portfolio_creation": "포트폴리오 생성",
            "obscure_stock": "생소한 종목",
            "formatting": "답변 형식"
        }
        
        print(f"\n📈 카테고리별 결과:")
        for category, name in categories.items():
            category_tests = [k for k in self.test_results.keys() if k.startswith(category)]
            if category_tests:
                success_count = sum(1 for k in category_tests 
                                  if self.test_results[k].get("status") == "SUCCESS")
                total_count = len(category_tests)
                print(f"   {name}: {success_count}/{total_count} ({'✅' if success_count == total_count else '⚠️'})")
        
        # 품질 지표 분석
        print(f"\n🎯 품질 지표:")
        
        # 응답 시간 분석
        response_times = []
        for result in self.test_results.values():
            if result.get("status") == "SUCCESS" and result.get("response_time"):
                try:
                    time_str = result["response_time"].replace("초", "")
                    response_times.append(float(time_str))
                except:
                    continue
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            print(f"   평균 응답시간: {avg_time:.2f}초")
            print(f"   최대 응답시간: {max_time:.2f}초")
            print(f"   최소 응답시간: {min_time:.2f}초")
        
        # 응답 길이 분석
        response_lengths = [r.get("response_length", 0) for r in self.test_results.values() 
                          if r.get("status") == "SUCCESS"]
        if response_lengths:
            avg_length = sum(response_lengths) / len(response_lengths)
            print(f"   평균 응답길이: {avg_length:.0f}자")
            print(f"   최대 응답길이: {max(response_lengths)}자")
            print(f"   최소 응답길이: {min(response_lengths)}자")
        
        # 투자자 보호 기능 체크
        protection_tests = [r for r in self.test_results.values() 
                          if "has_investor_protection" in r]
        if protection_tests:
            protection_rate = sum(1 for r in protection_tests if r["has_investor_protection"]) / len(protection_tests)
            print(f"   투자자보호 적용률: {protection_rate*100:.1f}%")
        
        # 구체적 데이터 제공율
        data_tests = [r for r in self.test_results.values() 
                     if "has_concrete_data" in r]
        if data_tests:
            data_rate = sum(1 for r in data_tests if r["has_concrete_data"]) / len(data_tests)
            print(f"   구체적 데이터 제공률: {data_rate*100:.1f}%")
        
        # 최종 평가
        print(f"\n🏆 최종 평가:")
        if success_tests == total_tests:
            print("   🟢 우수: 모든 시나리오 테스트 통과")
        elif success_tests >= total_tests * 0.8:
            print("   🟡 양호: 대부분의 시나리오 처리 가능") 
        else:
            print("   🔴 개선필요: 일부 시나리오에서 문제 발생")
        
        # 개선 권고사항
        print(f"\n💡 개선 권고사항:")
        if failed_tests > 0:
            print("   - 실패한 테스트 케이스 분석 및 수정 필요")
        if response_times and max(response_times) > 20:
            print("   - 응답 시간 최적화 필요 (20초 이상 케이스 존재)")
        if response_lengths and min(response_lengths) < 200:
            print("   - 일부 응답이 너무 짧음, 상세도 개선 필요")
        
        print(f"\n🎉 실제 사용 시나리오 테스트 완료!")

async def main():
    """메인 테스트 실행"""
    test_suite = RealScenarioTestSuite()
    await test_suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())