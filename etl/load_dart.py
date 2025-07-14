"""Open DART 재무제표 ETL 스크립트 (KOSPI/KOSDAQ)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

import dart_fss as dart
from sqlalchemy.dialects.postgresql import insert

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


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────────────────────────────────────
def _get_test_corps(tickers: List[str]) -> List:
    """테스트용 기업 정보만 가져오기."""
    test_corps = []
    
    try:
        # 전체 기업 리스트 가져오기
        all_corps = dart.get_corp_list(market="KOSPI") + dart.get_corp_list(market="KOSDAQ")
        
        # 테스트 종목에 해당하는 기업만 필터링
        for corp in all_corps:
            if corp.stock_code in tickers:
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
                            insert(models.Financial)  # type: ignore[attr-defined]
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
            # 전체 모드: 모든 기업
            corps = dart.get_corp_list(market="KOSPI") + dart.get_corp_list(market="KOSDAQ")

        # 실제 DART 데이터 수집
        for i, corp in enumerate(corps, 1):
            try:
                logger.info(f"⏳ [{i}/{len(corps)}] Processing {corp.corp_name} ({corp.stock_code})")
                
                fs = corp.extract_fs(bgn_de=f"{year}0101")
                if not fs:
                    logger.debug("공시 없음: %s", corp.stock_code)
                    continue

                income = fs["CFS"].get("손익계산서")
                if income is None:
                    logger.debug("손익계산서 없음: %s", corp.stock_code)
                    continue

                # ── row dict 생성 ────────────────────────────────────────
                row = {"ticker": corp.stock_code, "year": year}
                for item in EXTRACT_ITEMS:
                    val = None
                    if item in income.index:
                        try:
                            val = float(income.loc[item].iloc[0])
                        except Exception:
                            pass
                    row[item] = val

                # ── upsert (ticker, year) ON CONFLICT DO UPDATE ─────────
                stmt = (
                    insert(models.Financial)  # type: ignore[attr-defined]
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


def run_full():
    """전체 실행 (모든 KOSPI/KOSDAQ 기업).""" 
    logger.info("🌟 DART Full Mode Starting...")
    run(quick_test=False)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "quick":
            run_quick_test()
        elif mode == "full":
            run_full()
        else:
            print("Usage: python load_dart.py [quick|full]")
            print("  quick: 테스트용 5개 대형주만")
            print("  full:  전체 KOSPI/KOSDAQ 기업")
    else:
        # 기본값: 빠른 테스트
        run_quick_test()