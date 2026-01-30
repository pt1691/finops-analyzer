"""Command-line interface for FinOps Analyzer."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from . import __version__
from .config import get_settings, AIProvider
from .analyzer import get_analyzer
from .dashboard import display_full_report, console

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = typer.Typer(
    name="finops",
    help="🚀 AI-Powered Financial Portfolio Analyzer",
    add_completion=False,
    rich_markup_mode="rich"
)


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"FinOps Analyzer v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Enable verbose logging."
    )
):
    """FinOps Analyzer - AI-Powered Portfolio Analysis Tool."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@app.command()
def analyze(
    portfolio_file: Path | None = typer.Argument(
        None,
        help="Path to portfolio CSV file (columns: symbol, shares, cost_basis)",
        exists=True,
        readable=True
    ),
    symbols: str | None = typer.Option(
        None,
        "--symbols",
        "-s",
        help="Comma-separated stock symbols (e.g., AAPL,GOOGL,MSFT)"
    ),
    no_news: bool = typer.Option(
        False,
        "--no-news",
        help="Skip news and sentiment analysis"
    ),
    no_ai: bool = typer.Option(
        False,
        "--no-ai",
        help="Skip AI-powered insights (runs faster, no API costs)"
    ),
    output_json: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Save analysis results to JSON file"
    )
):
    """
    📊 Analyze a stock portfolio with AI-powered insights.
    
    Examples:
    
        finops analyze portfolio.csv
        
        finops analyze --symbols AAPL,GOOGL,MSFT,AMZN
        
        finops analyze portfolio.csv --no-ai
    """
    analyzer = get_analyzer()
    settings = get_settings()
    
    # Validate input
    if not portfolio_file and not symbols:
        console.print("[red]Error:[/red] Provide either a portfolio CSV file or --symbols option")
        raise typer.Exit(1)
    
    # Load portfolio
    if portfolio_file:
        console.print(f"📂 Loading portfolio from [cyan]{portfolio_file}[/cyan]")
        portfolio = analyzer.load_portfolio_from_csv(portfolio_file)
    else:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        console.print(f"📊 Analyzing symbols: [cyan]{', '.join(symbol_list)}[/cyan]")
        portfolio = analyzer.load_portfolio_from_symbols(symbol_list)
    
    console.print(f"📈 Found [green]{len(portfolio.holdings)}[/green] holdings\n")
    
    # Check AI configuration
    include_ai = not no_ai
    if include_ai and not settings.get_active_api_key():
        console.print(Panel(
            Text.from_markup(
                "[yellow]⚠️ No AI API key configured.[/yellow]\n\n"
                "To enable AI-powered insights, set one of:\n"
                "  • [cyan]FINOPS_OPENAI_API_KEY[/cyan]\n"
                "  • [cyan]FINOPS_ANTHROPIC_API_KEY[/cyan]\n\n"
                "Continuing without AI analysis..."
            ),
            title="AI Configuration",
            border_style="yellow"
        ))
        console.print()
        include_ai = False
    elif include_ai:
        provider = settings.ai_provider.value
        model = settings.get_active_model()
        console.print(f"🤖 Using [magenta]{provider}[/magenta] ({model})\n")
    
    # Run analysis
    analysis = analyzer.analyze_with_progress(
        portfolio,
        include_news=not no_news,
        include_ai_insights=include_ai
    )
    
    console.print()
    
    # Display report
    display_full_report(analysis)
    
    # Save to JSON if requested
    if output_json:
        import json
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, 'w') as f:
            json.dump(analysis.model_dump(mode='json'), f, indent=2, default=str)
        console.print(f"\n💾 Results saved to [cyan]{output_json}[/cyan]")


