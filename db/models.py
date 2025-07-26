"""SQLAlchemy database models for portfolio system."""
from __future__ import annotations

from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    Float, 
    Date, 
    BigInteger, 
    Index,
    UniqueConstraint,
    DateTime,
    Text
)
from sqlalchemy.sql import func
from utils.db import Base


class Price(Base):
    """주식 가격 데이터 테이블 (KRX + yfinance)."""
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, comment="종목 코드 (KRX)")
    date = Column(Date, nullable=False, comment="거래일")
    open = Column(Float, comment="시가")
    high = Column(Float, comment="고가") 
    low = Column(Float, comment="저가")
    close = Column(Float, comment="종가")
    volume = Column(BigInteger, comment="거래량")
    created_at = Column(DateTime, default=func.now(), comment="데이터 생성시간")
    
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uq_price_ticker_date'),
        Index('ix_price_ticker', 'ticker'),
        Index('ix_price_date', 'date'),
        Index('ix_price_ticker_date', 'ticker', 'date'),
    )
    
    def __repr__(self):
        return f"<Price(ticker={self.ticker}, date={self.date}, close={self.close})>"


class PriceYf(Base):
    """yfinance 백업 가격 데이터 테이블."""
    __tablename__ = "prices_yf"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, comment="종목 코드 (KRX)")
    date = Column(Date, nullable=False, comment="거래일")
    open = Column(Float, comment="시가")
    high = Column(Float, comment="고가")
    low = Column(Float, comment="저가") 
    close = Column(Float, comment="종가")
    volume = Column(BigInteger, comment="거래량")
    created_at = Column(DateTime, default=func.now(), comment="데이터 생성시간")
    
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uq_price_yf_ticker_date'),
        Index('ix_price_yf_ticker', 'ticker'),
        Index('ix_price_yf_date', 'date'),
    )


class PriceMerged(Base):
    """병합된 최종 가격 데이터 테이블 (KRX + yfinance 백필)."""
    __tablename__ = "prices_merged"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False, comment="종목 코드 (KRX)")
    date = Column(Date, nullable=False, comment="거래일")
    open = Column(Float, comment="시가")
    high = Column(Float, comment="고가")
    low = Column(Float, comment="저가")
    close = Column(Float, comment="종가") 
    volume = Column(BigInteger, comment="거래량")
    source = Column(String(10), comment="데이터 소스 (krx/yf/merged)")
    created_at = Column(DateTime, default=func.now(), comment="데이터 생성시간")
    
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uq_price_merged_ticker_date'),
        Index('ix_price_merged_ticker', 'ticker'),
        Index('ix_price_merged_date', 'date'),
        Index('ix_price_merged_ticker_date', 'ticker', 'date'),
    )


class Financial(Base):
    """DART 재무제표 데이터 테이블."""
    __tablename__ = "financials"
    
    ticker = Column(String(20), primary_key=True, comment="종목 코드 (KRX)")
    year = Column(Integer, primary_key=True, comment="회계연도")
    매출액 = Column(Float, comment="매출액 (단위: 원)")
    영업이익 = Column(Float, comment="영업이익 (단위: 원)")
    당기순이익 = Column(Float, comment="당기순이익 (단위: 원)")
    created_at = Column(DateTime, default=func.now(), comment="데이터 생성시간")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="데이터 수정시간")
    
    __table_args__ = (
        Index('ix_financial_ticker', 'ticker'),
        Index('ix_financial_year', 'year'),
    )
    
    def __repr__(self):
        return f"<Financial(ticker={self.ticker}, year={self.year}, 매출액={self.매출액})>"


class QualityMetric(Base):
    """데이터 품질 지표 테이블."""
    __tablename__ = "quality_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, comment="대상 테이블명")
    metric_name = Column(String(50), nullable=False, comment="지표명 (coverage, completeness 등)")
    metric_value = Column(Float, nullable=False, comment="지표 값")
    threshold = Column(Float, comment="임계값")
    status = Column(String(20), comment="상태 (PASS/FAIL/WARNING)")
    measured_at = Column(DateTime, default=func.now(), comment="측정 시간")
    details = Column(Text, comment="세부 정보 (JSON 등)")
    
    __table_args__ = (
        Index('ix_quality_table_metric', 'table_name', 'metric_name'),
        Index('ix_quality_measured_at', 'measured_at'),
    )
    
    def __repr__(self):
        return f"<QualityMetric(table={self.table_name}, metric={self.metric_name}, value={self.metric_value})>"


class CompanyInfo(Base):
    """기업 기본 정보 테이블 (선택사항)."""
    __tablename__ = "company_info"
    
    ticker = Column(String(20), primary_key=True, comment="종목 코드 (KRX)")
    corp_name = Column(String(100), comment="기업명")
    corp_code = Column(String(10), comment="DART 기업 고유번호")
    market = Column(String(10), comment="시장 구분 (KOSPI/KOSDAQ/KONEX)")
    sector = Column(String(50), comment="업종")
    industry = Column(String(100), comment="세부 업종")
    listing_date = Column(Date, comment="상장일")
    created_at = Column(DateTime, default=func.now(), comment="데이터 생성시간")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="데이터 수정시간")
    
    __table_args__ = (
        Index('ix_company_name', 'corp_name'),
        Index('ix_company_market', 'market'),
        Index('ix_company_sector', 'sector'),
    )
    
    def __repr__(self):
        return f"<CompanyInfo(ticker={self.ticker}, name={self.corp_name}, market={self.market})>"


# 모든 모델을 외부에서 임포트할 수 있도록 명시적으로 선언
__all__ = [
    "Price",
    "PriceYf", 
    "PriceMerged",
    "Financial",
    "QualityMetric",
    "CompanyInfo"
]