"""Rich terminal dashboard for beautiful portfolio reports."""

from decimal import Decimal

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .models import Portfolio, PortfolioAnalysis, RiskLevel, SentimentScore, StockAnalysis

console = Console()


def format_currency(value: Decimal | None, prefix: str = "$") -> str:
    """Format a decimal as currency."""
    if value is None:
        return "N/A"
    return f"{prefix}{value:,.2f}"


def format_percent(value: float | None, with_sign: bool = True) -> str:
    """Format a float as percentage."""
    if value is None:
        return "N/A"
    if with_sign:
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.2f}%"
    return f"{value:.2f}%"


def get_percent_style(value: float | None) -> str:
    """Get style based on percentage value."""
    if value is None:
        return ""
    if value > 5:
        return "bold green"
    elif value > 0:
        return "green"
    elif value < -5:
        return "bold red"
    elif value < 0:
        return "red"
    return "yellow"


def get_sentiment_display(sentiment: SentimentScore | None) -> Text:
    """Get rich text display for sentiment."""
    if sentiment is None:
        return Text("Unknown", style="dim")

    styles = {
        SentimentScore.VERY_BULLISH: ("Very Bullish", "bold green"),
        SentimentScore.BULLISH: ("Bullish", "green"),
        SentimentScore.NEUTRAL: ("Neutral", "yellow"),
        SentimentScore.BEARISH: ("Bearish", "red"),
        SentimentScore.VERY_BEARISH: ("Very Bearish", "bold red"),
    }

    label, style = styles[sentiment]
    return Text(f"{sentiment.emoji} {label}", style=style)


def get_risk_display(risk: RiskLevel | None) -> Text:
    """Get rich text display for risk level."""
    if risk is None:
        return Text("Unknown", style="dim")

    styles = {
        RiskLevel.LOW: ("Low", "green"),
        RiskLevel.MEDIUM: ("Medium", "yellow"),
        RiskLevel.HIGH: ("High", "orange1"),
        RiskLevel.VERY_HIGH: ("Very High", "bold red"),
    }

    label, style = styles[risk]
    return Text(f"{risk.emoji} {label}", style=style)


