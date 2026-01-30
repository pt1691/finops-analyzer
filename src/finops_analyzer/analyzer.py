"""Core analysis engine that orchestrates the analysis pipeline."""

import csv
import logging
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from .config import get_settings
from .dashboard import create_progress_bar
from .models import Portfolio, PortfolioAnalysis, StockHolding
from .sentiment import get_ai_analyzer, get_news_fetcher
from .stock_fetcher import get_stock_fetcher

logger = logging.getLogger(__name__)


class PortfolioAnalyzer:
    """Main analysis engine for portfolios."""

    def __init__(self):
        self.settings = get_settings()
        self.stock_fetcher = get_stock_fetcher()
        self.news_fetcher = get_news_fetcher()
        self.ai_analyzer = get_ai_analyzer()

    def load_portfolio_from_csv(self, csv_path: Path) -> Portfolio:
        """Load portfolio from a CSV file.

        Expected CSV format:
        symbol,shares,cost_basis (optional)
        AAPL,100,150.00
        GOOGL,50,
        """
        holdings = []

        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = row.get("symbol", "").strip().upper()
                if not symbol:
                    continue

                shares = Decimal(row.get("shares", "0").strip() or "0")
                cost_basis_str = row.get("cost_basis", "").strip()
                cost_basis = Decimal(cost_basis_str) if cost_basis_str else None

                holdings.append(StockHolding(symbol=symbol, shares=shares, cost_basis=cost_basis))

        return Portfolio(name=csv_path.stem, holdings=holdings)

    def load_portfolio_from_symbols(
        self,
        symbols: list[str],
        shares: list[float] | None = None,
        cost_basis: list[float] | None = None,
    ) -> Portfolio:
        """Create portfolio from list of symbols."""
        holdings = []

        for i, symbol in enumerate(symbols):
            share_count = Decimal(str(shares[i])) if shares and i < len(shares) else Decimal("1")
            basis = Decimal(str(cost_basis[i])) if cost_basis and i < len(cost_basis) else None

            holdings.append(StockHolding(symbol=symbol.upper(), shares=share_count, cost_basis=basis))

        return Portfolio(holdings=holdings)

    def analyze_portfolio(
        self,
        portfolio: Portfolio,
        include_news: bool = True,
        include_ai_insights: bool = True,
        progress_callback: Callable | None = None,
    ) -> PortfolioAnalysis:
        """Run complete portfolio analysis."""

        analysis = PortfolioAnalysis(portfolio=portfolio)
        total_steps = len(portfolio.holdings) * (3 if include_news else 2) + (1 if include_ai_insights else 0)
        current_step = 0

        def update_progress(description: str):
            nonlocal current_step
            current_step += 1
            if progress_callback:
                progress_callback(current_step, total_steps, description)

        # Step 1: Enrich holdings with current data
        for holding in portfolio.holdings:
            update_progress(f"Fetching data for {holding.symbol}")
            self.stock_fetcher.enrich_holding(holding)

        # Step 2: Technical analysis for each stock
        for holding in portfolio.holdings:
            update_progress(f"Analyzing {holding.symbol}")
            stock_analysis = self.stock_fetcher.analyze_stock(holding.symbol)
            analysis.stock_analyses[holding.symbol] = stock_analysis

        # Step 3: News and sentiment analysis
        if include_news:
            for holding in portfolio.holdings:
                update_progress(f"Analyzing news for {holding.symbol}")
                stock_analysis = analysis.stock_analyses[holding.symbol]

                # Fetch news
                articles = self.news_fetcher.fetch_news(holding.symbol)

                # AI sentiment analysis
                if articles and self.settings.get_active_api_key():
                    articles, overall_sentiment, summary = self.ai_analyzer.analyze_sentiment(holding.symbol, articles)
                    stock_analysis.news_articles = articles
                    stock_analysis.overall_sentiment = overall_sentiment
                    stock_analysis.sentiment_summary = summary
                else:
                    stock_analysis.news_articles = articles

        # Step 4: Portfolio-level AI insights
        if include_ai_insights and self.settings.get_active_api_key():
            update_progress("Generating AI insights")

            # Build portfolio summary
            portfolio_summary = f"""
Portfolio: {portfolio.name}
Total Value: ${portfolio.total_value:,.2f}
Total Gain/Loss: ${portfolio.total_gain_loss:,.2f} ({portfolio.total_gain_loss_percent:.1f}%)
Holdings: {len(portfolio.holdings)} stocks
Sector Allocation: {portfolio.get_sector_allocation()}
            """

            insights = self.ai_analyzer.generate_portfolio_insights(portfolio_summary, analysis.stock_analyses)

            # Apply insights to analysis
            if insights:
                analysis.portfolio_summary = insights.get("portfolio_summary")
                analysis.diversification_score = insights.get("diversification_score")
                analysis.risk_score = insights.get("risk_score")
                analysis.overall_sentiment = insights.get("overall_sentiment")
                analysis.strengths = insights.get("strengths", [])
                analysis.weaknesses = insights.get("weaknesses", [])
                analysis.recommendations = insights.get("recommendations", [])
                analysis.market_outlook = insights.get("market_outlook")

        return analysis

    def analyze_with_progress(
        self, portfolio: Portfolio, include_news: bool = True, include_ai_insights: bool = True
    ) -> PortfolioAnalysis:
        """Run analysis with a rich progress bar."""

        with create_progress_bar() as progress:
            task = progress.add_task("Analyzing portfolio...", total=100)

            def progress_callback(current: int, total: int, description: str):
                pct = (current / total) * 100 if total > 0 else 0
                progress.update(task, completed=pct, description=description)

            result = self.analyze_portfolio(
                portfolio,
                include_news=include_news,
                include_ai_insights=include_ai_insights,
                progress_callback=progress_callback,
            )

            progress.update(task, completed=100, description="Analysis complete!")

        return result


# Singleton instance
_analyzer: PortfolioAnalyzer | None = None


def get_analyzer() -> PortfolioAnalyzer:
    """Get singleton analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = PortfolioAnalyzer()
    return _analyzer
