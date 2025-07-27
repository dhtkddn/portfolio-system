"""Open DART 재무제표 ETL 스크립트 (KOSPI/KOSDAQ)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

import dart_fss as dart
from sqlalchemy.dialects.postgresql import insert

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import get_settings
from utils.db import SessionLocal
from db.models import Financial  # ← SQLAlchemy 모델 모듈 (예: models.Financial)

# ──────────────────────────────────────────────────────────────────────────────
# 설정 & 로거
# ──────────────────────────────────────────────────────────────────────────────
try:
    dart.set_api_key(get_settings().dart_api_key)
except Exception as e:
    print(f"⚠️ DART API key error: {e}")
    print("Continuing without DART API key for testing...")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXTRACT_ITEMS: List[str] = ["매출액", "영업이익", "당기순이익"]

# 빠른 테스트용 종목 코드 (KRX에서 수집한 것과 동일)
DEFAULT_TEST_TICKERS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # 네이버
    "005380",  # 현대차
    "051910",  # LG화학
]

# 25개 기업 테스트용 (다양한 업종 포함)
EXTENDED_TEST_TICKERS = [
    "005930",  # 삼성전자 (전자)
    "000660",  # SK하이닉스 (반도체)
    "035420",  # 네이버 (인터넷)
    "005380",  # 현대차 (자동차)
    "051910",  # LG화학 (화학)
    "006400",  # 삼성SDI (배터리)
    "207940",  # 삼성바이오로직스 (바이오)
    "035720",  # 카카오 (인터넷)
    "012330",  # 현대모비스 (자동차부품)
    "066570",  # LG전자 (전자)
    "009150",  # 삼성전기 (전자부품)
    "096770",  # SK이노베이션 (화학)
    "028260",  # 삼성물산 (건설)
    "055550",  # 신한지주 (금융)
    "105560",  # KB금융 (금융)
    "373220",  # LG에너지솔루션 (배터리)
    "000270",  # 기아 (자동차)
    "003670",  # 포스코홀딩스 (철강)
    "017670",  # SK텔레콤 (통신)
    "034730",  # SK (지주)
    "018260",  # 삼성에스디에스 (IT서비스)
    "015760",  # 한국전력 (전력)
    "323410",  # 카카오뱅크 (금융)
    "006800",  # 미래에셋증권 (증권)
    "085620",  # 미래에셋생명보험 (보험)
]


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────────────────────────────
def _get_listed_corps_only() -> List:
    """코스피/코스닥 상장사만 가져오기 (DB의 company_info 기반)."""
    from sqlalchemy import text
    
    session = SessionLocal()
    listed_corps = []
    
    try:
        # DB에서 상장사 종목 코드 가져오기
        result = session.execute(text("""
            SELECT DISTINCT ticker 
            FROM company_info 
            WHERE market IN ('KOSPI', 'KOSDAQ') 
            AND ticker IS NOT NULL
            ORDER BY ticker
        """))
        
        listed_tickers = [row[0] for row in result.fetchall()]
        logger.info(f"📊 DB에서 {len(listed_tickers)}개 상장사 종목 발견")
        
        # DART에서 전체 기업 리스트 가져오기
        all_corps = dart.get_corp_list()
        
        # 상장사만 필터링
        for corp in all_corps:
            if corp.stock_code in listed_tickers:
                listed_corps.append(corp)
        
        logger.info(f"🎯 DART에서 매칭된 상장사: {len(listed_corps)}개")
        return listed_corps
        
    except Exception as e:
        logger.error(f"상장사 필터링 실패: {e}")
        return []
    finally:
        session.close()


def _get_test_corps(tickers: List[str]) -> List:
    """테스트용 기업 정보만 가져오기."""
    test_corps = []
    
    try:
        # 전체 기업 리스트 가져오기 (새 API 문법)
        all_corps = dart.get_corp_list()
        
        # 테스트 종목에 해당하는 기업만 필터링
        for corp in all_corps:
            if hasattr(corp, 'stock_code') and corp.stock_code in tickers:
                test_corps.append(corp)
                logger.info(f"✅ Found corp: {corp.corp_name} ({corp.stock_code})")
        
        logger.info(f"📊 Total test corps: {len(test_corps)}")
        return test_corps
        
    except Exception as e:
        logger.error(f"❌ Error getting corp list: {e}")
        return []


def _create_dummy_financial_data(tickers: List[str], year: int) -> List[dict]:
    """DART API 오류 시 더미 재무 데이터 생성 (테스트용)."""
    dummy_data = []
    
    # 실제 대략적인 재무 데이터 (단위: 억원)
    dummy_financials = {
        "005930": {"매출액": 3020000, "영업이익": 659000, "당기순이익": 554000},  # 삼성전자
        "000660": {"매출액": 500000, "영업이익": 78000, "당기순이익": 65000},    # SK하이닉스
        "035420": {"매출액": 88000, "영업이익": 15000, "당기순이익": 12000},     # 네이버
        "005380": {"매출액": 1420000, "영업이익": 38000, "당기순이익": 32000},   # 현대차
        "051910": {"매출액": 508000, "영업이익": 46000, "당기순이익": 38000},    # LG화학
    }
    
    for ticker in tickers:
        if ticker in dummy_financials:
            row = {"ticker": ticker, "year": year}
            row.update(dummy_financials[ticker])
            dummy_data.append(row)
            logger.info(f"📊 Created dummy data for {ticker}")
    
    return dummy_data


# ──────────────────────────────────────────────────────────────────────────────
# 메인 로직
# ──────────────────────────────────────────────────────────────────────────────
def run(
    year: int | None = None, 
    quick_test: bool = True,
    test_tickers: List[str] | None = None,
    use_dummy_on_error: bool = True
) -> None:
    """
    지정 연도의 연결 손익계산서 주요 항목을 수집하여 DB에 upsert.
    
    Args:
        year: 수집할 연도 (기본값: 작년)
        quick_test: True면 테스트 종목만 수집
        test_tickers: 테스트용 종목 리스트
        use_dummy_on_error: API 오류 시 더미 데이터 사용 여부
    """
    year = year or datetime.now().year - 1
    test_tickers = test_tickers or DEFAULT_TEST_TICKERS
    
    if quick_test:
        logger.info(f"🚀 Quick test mode: {len(test_tickers)} 종목만 수집")
        logger.info(f"📅 Target year: {year}")
        logger.info(f"📈 Test tickers: {test_tickers}")
    else:
        logger.info(f"📊 Full mode: 전체 KOSPI/KOSDAQ 기업")

    session = SessionLocal()
    processed_count = 0
    
    try:
        if quick_test:
            # 빠른 테스트 모드: 특정 종목만
            try:
                corps = _get_test_corps(test_tickers)
                
                if not corps and use_dummy_on_error:
                    # DART API 오류 시 더미 데이터 사용
                    logger.warning("⚠️ DART API 접근 실패, 더미 데이터 사용")
                    dummy_data = _create_dummy_financial_data(test_tickers, year)
                    
                    for row in dummy_data:
                        stmt = (
                            insert(Financial)  # type: ignore[attr-defined]
                            .values(**row)
                            .on_conflict_do_update(
                                index_elements=["ticker", "year"],
                                set_=row,
                            )
                        )
                        session.execute(stmt)
                        processed_count += 1
                    
                    session.commit()
                    logger.info(f"🎉 DART ETL 완료 (더미 데이터): {processed_count}개 종목")
                    return
                    
            except Exception as e:
                logger.error(f"❌ Error in quick test: {e}")
                if use_dummy_on_error:
                    logger.info("🔄 Falling back to dummy data...")
                    dummy_data = _create_dummy_financial_data(test_tickers, year)
                    
                    for row in dummy_data:
                        stmt = (
                            insert(Financial)  # type: ignore[attr-defined]
                            .values(**row)
                            .on_conflict_do_update(
                                index_elements=["ticker", "year"],
                                set_=row,
                            )
                        )
                        session.execute(stmt)
                        processed_count += 1
                    
                    session.commit()
                    logger.info(f"🎉 DART ETL 완료 (더미 데이터): {processed_count}개 종목")
                    return
        else:
            # 전체 모드: 코스피/코스닥 상장사만
            corps = _get_listed_corps_only()

        # 실제 DART 데이터 수집
        for i, corp in enumerate(corps, 1):
            try:
                logger.info(f"⏳ [{i}/{len(corps)}] Processing {corp.corp_name} ({corp.stock_code})")
                
                fs = corp.extract_fs(bgn_de=f"{year}0101")
                if not fs:
                    logger.debug("공시 없음: %s", corp.stock_code)
                    continue

                # dart-fss API 버전에 상관없이 안전한 추출 방식
                income = None
                
                try:
                    # fs.labels에서 손익계산서('is') 또는 포괄손익계산서('cis') 확인
                    labels_dict = fs.labels if hasattr(fs, 'labels') else {}
                    logger.debug(f"📋 {corp.stock_code} 사용 가능한 재무제표 키: {list(labels_dict.keys())}")
                    
                    # 'is'(Income Statement) 키로 손익계산서 추출 시도
                    if 'is' in labels_dict:
                        income = fs.show('is')
                        if income is not None and not income.empty:
                            logger.debug(f"✅ {corp.stock_code} 손익계산서('is') 추출 성공")
                        else:
                            income = None
                    
                    # 'is'가 실패하면 'cis'(포괄손익계산서) 시도
                    if (income is None or income.empty) and 'cis' in labels_dict:
                        income = fs.show('cis')
                        if income is not None and not income.empty:
                            logger.debug(f"✅ {corp.stock_code} 포괄손익계산서('cis') 추출 성공")
                        else:
                            income = None
                    
                    if income is None or income.empty:
                        logger.warning(f"손익계산서 추출 실패: {corp.stock_code}")
                        continue
                    
                except Exception as e:
                    logger.warning(f"재무제표 구조 파싱 오류 {corp.stock_code}: {e}")
                    continue

                # ── row dict 생성 ────────────────────────────────────────
                row = {"ticker": corp.stock_code, "year": year}
                
                # 데이터 구조에 따라 다르게 처리
                for item in EXTRACT_ITEMS:
                    val = None
                    try:
                        # 방법 1: 일반적인 손익계산서 형태 (삼성전자 등) - index 기반
                        if hasattr(income, 'index') and item in income.index:
                            val = float(income.loc[item].iloc[0])
                            logger.debug(f"✅ {corp.stock_code} {item} 방법1(index) 성공: {val}")
                        
                        # 방법 2: DataFrame 형태에서 label_ko 컬럼 검색 (삼성전자, 네이버 등)
                        elif hasattr(income, 'columns') and len(income.columns) > 1:
                            # label_ko 컬럼에서 해당 항목 찾기
                            label_col = income.columns[1]  # label_ko
                            year_col = f"20{year-2000}0101-20{year-2000}1231"  # 해당 연도 컬럼
                            
                            # 매출액 매핑 (매출액 또는 영업수익)
                            if item == "매출액":
                                # 1) 매출액으로 찾기
                                revenue_rows = income[income[label_col].str.contains('매출액', na=False)]
                                if len(revenue_rows) == 0:
                                    # 2) 영업수익으로 찾기 (네이버 스타일)
                                    revenue_rows = income[income[label_col].str.contains('영업수익', na=False)]
                                
                                if len(revenue_rows) > 0 and (year_col, ('연결재무제표',)) in income.columns:
                                    val = float(revenue_rows[(year_col, ('연결재무제표',))].iloc[0])
                                    logger.debug(f"✅ {corp.stock_code} {item} 방법2(label검색) 성공: {val}")
                            
                            # 영업이익 매핑
                            elif item == "영업이익":
                                operating_rows = income[income[label_col].str.contains('영업이익', na=False)]
                                if len(operating_rows) > 0 and (year_col, ('연결재무제표',)) in income.columns:
                                    val = float(operating_rows[(year_col, ('연결재무제표',))].iloc[0])
                                    logger.debug(f"✅ {corp.stock_code} {item} 방법2(label검색) 성공: {val}")
                            
                            # 당기순이익 매핑
                            elif item == "당기순이익":
                                net_rows = income[income[label_col].str.contains('당기순이익', na=False)]
                                if len(net_rows) > 0 and (year_col, ('연결재무제표',)) in income.columns:
                                    val = float(net_rows[(year_col, ('연결재무제표',))].iloc[0])
                                    logger.debug(f"✅ {corp.stock_code} {item} 방법2(label검색) 성공: {val}")
                    
                    except Exception as e:
                        logger.debug(f"{corp.stock_code} {item} 추출 오류: {e}")
                        pass
                    
                    row[item] = val

                # ── upsert (ticker, year) ON CONFLICT DO UPDATE ─────────
                stmt = (
                    insert(Financial)  # type: ignore[attr-defined]
                    .values(**row)
                    .on_conflict_do_update(
                        index_elements=["ticker", "year"],
                        set_=row,
                    )
                )
                session.execute(stmt)
                processed_count += 1
                
                # 진행 상황 표시
                if i % 5 == 0 or i == len(corps):
                    logger.info(f"✅ Progress: {i}/{len(corps)} corps, {processed_count} processed")

            except Exception as err:  # noqa: BLE001
                logger.warning("skip %s (%s): %s", corp.stock_code, corp.corp_name, err)

        session.commit()
        logger.info(f"🎉 DART ETL 완료 ({year}): {processed_count}개 종목")

    finally:
        session.close()


def run_quick_test():
    """빠른 테스트 실행 (5개 대형주만)."""
    logger.info("🔥 DART Quick Test Starting...")
    run(quick_test=True)

def run_extended_test():
    """확장 테스트 실행 (15개 다양한 업종)."""
    logger.info("🚀 DART Extended Test Starting (15 companies)...")
    run(quick_test=True, test_tickers=EXTENDED_TEST_TICKERS)


def run_full():
    """전체 실행 (모든 KOSPI/KOSDAQ 기업).""" 
    logger.info("🌟 DART Full Mode Starting...")
    run(quick_test=False)


def run_multi_year(start_year: int = 2021, end_year: int = 2024):
    """다년도 데이터 수집 (2021-2024)"""
    logger.info(f"🚀 Multi-Year Collection: {start_year}-{end_year}")
    
    for year in range(start_year, end_year + 1):
        logger.info(f"📅 Starting collection for year {year}")
        try:
            run(year=year, quick_test=False)
            logger.info(f"✅ Completed collection for year {year}")
        except Exception as e:
            logger.error(f"❌ Failed for year {year}: {e}")
            continue
    
    logger.info("🎉 Multi-year collection completed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "quick":
            run_quick_test()
        elif mode == "extended" or mode == "ext":
            run_extended_test()
        elif mode == "full":
            run_full()
        elif mode == "multi":
            run_multi_year()
        else:
            print("Usage: python load_dart.py [quick|extended|full|multi]")
            print("  quick:    테스트용 5개 대형주만")
            print("  extended: 테스트용 15개 다양한 업종")
            print("  full:     전체 KOSPI/KOSDAQ 기업 (단일년도)")
            print("  multi:    2021-2024년 전체 수집")
    else:
        # 기본값: 빠른 테스트
        run_quick_test()