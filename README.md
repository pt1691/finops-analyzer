# 📊 FinOps Analyzer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **AI-Powered Financial Portfolio Analyzer with NLP Sentiment Analysis**

A sophisticated Python CLI tool that analyzes stock portfolios using real-time market data, technical indicators, and AI-powered sentiment analysis. Get actionable insights with beautiful terminal dashboards.

![FinOps Analyzer Demo](docs/demo.gif)

## ✨ Features

- 📈 **Real-time Stock Data** - Fetches live prices, fundamentals, and historical data via Yahoo Finance
- 🤖 **AI-Powered Analysis** - Uses OpenAI GPT-4 or Anthropic Claude for intelligent insights
- 📰 **News Sentiment Analysis** - Analyzes recent news articles using NLP to gauge market sentiment
- 📊 **Technical Indicators** - RSI, moving averages, volatility, and price momentum
- 🎨 **Beautiful Terminal UI** - Rich, colorful dashboards using the Rich library
- 💾 **Smart Caching** - Reduces API calls with intelligent disk caching
- 🔧 **Highly Configurable** - Environment-based configuration for flexibility

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/praneethturlapati/finops-analyzer.git
cd finops-analyzer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your API keys
# Required for AI features: OpenAI or Anthropic API key
```

### Usage

```bash
# Analyze a portfolio from CSV
finops analyze examples/sample_portfolio.csv

# Quick analysis with stock symbols
finops analyze --symbols AAPL,GOOGL,MSFT,AMZN

# Get a quick quote for a single stock
finops quote NVDA

# Skip AI analysis (faster, no API costs)
finops analyze examples/sample_portfolio.csv --no-ai

# Save results to JSON
finops analyze --symbols AAPL,MSFT -o results.json

# View current configuration
finops config

# Clear cache
finops clear-cache
```

## 📋 Portfolio CSV Format

Create a CSV file with your holdings:

```csv
symbol,shares,cost_basis
AAPL,50,145.00
GOOGL,25,125.00
MSFT,40,320.00
NVDA,20,450.00
```

- `symbol` - Stock ticker symbol (required)
- `shares` - Number of shares owned (required)
- `cost_basis` - Average purchase price per share (optional, for gain/loss calculation)

## 🤖 AI Providers

FinOps Analyzer supports both OpenAI and Anthropic:

| Provider | Model | Cost (approx) | Best For |
|----------|-------|---------------|----------|
| OpenAI | gpt-4o-mini | ~$0.15/1M tokens | Cost-effective daily use |
| OpenAI | gpt-4o | ~$2.50/1M tokens | Highest quality insights |
| Anthropic | claude-3-haiku | ~$0.25/1M tokens | Fast, affordable analysis |
| Anthropic | claude-3-sonnet | ~$3/1M tokens | Balanced quality/cost |

**Expected costs:** $0.01-0.05 per portfolio analysis with default settings.

## 📊 Sample Output

```
┌──────────────────────────────────────────────────────────────────────┐
│                        📊 Portfolio Holdings                         │
├────────┬─────────────┬────────┬─────────┬──────────┬─────────────────┤
│ Symbol │ Company     │ Shares │ Price   │ Value    │ Gain/Loss       │
├────────┼─────────────┼────────┼─────────┼──────────┼─────────────────┤
│ AAPL   │ Apple Inc.  │ 50.00  │ $185.50 │ $9,275   │ +$2,025 (27.9%) │
│ NVDA   │ NVIDIA Corp │ 20.00  │ $890.25 │ $17,805  │ +$8,805 (97.9%) │
│ MSFT   │ Microsoft   │ 40.00  │ $415.30 │ $16,612  │ +$3,812 (29.8%) │
└────────┴─────────────┴────────┴─────────┴──────────┴─────────────────┘

╔══════════════════════════════════════════════════════════════════════╗
║                      🤖 AI Portfolio Insights                        ║
╠══════════════════════════════════════════════════════════════════════╣
║ 📊 Portfolio Metrics                                                 ║
║    Diversification Score: 72/100                                     ║
║    Risk Score: 45/100                                                ║
║    Overall Sentiment: 🟢 Bullish                                     ║
║                                                                      ║
║ ✅ Strengths                                                         ║
║    • Strong tech sector exposure with market leaders                 ║
║    • Healthy mix of growth and value stocks                          ║
║    • Most holdings above 200-day moving average                      ║
║                                                                      ║
║ 🎯 Recommendations                                                   ║
║    • Consider adding defensive sectors for diversification           ║
║    • NVDA position is 35% of portfolio - consider rebalancing        ║
╚══════════════════════════════════════════════════════════════════════╝
```

## 🔧 Configuration Options

All settings can be configured via environment variables (prefix: `FINOPS_`):

| Variable | Description | Default |
|----------|-------------|---------|
| `FINOPS_AI_PROVIDER` | AI provider (`openai` or `anthropic`) | `openai` |
| `FINOPS_OPENAI_API_KEY` | OpenAI API key | - |
| `FINOPS_ANTHROPIC_API_KEY` | Anthropic API key | - |
| `FINOPS_OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `FINOPS_ANTHROPIC_MODEL` | Anthropic model to use | `claude-3-haiku-20240307` |
| `FINOPS_CACHE_ENABLED` | Enable disk caching | `true` |
| `FINOPS_CACHE_TTL_SECONDS` | Cache time-to-live | `3600` |
| `FINOPS_ANALYSIS_PERIOD_DAYS` | Days of historical data | `30` |
| `FINOPS_SENTIMENT_NEWS_COUNT` | News articles per stock | `10` |

## 🏗️ Architecture

```
finops-analyzer/
├── src/finops_analyzer/
│   ├── __init__.py          # Package metadata
│   ├── cli.py               # Typer CLI commands
│   ├── config.py            # Pydantic settings management
│   ├── models.py            # Data models (Portfolio, Stock, Analysis)
│   ├── stock_fetcher.py     # Yahoo Finance integration
│   ├── sentiment.py         # AI sentiment analysis
│   ├── analyzer.py          # Core analysis engine
│   └── dashboard.py         # Rich terminal UI
├── examples/
│   └── sample_portfolio.csv # Example portfolio
├── tests/                   # Test suite
├── pyproject.toml           # Project configuration
└── README.md
```

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Type checking
mypy src/
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙋‍♂️ Author

**Praneeth Turlapati**
- LinkedIn: [linkedin.com/in/praneeth-turlapati](https://linkedin.com/in/praneeth-turlapati)
- GitHub: [github.com/pt1691](https://github.com/pt1691)

---

⭐ **If you find this useful, please star the repository!**
