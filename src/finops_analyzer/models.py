"""Core data models for portfolio analysis."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, computed_field


class SentimentScore(str, Enum):
    """Sentiment classification for news analysis."""

    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"

    @property
    def emoji(self) -> str:
        """Get emoji representation of sentiment."""
        return {
            self.VERY_BEARISH: "🔴",
            self.BEARISH: "🟠",
            self.NEUTRAL: "🟡",
            self.BULLISH: "🟢",
            self.VERY_BULLISH: "🟢✨",
        }[self]

    @property
    def score(self) -> float:
        """Get numeric score (-1 to 1)."""
        return {
            self.VERY_BEARISH: -1.0,
            self.BEARISH: -0.5,
            self.NEUTRAL: 0.0,
            self.BULLISH: 0.5,
            self.VERY_BULLISH: 1.0,
        }[self]


class RiskLevel(str, Enum):
    """Risk classification for holdings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @property
    def emoji(self) -> str:
        return {
            self.LOW: "🟢",
            self.MEDIUM: "🟡",
            self.HIGH: "🟠",
            self.VERY_HIGH: "🔴",
        }[self]


class StockHolding(BaseModel):
    """Represents a single stock holding in the portfolio."""

    symbol: str = Field(..., description="Stock ticker symbol (e.g., AAPL)")
    shares: Decimal = Field(..., gt=0, description="Number of shares owned")
    cost_basis: Decimal | None = Field(default=None, description="Average purchase price per share")

    # Populated after fetching data
    current_price: Decimal | None = None
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: Decimal | None = None
    pe_ratio: float | None = None
    dividend_yield: float | None = None
    fifty_two_week_high: Decimal | None = None
    fifty_two_week_low: Decimal | None = None

    @computed_field
    @property
    def current_value(self) -> Decimal | None:
        """Calculate current market value of holding."""
        if self.current_price:
            return self.shares * self.current_price
        return None

    @computed_field
    @property
    def total_gain_loss(self) -> Decimal | None:
        """Calculate total unrealized gain/loss."""
        if self.current_price and self.cost_basis:
            return (self.current_price - self.cost_basis) * self.shares
        return None

    @computed_field
    @property
    def gain_loss_percent(self) -> float | None:
        """Calculate percentage gain/loss."""
        if self.current_price and self.cost_basis and self.cost_basis > 0:
            return float((self.current_price - self.cost_basis) / self.cost_basis * 100)
        return None


class NewsArticle(BaseModel):
    """Represents a news article for sentiment analysis."""

    title: str
    description: str | None = None
    source: str
    url: str
    published_at: datetime
    symbol: str

    # Populated after AI analysis
    sentiment: SentimentScore | None = None
    sentiment_reasoning: str | None = None
    key_points: list[str] = Field(default_factory=list)


class StockAnalysis(BaseModel):
    """Complete analysis for a single stock."""

    symbol: str
    analyzed_at: datetime = Field(default_factory=datetime.now)

    # Price metrics
    price_change_1d: float | None = None
    price_change_7d: float | None = None
    price_change_30d: float | None = None
    volatility_30d: float | None = None

    # Technical indicators
    rsi_14: float | None = None
    above_50_ma: bool | None = None
    above_200_ma: bool | None = None

    # Sentiment
    news_articles: list[NewsArticle] = Field(default_factory=list)
    overall_sentiment: SentimentScore | None = None
    sentiment_summary: str | None = None

    # Risk assessment
    risk_level: RiskLevel | None = None
    risk_factors: list[str] = Field(default_factory=list)


class Portfolio(BaseModel):
    """Represents an investment portfolio."""

    name: str = "My Portfolio"
    holdings: list[StockHolding] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def total_value(self) -> Decimal:
        """Calculate total portfolio value."""
        return sum((h.current_value or Decimal("0") for h in self.holdings), Decimal("0"))

    @computed_field
    @property
    def total_cost(self) -> Decimal:
        """Calculate total cost basis."""
        return sum(
            (h.cost_basis * h.shares if h.cost_basis else Decimal("0") for h in self.holdings),
            Decimal("0"),
        )

    @computed_field
    @property
    def total_gain_loss(self) -> Decimal:
        """Calculate total unrealized gain/loss."""
        return self.total_value - self.total_cost

    @computed_field
    @property
    def total_gain_loss_percent(self) -> float:
        """Calculate total percentage gain/loss."""
        if self.total_cost > 0:
            return float(self.total_gain_loss / self.total_cost * 100)
        return 0.0

    def get_allocation(self) -> dict[str, float]:
        """Get percentage allocation for each holding."""
        if self.total_value == 0:
            return {}
        return {h.symbol: float((h.current_value or Decimal("0")) / self.total_value * 100) for h in self.holdings}

    def get_sector_allocation(self) -> dict[str, float]:
        """Get percentage allocation by sector."""
        if self.total_value == 0:
            return {}
        sector_values: dict[str, Decimal] = {}
        for h in self.holdings:
            sector = h.sector or "Unknown"
            sector_values[sector] = sector_values.get(sector, Decimal("0")) + (h.current_value or Decimal("0"))
        return {sector: float(value / self.total_value * 100) for sector, value in sector_values.items()}


class PortfolioAnalysis(BaseModel):
    """Complete portfolio analysis with AI insights."""

    portfolio: Portfolio
    analyzed_at: datetime = Field(default_factory=datetime.now)

    # Per-stock analysis
    stock_analyses: dict[str, StockAnalysis] = Field(default_factory=dict)

    # AI-generated insights
    portfolio_summary: str | None = None
    diversification_score: int | None = None
    risk_score: int | None = None
    overall_sentiment: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    market_outlook: str | None = None