@app.command()
def quote(
    symbol: str = typer.Argument(..., help="Stock symbol to look up")
):
    """
    📈 Get a quick quote for a single stock.
    
    Example:
    
        finops quote AAPL
    """
    from .stock_fetcher import get_stock_fetcher
    from .models import StockHolding
    from decimal import Decimal
    
    fetcher = get_stock_fetcher()
    
    console.print(f"📊 Fetching quote for [cyan]{symbol.upper()}[/cyan]...\n")
    
    holding = StockHolding(symbol=symbol.upper(), shares=Decimal("1"))
    holding = fetcher.enrich_holding(holding)
    analysis = fetcher.analyze_stock(symbol.upper())
    
    # Display quote
    content = Text()
    content.append(f"{holding.company_name or symbol.upper()}\n", style="bold")
    content.append(f"Symbol: ", style="dim")
    content.append(f"{holding.symbol}\n")
    content.append(f"Price: ", style="dim")
    content.append(f"${holding.current_price:,.2f}\n", style="bold green")
    content.append(f"Sector: ", style="dim")
    content.append(f"{holding.sector or 'N/A'}\n")
    content.append(f"Industry: ", style="dim")
    content.append(f"{holding.industry or 'N/A'}\n")
    
    if holding.pe_ratio:
        content.append(f"P/E Ratio: ", style="dim")
        content.append(f"{holding.pe_ratio:.2f}\n")
    
    if holding.dividend_yield:
        content.append(f"Dividend Yield: ", style="dim")
        content.append(f"{holding.dividend_yield * 100:.2f}%\n")
    
    if holding.fifty_two_week_high and holding.fifty_two_week_low:
        content.append(f"52W Range: ", style="dim")
        content.append(f"${holding.fifty_two_week_low:,.2f} - ${holding.fifty_two_week_high:,.2f}\n")
    
    console.print(Panel(content, title="📈 Stock Quote", border_style="cyan"))
    
    # Technical analysis
    if analysis.rsi_14:
        tech_content = Text()
        tech_content.append(f"RSI (14): ", style="dim")
        tech_content.append(f"{analysis.rsi_14:.1f}\n")
        
        if analysis.volatility_30d:
            tech_content.append(f"Volatility (30D): ", style="dim")
            tech_content.append(f"{analysis.volatility_30d:.1f}%\n")
        
        if analysis.price_change_30d:
            tech_content.append(f"30D Change: ", style="dim")
            style = "green" if analysis.price_change_30d > 0 else "red"
            tech_content.append(f"{analysis.price_change_30d:+.2f}%\n", style=style)
        
        console.print(Panel(tech_content, title="📉 Technical Indicators", border_style="magenta"))


@app.command()
def demo():
    """
    🎮 Run a demo analysis with sample portfolio.
    
    Uses a sample portfolio to demonstrate the tool.
    """
    from .models import StockHolding, Portfolio
    from decimal import Decimal
    
    console.print("[bold cyan]🎮 Running FinOps Analyzer Demo[/bold cyan]\n")
    
    # Create sample portfolio
    sample_holdings = [
        StockHolding(symbol="AAPL", shares=Decimal("50"), cost_basis=Decimal("150")),
        StockHolding(symbol="GOOGL", shares=Decimal("20"), cost_basis=Decimal("120")),
        StockHolding(symbol="MSFT", shares=Decimal("30"), cost_basis=Decimal("350")),
        StockHolding(symbol="AMZN", shares=Decimal("15"), cost_basis=Decimal("140")),
        StockHolding(symbol="NVDA", shares=Decimal("10"), cost_basis=Decimal("400")),
    ]
    
    portfolio = Portfolio(name="Demo Portfolio", holdings=sample_holdings)
    
    console.print("📊 Demo Portfolio:")
    for h in sample_holdings:
        console.print(f"  • {h.symbol}: {h.shares} shares @ ${h.cost_basis}")
    console.print()
    
    # Run analysis (without AI to avoid API costs)
    analyzer = get_analyzer()
    analysis = analyzer.analyze_with_progress(
        portfolio,
        include_news=True,
        include_ai_insights=False
    )
    
    console.print()
    display_full_report(analysis)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
