"""Tests for stock fetcher module."""

import pytest
from decimal import Decimal

from finops_analyzer.models import StockHolding
from finops_analyzer.stock_fetcher import StockDataFetcher


class TestStockDataFetcher:
    """Test cases for StockDataFetcher."""
    
    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance."""
        return StockDataFetcher()
    
    def test_fetch_stock_info(self, fetcher):
        """Test fetching stock info for a valid symbol."""
        info = fetcher.fetch_stock_info("AAPL")
        
        assert info is not None
        assert "currentPrice" in info or "regularMarketPrice" in info
    
    def test_fetch_history(self, fetcher):
        """Test fetching historical data."""
        history = fetcher.fetch_history("AAPL", period_days=30)
        
        assert not history.empty
        assert "Close" in history.columns
        assert len(history) > 0
    
    def test_enrich_holding(self, fetcher):
        """Test enriching a stock holding with market data."""
        holding = StockHolding(
            symbol="MSFT",
            shares=Decimal("10"),
            cost_basis=Decimal("300")
        )
        
        enriched = fetcher.enrich_holding(holding)
        
        assert enriched.current_price is not None
        assert enriched.current_price > 0
        assert enriched.company_name is not None
    
    def test_analyze_stock(self, fetcher):
        """Test technical analysis for a stock."""
        analysis = fetcher.analyze_stock("GOOGL")
        
        assert analysis.symbol == "GOOGL"
        assert analysis.price_change_1d is not None
        assert analysis.risk_level is not None


class TestStockHolding:
    """Test cases for StockHolding model."""
    
    def test_current_value_calculation(self):
        """Test current value is calculated correctly."""
        holding = StockHolding(
            symbol="TEST",
            shares=Decimal("10"),
            cost_basis=Decimal("100"),
            current_price=Decimal("150")
        )
        
        assert holding.current_value == Decimal("1500")
    
    def test_gain_loss_calculation(self):
        """Test gain/loss is calculated correctly."""
        holding = StockHolding(
            symbol="TEST",
            shares=Decimal("10"),
            cost_basis=Decimal("100"),
            current_price=Decimal("150")
        )
        
        assert holding.total_gain_loss == Decimal("500")
        assert holding.gain_loss_percent == 50.0
