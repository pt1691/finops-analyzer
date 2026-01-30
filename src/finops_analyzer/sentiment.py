"""AI-powered sentiment analyzer using OpenAI or Anthropic."""

import json
import logging
from datetime import datetime, timedelta

import httpx
from diskcache import Cache

from .config import AIProvider, get_settings
from .models import NewsArticle, SentimentScore, StockAnalysis

logger = logging.getLogger(__name__)


# System prompt for sentiment analysis
SENTIMENT_SYSTEM_PROMPT = """You are a senior financial analyst specializing in stock market sentiment analysis.
Your task is to analyze news articles about a stock and provide sentiment ratings.

For each article, analyze:
1. The overall sentiment (very_bearish, bearish, neutral, bullish, very_bullish)
2. Key points that influenced your rating
3. Brief reasoning for your sentiment score

Respond in valid JSON format only."""


SENTIMENT_USER_PROMPT = """Analyze the sentiment of these news articles for {symbol}:

{articles_text}

Respond with a JSON object in this exact format:
{{
    "articles": [
        {{
            "index": 0,
            "sentiment": "bullish",
            "reasoning": "Brief explanation",
            "key_points": ["point 1", "point 2"]
        }}
    ],
    "overall_sentiment": "bullish",
    "summary": "2-3 sentence summary of the overall news sentiment for {symbol}"
}}

Valid sentiment values: very_bearish, bearish, neutral, bullish, very_bullish"""


PORTFOLIO_INSIGHTS_PROMPT = """You are a senior portfolio manager providing analysis for a retail investor.

Portfolio Summary:
{portfolio_summary}

Individual Stock Analyses:
{stock_analyses}

Provide a comprehensive portfolio analysis in this exact JSON format:
{{
    "portfolio_summary": "2-3 sentence overall portfolio assessment",
    "diversification_score": 75,
    "risk_score": 45,
    "overall_sentiment": "bullish",
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
    "market_outlook": "1-2 sentence market outlook relevant to this portfolio"
}}

Be specific, actionable, and consider the current market conditions. diversification_score and risk_score should be 0-100."""


class NewsFetcher:
    """Fetches financial news for stocks."""

    def __init__(self):
        self.settings = get_settings()
        if self.settings.cache_enabled:
            self.settings.cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache = Cache(str(self.settings.cache_dir / "news"))
        else:
            self._cache = None

    def fetch_news(self, symbol: str) -> list[NewsArticle]:
        """Fetch news articles for a stock symbol."""
        cache_key = f"news_{symbol}"
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                return [NewsArticle(**a) for a in cached]

        articles = []

        # Try NewsAPI if key is available
        if self.settings.newsapi_key:
            articles = self._fetch_from_newsapi(symbol)

        # Fallback: Use yfinance news (free, no API key)
        if not articles:
            articles = self._fetch_from_yfinance(symbol)

        if self._cache and articles:
            self._cache.set(
                cache_key,
                [a.model_dump() for a in articles],
                expire=self.settings.cache_ttl_seconds,
            )

        return articles[: self.settings.sentiment_news_count]

    def _fetch_from_yfinance(self, symbol: str) -> list[NewsArticle]:
        """Fetch news using yfinance (free)."""
        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news or []

            articles = []
            for item in news_items[: self.settings.sentiment_news_count]:
                articles.append(
                    NewsArticle(
                        title=item.get("title", ""),
                        description=item.get("summary", ""),
                        source=item.get("publisher", "Unknown"),
                        url=item.get("link", ""),
                        published_at=datetime.fromtimestamp(item.get("providerPublishTime", 0)),
                        symbol=symbol,
                    )
                )
            return articles
        except Exception as e:
            logger.error(f"Error fetching yfinance news for {symbol}: {e}")
            return []

    def _fetch_from_newsapi(self, symbol: str) -> list[NewsArticle]:
        """Fetch news from NewsAPI.org (requires API key)."""
        if not self.settings.newsapi_key:
            return []

        try:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": f"{symbol} stock",
                "from": from_date,
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": self.settings.sentiment_news_count,
                "apiKey": self.settings.newsapi_key.get_secret_value(),
            }

            response = httpx.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            articles = []
            for item in data.get("articles", []):
                articles.append(
                    NewsArticle(
                        title=item.get("title", ""),
                        description=item.get("description", ""),
                        source=item.get("source", {}).get("name", "Unknown"),
                        url=item.get("url", ""),
                        published_at=datetime.fromisoformat(item.get("publishedAt", "").replace("Z", "+00:00")),
                        symbol=symbol,
                    )
                )
            return articles
        except Exception as e:
            logger.error(f"Error fetching NewsAPI news for {symbol}: {e}")
            return []