def create_holdings_table(portfolio: Portfolio) -> Table:
    """Create a rich table showing portfolio holdings."""
    table = Table(title="📊 Portfolio Holdings", box=box.ROUNDED, header_style="bold cyan", show_lines=True)

    table.add_column("Symbol", style="bold", justify="center")
    table.add_column("Company", max_width=25)
    table.add_column("Shares", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Gain/Loss", justify="right")
    table.add_column("Gain %", justify="right")
    table.add_column("Allocation", justify="right")

    allocation = portfolio.get_allocation()

    for holding in portfolio.holdings:
        gain_style = get_percent_style(holding.gain_loss_percent)

        table.add_row(
            holding.symbol,
            holding.company_name or "Unknown",
            f"{holding.shares:,.2f}",
            format_currency(holding.current_price),
            format_currency(holding.current_value),
            format_currency(holding.cost_basis) if holding.cost_basis else "N/A",
            format_currency(holding.total_gain_loss),
            Text(format_percent(holding.gain_loss_percent), style=gain_style),
            f"{allocation.get(holding.symbol, 0):.1f}%",
        )

    return table


def create_summary_panel(portfolio: Portfolio) -> Panel:
    """Create a summary panel for the portfolio."""
    content = Text()

    content.append("📈 Total Value: ", style="bold")
    content.append(format_currency(portfolio.total_value), style="bold green")
    content.append("\n")

    content.append("💰 Total Cost: ", style="bold")
    content.append(format_currency(portfolio.total_cost), style="")
    content.append("\n")

    gain_style = get_percent_style(portfolio.total_gain_loss_percent)
    content.append("📊 Total Gain/Loss: ", style="bold")
    content.append(format_currency(portfolio.total_gain_loss), style=gain_style)
    content.append(" (", style="")
    content.append(format_percent(portfolio.total_gain_loss_percent), style=gain_style)
    content.append(")\n", style="")

    content.append("🏢 Holdings: ", style="bold")
    content.append(f"{len(portfolio.holdings)} stocks", style="")

    return Panel(content, title=f"💼 {portfolio.name}", border_style="cyan")


def create_analysis_table(analyses: dict[str, StockAnalysis]) -> Table:
    """Create a table showing stock analysis details."""
    table = Table(title="📉 Technical Analysis", box=box.ROUNDED, header_style="bold magenta")

    table.add_column("Symbol", style="bold")
    table.add_column("1D", justify="right")
    table.add_column("7D", justify="right")
    table.add_column("30D", justify="right")
    table.add_column("Volatility", justify="right")
    table.add_column("RSI", justify="right")
    table.add_column("50-MA", justify="center")
    table.add_column("200-MA", justify="center")
    table.add_column("Risk", justify="center")
    table.add_column("Sentiment", justify="center")

    for symbol, analysis in analyses.items():
        table.add_row(
            symbol,
            Text(
                format_percent(analysis.price_change_1d),
                style=get_percent_style(analysis.price_change_1d),
            ),
            Text(
                format_percent(analysis.price_change_7d),
                style=get_percent_style(analysis.price_change_7d),
            ),
            Text(
                format_percent(analysis.price_change_30d),
                style=get_percent_style(analysis.price_change_30d),
            ),
            f"{analysis.volatility_30d:.1f}%" if analysis.volatility_30d else "N/A",
            f"{analysis.rsi_14:.1f}" if analysis.rsi_14 else "N/A",
            "✅" if analysis.above_50_ma else "❌" if analysis.above_50_ma is False else "—",
            "✅" if analysis.above_200_ma else "❌" if analysis.above_200_ma is False else "—",
            get_risk_display(analysis.risk_level),
            get_sentiment_display(analysis.overall_sentiment),
        )

    return table


def create_sector_table(portfolio: Portfolio) -> Table:
    """Create a table showing sector allocation."""
    table = Table(title="🏭 Sector Allocation", box=box.ROUNDED, header_style="bold yellow")

    table.add_column("Sector", style="bold")
    table.add_column("Allocation", justify="right")
    table.add_column("", width=30)  # Progress bar column

    sector_alloc = portfolio.get_sector_allocation()
    for sector, pct in sorted(sector_alloc.items(), key=lambda x: x[1], reverse=True):
        bar_width = int(pct / 100 * 25)
        bar = "█" * bar_width + "░" * (25 - bar_width)
        table.add_row(sector, f"{pct:.1f}%", Text(bar, style="cyan"))

    return table


def create_insights_panel(analysis: PortfolioAnalysis) -> Panel:
    """Create a panel with AI-generated insights."""
    content = Text()

    if analysis.portfolio_summary:
        content.append("📝 Summary\n", style="bold cyan")
        content.append(f"{analysis.portfolio_summary}\n\n")

    if analysis.diversification_score is not None:
        content.append("🎯 Diversification Score: ", style="bold")
        score_style = (
            "green"
            if analysis.diversification_score >= 70
            else "yellow"
            if analysis.diversification_score >= 40
            else "red"
        )
        content.append(f"{analysis.diversification_score}/100\n", style=score_style)

    if analysis.risk_score is not None:
        content.append("⚠️ Risk Score: ", style="bold")
        risk_style = "green" if analysis.risk_score <= 30 else "yellow" if analysis.risk_score <= 60 else "red"
        content.append(f"{analysis.risk_score}/100\n", style=risk_style)

    if analysis.overall_sentiment:
        content.append("💭 Overall Sentiment: ", style="bold")
        content.append(f"{analysis.overall_sentiment}\n")

    if analysis.strengths:
        content.append("\n💪 Strengths\n", style="bold green")
        for s in analysis.strengths:
            content.append(f"  • {s}\n")

    if analysis.weaknesses:
        content.append("\n⚠️ Weaknesses\n", style="bold yellow")
        for w in analysis.weaknesses:
            content.append(f"  • {w}\n")

    if analysis.recommendations:
        content.append("\n💡 Recommendations\n", style="bold cyan")
        for r in analysis.recommendations:
            content.append(f"  • {r}\n")

    if analysis.market_outlook:
        content.append("\n🔮 Market Outlook\n", style="bold magenta")
        content.append(f"  {analysis.market_outlook}\n")

    return Panel(content, title="🤖 AI Insights", border_style="magenta")


def create_news_panel(analyses: dict[str, StockAnalysis]) -> Panel:
    """Create a panel showing recent news with sentiment."""
    content = Text()

    for symbol, analysis in analyses.items():
        if not analysis.news_articles:
            continue

        content.append(f"\n{symbol}\n", style="bold cyan")

        if analysis.sentiment_summary:
            content.append(f"  {analysis.sentiment_summary}\n", style="dim italic")

        for article in analysis.news_articles[:3]:
            sentiment_emoji = article.sentiment.emoji if article.sentiment else "❓"
            content.append(f"  {sentiment_emoji} ", style="")
            content.append(
                f"{article.title[:60]}...\n" if len(article.title) > 60 else f"{article.title}\n",
                style="",
            )
            content.append(
                f"     {article.source} • {article.published_at.strftime('%Y-%m-%d')}\n",
                style="dim",
            )

    return Panel(content, title="📰 News & Sentiment", border_style="yellow")


def display_full_report(analysis: PortfolioAnalysis) -> None:
    """Display a complete portfolio analysis report."""
    portfolio = analysis.portfolio

    # Summary
    console.print(create_summary_panel(portfolio))
    console.print()

    # Holdings table
    console.print(create_holdings_table(portfolio))
    console.print()

    # Sector allocation
    console.print(create_sector_table(portfolio))
    console.print()

    # Technical analysis
    if analysis.stock_analyses:
        console.print(create_analysis_table(analysis.stock_analyses))
        console.print()

    # AI Insights
    if analysis.portfolio_summary or analysis.recommendations:
        console.print(create_insights_panel(analysis))
        console.print()

    # News
    has_news = any(a.news_articles for a in analysis.stock_analyses.values())
    if has_news:
        console.print(create_news_panel(analysis.stock_analyses))


def create_progress_bar() -> Progress:
    """Create a rich progress bar for analysis."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    )
