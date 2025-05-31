"""
Modelos de datos para la base de datos SQLite.
Define las tablas y sus relaciones para almacenar datos financieros.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from .connection import Base


class CryptoCurrency(Base):
    """Modelo para almacenar información básica de criptomonedas."""
    __tablename__ = "cryptocurrencies"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relación con los precios
    prices = relationship("CryptoPrice", back_populates="cryptocurrency", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CryptoCurrency(symbol='{self.symbol}', name='{self.name}')>"


class CryptoPrice(Base):
    """Modelo para almacenar precios históricos de criptomonedas."""
    __tablename__ = "crypto_prices"
    
    id = Column(Integer, primary_key=True)
    cryptocurrency_id = Column(Integer, ForeignKey("cryptocurrencies.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    price_usd = Column(Float, nullable=False)
    market_cap_usd = Column(Float)
    volume_24h_usd = Column(Float)
    percent_change_24h = Column(Float)
    
    # Campos adicionales para análisis financiero más completo
    percent_change_7d = Column(Float)
    percent_change_30d = Column(Float)
    circulating_supply = Column(Float)
    total_supply = Column(Float)
    max_supply = Column(Float)
    ath_price = Column(Float)  # All-Time High
    ath_date = Column(DateTime)
    atl_price = Column(Float)  # All-Time Low
    atl_date = Column(DateTime)
    high_24h = Column(Float)
    low_24h = Column(Float)
    market_cap_rank = Column(Integer)
    fully_diluted_valuation = Column(Float)
    
    # Relación con la criptomoneda
    cryptocurrency = relationship("CryptoCurrency", back_populates="prices")
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index("ix_crypto_prices_cryptocurrency_id_timestamp", "cryptocurrency_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<CryptoPrice(symbol='{self.cryptocurrency.symbol}', timestamp='{self.timestamp}', price_usd={self.price_usd})>"


class Stock(Base):
    """Modelo para almacenar información básica de acciones y ETFs."""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'stock' o 'etf'
    exchange = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relación con los precios
    prices = relationship("StockPrice", back_populates="stock", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Stock(symbol='{self.symbol}', name='{self.name}', type='{self.type}')>"


class StockPrice(Base):
    """Modelo para almacenar precios históricos de acciones y ETFs."""
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open_price = Column(Float)
    high_price = Column(Float)
    low_price = Column(Float)
    close_price = Column(Float, nullable=False)
    volume = Column(Float)
    adjusted_close = Column(Float)
    
    # Relación con la acción/ETF
    stock = relationship("Stock", back_populates="prices")
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index("ix_stock_prices_stock_id_timestamp", "stock_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<StockPrice(symbol='{self.stock.symbol}', timestamp='{self.timestamp}', close_price={self.close_price})>"


class MacroIndicator(Base):
    """Modelo para almacenar indicadores macroeconómicos."""
    __tablename__ = "macro_indicators"
    
    id = Column(Integer, primary_key=True)
    indicator_name = Column(String, nullable=False)
    country = Column(String, nullable=False)
    region = Column(String)
    frequency = Column(String)  # 'daily', 'monthly', 'quarterly', 'yearly'
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relación con los valores
    values = relationship("MacroValue", back_populates="indicator", cascade="all, delete-orphan")
    
    # Índice compuesto para indicador y país
    __table_args__ = (
        Index("ix_macro_indicators_name_country", "indicator_name", "country", unique=True),
    )
    
    def __repr__(self):
        return f"<MacroIndicator(name='{self.indicator_name}', country='{self.country}')>"


class MacroValue(Base):
    """Modelo para almacenar valores históricos de indicadores macroeconómicos."""
    __tablename__ = "macro_values"
    
    id = Column(Integer, primary_key=True)
    indicator_id = Column(Integer, ForeignKey("macro_indicators.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    
    # Relación con el indicador
    indicator = relationship("MacroIndicator", back_populates="values")
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index("ix_macro_values_indicator_id_timestamp", "indicator_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<MacroValue(indicator='{self.indicator.indicator_name}', timestamp='{self.timestamp}', value={self.value})>"


class FixedIncomeInstrument(Base):
    """Modelo para almacenar instrumentos de renta fija."""
    __tablename__ = "fixed_income_instruments"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    instrument_type = Column(String, nullable=False)  # 'bond', 'certificate', etc.
    issuer = Column(String, nullable=False)
    country = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    maturity = Column(String)  # '1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Relación con los rendimientos
    yields = relationship("FixedIncomeYield", back_populates="instrument", cascade="all, delete-orphan")
    
    # Índice compuesto
    __table_args__ = (
        Index("ix_fixed_income_name_type_issuer_maturity", "name", "instrument_type", "issuer", "maturity", unique=True),
    )
    
    def __repr__(self):
        return f"<FixedIncomeInstrument(name='{self.name}', type='{self.instrument_type}', maturity='{self.maturity}')>"


class FixedIncomeYield(Base):
    """Modelo para almacenar rendimientos históricos de instrumentos de renta fija."""
    __tablename__ = "fixed_income_yields"
    
    id = Column(Integer, primary_key=True)
    instrument_id = Column(Integer, ForeignKey("fixed_income_instruments.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    yield_value = Column(Float, nullable=False)
    price = Column(Float)
    
    # Relación con el instrumento
    instrument = relationship("FixedIncomeInstrument", back_populates="yields")
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index("ix_fixed_income_yields_instrument_id_timestamp", "instrument_id", "timestamp"),
    )
    
    def __repr__(self):
        return f"<FixedIncomeYield(instrument='{self.instrument.name}', timestamp='{self.timestamp}', yield={self.yield_value})>"


class OHLCV(Base):
    """Modelo para almacenar datos de velas japonesas (OHLCV) de criptomonedas."""
    __tablename__ = "ohlcv"
    
    id = Column(Integer, primary_key=True)
    cryptocurrency_id = Column(Integer, ForeignKey("cryptocurrencies.id"), nullable=False)
    symbol = Column(String, nullable=False)  # Par de trading (ej. BTC/USDT)
    timeframe = Column(String, nullable=False)  # Intervalo de tiempo (ej. 1h, 4h, 1d)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Relación con la criptomoneda
    cryptocurrency = relationship("CryptoCurrency")
    
    # Índices para consultas eficientes
    __table_args__ = (
        Index("ix_ohlcv_symbol_timeframe_timestamp", "symbol", "timeframe", "timestamp", unique=True),
        Index("ix_ohlcv_cryptocurrency_id", "cryptocurrency_id"),
    )
    
    def __repr__(self):
        return f"<OHLCV(symbol='{self.symbol}', timeframe='{self.timeframe}', timestamp='{self.timestamp}')>"