class AIAnalyzer:
    """AI-powered analysis using OpenAI or Anthropic."""

    def __init__(self):
        self.settings = get_settings()
        self._openai_client = None
        self._anthropic_client = None

    @property
    def openai_client(self):
        """Lazy load OpenAI client."""
        if self._openai_client is None:
            from openai import OpenAI

            api_key = self.settings.openai_api_key
            if api_key:
                self._openai_client = OpenAI(api_key=api_key.get_secret_value())
        return self._openai_client

    @property
    def anthropic_client(self):
        """Lazy load Anthropic client."""
        if self._anthropic_client is None:
            from anthropic import Anthropic

            api_key = self.settings.anthropic_api_key
            if api_key:
                self._anthropic_client = Anthropic(api_key=api_key.get_secret_value())
        return self._anthropic_client

    def _call_ai(self, system_prompt: str, user_prompt: str) -> str | None:
        """Call the configured AI provider."""
        try:
            if self.settings.ai_provider == AIProvider.OPENAI:
                return self._call_openai(system_prompt, user_prompt)
            else:
                return self._call_anthropic(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            return None

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str | None:
        """Call OpenAI API."""
        if not self.openai_client:
            logger.warning("OpenAI client not configured")
            return None

        response = self.openai_client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str | None:
        """Call Anthropic API."""
        if not self.anthropic_client:
            logger.warning("Anthropic client not configured")
            return None

        response = self.anthropic_client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def analyze_sentiment(
        self, symbol: str, articles: list[NewsArticle]
    ) -> tuple[list[NewsArticle], SentimentScore | None, str | None]:
        """Analyze sentiment for news articles using AI."""
        if not articles:
            return articles, None, None

        # Prepare articles text
        articles_text = "\n\n".join(
            [
                f"[Article {i}]\nTitle: {a.title}\nSource: {a.source}\nDate: {a.published_at.strftime('%Y-%m-%d')}\nDescription: {a.description or 'N/A'}"
                for i, a in enumerate(articles)
            ]
        )

        user_prompt = SENTIMENT_USER_PROMPT.format(symbol=symbol, articles_text=articles_text)

        response = self._call_ai(SENTIMENT_SYSTEM_PROMPT, user_prompt)

        if not response:
            return articles, None, None

        try:
            # Parse JSON response
            data = json.loads(response)

            # Update articles with sentiment
            for article_data in data.get("articles", []):
                idx = article_data.get("index", 0)
                if 0 <= idx < len(articles):
                    sentiment_str = article_data.get("sentiment", "neutral")
                    articles[idx].sentiment = SentimentScore(sentiment_str)
                    articles[idx].sentiment_reasoning = article_data.get("reasoning")
                    articles[idx].key_points = article_data.get("key_points", [])

            overall = SentimentScore(data.get("overall_sentiment", "neutral"))
            summary = data.get("summary")

            return articles, overall, summary

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            return articles, None, None

    def generate_portfolio_insights(self, portfolio_summary: str, stock_analyses: dict[str, StockAnalysis]) -> dict:
        """Generate AI insights for the entire portfolio."""
        # Format stock analyses
        analyses_text = ""
        for symbol, analysis in stock_analyses.items():
            analyses_text += f"\n{symbol}:\n"
            analyses_text += (
                f"  - 30-day change: {analysis.price_change_30d:.1f}%\n" if analysis.price_change_30d else ""
            )
            analyses_text += f"  - Volatility: {analysis.volatility_30d:.1f}%\n" if analysis.volatility_30d else ""
            analyses_text += f"  - RSI: {analysis.rsi_14:.1f}\n" if analysis.rsi_14 else ""
            analyses_text += f"  - Risk: {analysis.risk_level.value if analysis.risk_level else 'Unknown'}\n"
            analyses_text += (
                f"  - Sentiment: {analysis.overall_sentiment.value if analysis.overall_sentiment else 'Unknown'}\n"
            )
            if analysis.risk_factors:
                analyses_text += f"  - Risk factors: {', '.join(analysis.risk_factors)}\n"

        user_prompt = PORTFOLIO_INSIGHTS_PROMPT.format(
            portfolio_summary=portfolio_summary, stock_analyses=analyses_text
        )

        response = self._call_ai("You are a senior portfolio manager. Respond only with valid JSON.", user_prompt)

        if not response:
            return {}

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse portfolio insights: {e}")
            return {}


# Singleton instances
_news_fetcher: NewsFetcher | None = None
_ai_analyzer: AIAnalyzer | None = None


def get_news_fetcher() -> NewsFetcher:
    """Get singleton news fetcher instance."""
    global _news_fetcher
    if _news_fetcher is None:
        _news_fetcher = NewsFetcher()
    return _news_fetcher


def get_ai_analyzer() -> AIAnalyzer:
    """Get singleton AI analyzer instance."""
    global _ai_analyzer
    if _ai_analyzer is None:
        _ai_analyzer = AIAnalyzer()
    return _ai_analyzer
