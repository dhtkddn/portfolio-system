#!/usr/bin/env python3
"""
간단한 DART API 재무데이터 수집기
전체 KOSPI/KOSDAQ 종목의 기본 재무 정보만 수집
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import asyncio
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text

from utils.db import SessionLocal
from db.models import Financial

# 환경변수에서 DART API 키 가져오기
from dotenv import load_dotenv
load_dotenv()

DART_API_KEY = os.getenv('DART_API_KEY')
DART_BASE_URL = "https://opendart.fss.or.kr/api"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleDartCollector:
    def __init__(self):
        self.session = SessionLocal()
        self.api_key = DART_API_KEY
        
        if not self.api_key:
            logger.error("DART_API_KEY가 설정되지 않았습니다.")
            raise ValueError("DART API 키 필요")
    
    def get_corp_list(self) -> List[Dict]:
        """DART API로 전체 법인 목록 조회"""
        url = f"{DART_BASE_URL}/corpCode.xml"
        params = {
            'crtfc_key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            # XML 파싱 대신 간단하게 처리
            content = response.text
            logger.info(f"법인 목록 XML 크기: {len(content)} bytes")
            
            # 실제로는 XML 파싱이 필요하지만, 여기서는 기존 DB의 company_info 사용
            return []
            
        except Exception as e:
            logger.error(f"법인 목록 조회 실패: {e}")
            return []
    
    def get_company_financials(self, corp_code: str, bsns_year: str) -> Optional[Dict]:
        """특정 기업의 재무제표 조회 (간소화)"""
        url = f"{DART_BASE_URL}/fnlttSinglAcntAll.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': '11011',  # 사업보고서
            'fs_div': 'CFS'  # 연결재무제표
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != '000':
                logger.debug(f"API 응답 오류: {data.get('message', 'Unknown error')}")
                return None
            
            # 재무제표 데이터 파싱
            financials = {}
            for item in data.get('list', []):
                account_nm = item.get('account_nm', '')
                thstrm_amount = item.get('thstrm_amount', '0')
                
                # 주요 재무 지표만 추출
                if '매출액' in account_nm and '영업' not in account_nm:
                    financials['매출액'] = self._parse_amount(thstrm_amount)
                elif '영업이익' in account_nm:
                    financials['영업이익'] = self._parse_amount(thstrm_amount)
                elif '당기순이익' in account_nm and '포괄' not in account_nm:
                    financials['당기순이익'] = self._parse_amount(thstrm_amount)
            
            return financials if financials else None
            
        except Exception as e:
            logger.debug(f"재무제표 조회 실패 ({corp_code}): {e}")
            return None
    
    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """금액 문자열을 숫자로 변환"""
        try:
            # 쉼표 제거하고 숫자만 추출
            cleaned = amount_str.replace(',', '').replace('-', '0')
            if cleaned.isdigit():
                return float(cleaned)
            return None
        except:
            return None
    
    def get_corp_code_mapping(self) -> Dict[str, str]:
        """DART API로 종목코드와 corp_code 매핑 테이블 생성"""
        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {'crtfc_key': self.api_key}
        
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            
            # XML 파싱
            import xml.etree.ElementTree as ET
            from io import BytesIO
            import zipfile
            
            # ZIP 파일 압축 해제
            with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                xml_content = zip_file.read('CORPCODE.xml')
            
            root = ET.fromstring(xml_content)
            
            mapping = {}
            count = 0
            
            for corp in root.findall('list'):
                corp_code = corp.find('corp_code')
                stock_code = corp.find('stock_code')
                corp_name = corp.find('corp_name')
                
                if corp_code is not None and stock_code is not None and stock_code.text:
                    mapping[stock_code.text] = corp_code.text
                    count += 1
                    
                    if count <= 5:  # 처음 5개만 로그
                        logger.info(f"매핑: {stock_code.text} -> {corp_code.text} ({corp_name.text if corp_name is not None else 'N/A'})")
            
            logger.info(f"📋 DART 매핑 테이블 생성 완료: {len(mapping)}개 종목")
            return mapping
            
        except Exception as e:
            logger.error(f"DART 매핑 테이블 생성 실패: {e}")
            return {}

    async def collect_all_financials(self, limit: int = 100):
        """DB의 모든 기업에 대해 재무데이터 수집"""
        
        # DART corp_code 매핑 테이블 생성
        logger.info("🔍 DART corp_code 매핑 테이블 생성 중...")
        corp_mapping = self.get_corp_code_mapping()
        
        if not corp_mapping:
            logger.error("❌ DART 매핑 테이블 생성 실패")
            return
        
        # DB에서 기업 목록 조회
        companies = self.session.execute(text("""
            SELECT ticker, corp_name 
            FROM company_info 
            WHERE ticker IS NOT NULL 
            ORDER BY market, ticker
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        logger.info(f"📊 수집 대상: {len(companies)}개 기업")
        
        success_count = 0
        total_records = 0
        years = [2021, 2022, 2023, 2024]  # 4개년 데이터 수집
        
        for i, (ticker, corp_name) in enumerate(companies, 1):
            logger.info(f"⏳ [{i}/{len(companies)}] {corp_name} ({ticker}) 처리 중...")
            
            # 매핑 테이블에서 corp_code 찾기
            corp_code = corp_mapping.get(ticker)
            
            if not corp_code:
                logger.debug(f"⚠️ {ticker}에 대한 corp_code를 찾을 수 없습니다")
                continue
            
            # 4개년 데이터 수집
            company_success = 0
            for year in years:
                financials = self.get_company_financials(corp_code, str(year))
                
                if financials:
                    # DB에 저장
                    row = {
                        "ticker": ticker,
                        "year": year,
                        **financials
                    }
                    
                    stmt = insert(Financial).values(**row).on_conflict_do_update(
                        index_elements=["ticker", "year"],
                        set_=row
                    )
                    
                    self.session.execute(stmt)
                    company_success += 1
                    total_records += 1
                
                # API 호출 제한을 위한 대기
                await asyncio.sleep(0.05)  # 연도별 대기 시간 단축
            
            if company_success > 0:
                success_count += 1
                latest_financials = self.get_company_financials(corp_code, "2024")
                revenue = latest_financials.get('매출액', 0) if latest_financials else 0
                logger.info(f"✅ {corp_name}: {company_success}개년 데이터, 최근 매출액 {revenue:,}")
            
            # 5개씩 처리할 때마다 커밋
            if i % 5 == 0:
                self.session.commit()
                logger.info(f"💾 중간 저장 완료: {i}/{len(companies)}, 총 {total_records}개 레코드")
        
        # 최종 커밋
        self.session.commit()
        logger.info(f"🎉 재무데이터 수집 완료: {success_count}/{len(companies)}개 기업, 총 {total_records}개 레코드")
    
    def close(self):
        if self.session:
            self.session.close()

async def main():
    """메인 실행 함수"""
    collector = SimpleDartCollector()
    
    try:
        # 처음에는 100개만 테스트
        limit = 100 if len(sys.argv) < 2 else int(sys.argv[1])
        
        logger.info(f"🚀 DART 재무데이터 수집 시작 (최대 {limit}개)")
        await collector.collect_all_financials(limit=limit)
        logger.info("✅ 수집 완료!")
        
    except Exception as e:
        logger.error(f"❌ 수집 실패: {e}")
    finally:
        collector.close()

if __name__ == "__main__":
    # 사용법: python load_dart_simple.py [limit]
    # 예: python load_dart_simple.py 500  (500개 기업)
    asyncio.run(main())