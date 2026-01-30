"""Stock data fetcher using yfinance (free, no API key required)."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import yfinance as yf
from diskcache import Cache

from .config import get_settings
from .models import RiskLevel, StockAnalysis, StockHolding

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """Fetches stock data from Yahoo Finance with caching."""

    def __init__(self):
        self.settings = get_settings()
        if self.settings.cache_enabled:
            self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache = Cache(str(self.settings.cache_dir / "stock_data"))
        else:
            self._cache = None

    def _get_cached(self, key: str) -> dict | None:
        """Get value from cache if available."""
        if self._cache is None:
            return None
        return self._cache.get(key)

    def _set_cached(self, key: str, value: dict) -> None:
        """Set value in cache."""
        if self._cache is not None:
            self._cache.set(key, value, expire=self.settings.cache_ttl_seconds)

    def fetch_stock_info(self, symbol: str) -> dict:
        """Fetch current stock information."""
        cache_key = f"info_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for {symbol} info")
            return cached

        logger.info(f"Fetching stock info for {symbol}")
        ticker = yf.Ticker(symbol)
        info = ticker.info

        self._set_cached(cache_key, info)
        return info

    def fetch_history(self, symbol: str, period_days: int | None = None) -> pd.DataFrame:
        """Fetch historical price data."""
        period_days = period_days or self.settings.analysis_period_days
        cache_key = f"history_{symbol}_{period_days}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for {symbol} history")
            return pd.DataFrame(cached)

        logger.info(f"Fetching {period_days}-day history for {symbol}")
        ticker = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)

        history = ticker.history(start=start_date, end=end_date)

        self._set_cached(cache_key, history.to_dict())
        return history

    def enrich_holding(self, holding: StockHolding) -> StockHolding:
        """Enrich a stock holding with current market data."""
        try:
            info = self.fetch_stock_info(holding.symbol)

            # Update holding with fetched data
            holding.current_price = Decimal(str(info.get("currentPrice", 0) or info.get("regularMarketPrice", 0)))
            holding.company_name = info.get("longName") or info.get("shortName")
            holding.sector = info.get("sector")
            holding.industry = info.get("industry")
            holding.market_cap = Decimal(str(info.get("marketCap", 0))) if info.get("marketCap") else None
            holding.pe_ratio = info.get("trailingPE")
            holding.dividend_yield = info.get("dividendYield")
            holding.fifty_two_week_high = (
                Decimal(str(info.get("fiftyTwoWeekHigh", 0))) if info.get("fiftyTwoWeekHigh") else None
            )
            holding.fifty_two_week_low = (
                Decimal(str(info.get("fiftyTwoWeekLow", 0))) if info.get("fiftyTwoWeekLow") else None
            )

        except Exception as e:
            logger.error(f"Error fetching data for {holding.symbol}: {e}")

        return holding

    def analyze_stock(self, symbol: str) -> StockAnalysis:
        """Generate technical analysis for a stock."""
        analysis = StockAnalysis(symbol=symbol)

        try:
            # Fetch historical data
            history = self.fetch_history(symbol, period_days=200)  # Need 200 days for 200-MA

            if history.empty:
                logger.warning(f"No historical data available for {symbol}")
                return analysis

            close_prices = history["Close"]

            # Price changes
            if len(close_prices) >= 2:
                analysis.price_change_1d = float(
                    (close_prices.iloc[-1] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100
                )

            if len(close_prices) >= 7:
                analysis.price_change_7d = float(
                    (close_prices.iloc[-1] - close_prices.iloc[-7]) / close_prices.iloc[-7] * 100
                )

            if len(close_prices) >= 30:
                analysis.price_change_30d = float(
                    (close_prices.iloc[-1] - close_prices.iloc[-30]) / close_prices.iloc[-30] * 100
                )
                # 30-day volatility (annualized)
                returns = close_prices.pct_change().dropna()
                analysis.volatility_30d = float(returns.tail(30).std() * (252**0.5) * 100)

            # RSI calculation (14-day)
            if len(close_prices) >= 15:
                analysis.rsi_14 = self._calculate_rsi(close_prices, period=14)

            # Moving averages
            current_price = close_prices.iloc[-1]
            if len(close_prices) >= 50:
                ma_50 = close_prices.tail(50).mean()
                analysis.above_50_ma = current_price > ma_50

            if len(close_prices) >= 200:
                ma_200 = close_prices.tail(200).mean()
                analysis.above_200_ma = current_price > ma_200

            # Risk assessment
            analysis.risk_level, analysis.risk_factors = self._assess_risk(analysis)

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")

        return analysis

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    def _assess_risk(self, analysis: StockAnalysis) -> tuple[RiskLevel, list[str]]:
        """Assess risk level based on technical indicators."""
        risk_factors = []
        risk_score = 0

        # Volatility risk
        if analysis.volatility_30d:
            if analysis.volatility_30d > 50:
                risk_factors.append(f"High volatility ({analysis.volatility_30d:.1f}%)")
                risk_score += 2
            elif analysis.volatility_30d > 30:
                risk_factors.append(f"Moderate volatility ({analysis.volatility_30d:.1f}%)")
                risk_score += 1

        # RSI extremes
        if analysis.rsi_14:
            if analysis.rsi_14 > 70:
                risk_factors.append(f"Overbought (RSI: {analysis.rsi_14:.1f})")
                risk_score += 1
            elif analysis.rsi_14 < 30:
                risk_factors.append(f"Oversold (RSI: {analysis.rsi_14:.1f})")
                risk_score += 1

        # Trend risk
        if analysis.above_200_ma is False:
            risk_factors.append("Below 200-day moving average")
            risk_score += 1

        # Price decline risk
        if analysis.price_change_30d and analysis.price_change_30d < -10:
            risk_factors.append(f"Significant 30-day decline ({analysis.price_change_30d:.1f}%)")
            risk_score += 1

        # Determine risk level
        if risk_score >= 4:
            return RiskLevel.VERY_HIGH, risk_factors
        elif risk_score >= 3:
            return RiskLevel.HIGH, risk_factors
        elif risk_score >= 2:
            return RiskLevel.MEDIUM, risk_factors
        else:
            return RiskLevel.LOW, risk_factors


# Singleton instance
_fetcher: StockDataFetcher | None = None


def get_stock_fetcher() -> StockDataFetcher:
    """Get singleton stock data fetcher instance."""
    global _fetcher
    if _fetcher is None:
        _fetcher = StockDataFetcher()
    return _fetcher
