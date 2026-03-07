# fx/utils/formatters.py
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from prettytable import PrettyTable
import humanize
import json


def format_trade_calculation(
    calculation: Dict[str, Any],
    show_confirmation: bool = True
) -> str:
    """
    Format trade calculation for display
    """
    signal = calculation.get('signal', {})
    calc = calculation.get('calculated', {})
    
    # Create table
    table = PrettyTable()
    table.title = "📊 Trade Information"
    table.field_names = ["Key", "Value"]
    table.align["Key"] = "l"
    table.align["Value"] = "l"
    
    # Basic trade info
    table.add_row([
        f"{signal.get('order_type', 'Unknown')}",
        signal.get('symbol', 'N/A')
    ])
    table.add_row(['Entry', f"{signal.get('entry', 'MARKET'):.5f}" if signal.get('entry') else 'MARKET'])
    table.add_row(['Stop Loss', f"{calc.get('stop_loss_pips', 0)} pips"])
    
    # Take profits
    tp_pips = calc.get('take_profit_pips', [])
    for i, pips in enumerate(tp_pips, 1):
        table.add_row([f'TP {i}', f'{pips} pips'])
    
    # Risk and position
    table.add_row(['\nRisk Factor', f'\n{calc.get("risk_percentage", 0):.1f}%'])
    table.add_row(['Position Size', f"{calc.get('position_size', 0):.2f} lots"])
    
    # Balance
    table.add_row(['\nCurrent Balance', f'\n$ {calculation.get("account", {}).get("balance", 0):,.2f}'])
    table.add_row(['Potential Loss', f'$ {calc.get("potential_loss", 0):,.2f}'])
    
    # Profits
    profits = calc.get('potential_profits', [])
    for i, profit in enumerate(profits, 1):
        table.add_row([f'TP {i} Profit', f'$ {profit:,.2f}'])
    
    table.add_row(['\nTotal Profit', f'\n$ {calc.get("total_profit", 0):,.2f}'])
    table.add_row(['R:R Ratio', f'1:{calc.get("risk_reward_ratio", 0):.2f}'])
    
    return f'<pre>{table}</pre>'


def format_balance(account_info: Dict[str, Any]) -> str:
    """
    Format account balance information
    """
    table = PrettyTable()
    table.title = "💰 Account Balance"
    table.field_names = ["Item", "Value"]
    table.align["Item"] = "l"
    table.align["Value"] = "l"
    
    table.add_row(['Balance', f'$ {account_info.get("balance", 0):,.2f}'])
    table.add_row(['Equity', f'$ {account_info.get("equity", 0):,.2f}'])
    table.add_row(['Margin', f'$ {account_info.get("margin", 0):,.2f}'])
    table.add_row(['Free Margin', f'$ {account_info.get("free_margin", 0):,.2f}'])
    table.add_row(['Margin Level', f'{account_info.get("margin_level", 0):.2f}%'])
    table.add_row(['Currency', account_info.get("currency", "USD")])
    table.add_row(['Server', account_info.get("server", "Unknown")])
    
    return f'<pre>{table}</pre>'


def format_positions(positions: List[Dict[str, Any]]) -> str:
    """
    Format open positions for display
    """
    if not positions:
        return "No open positions."
    
    table = PrettyTable()
    table.title = "📈 Open Positions"
    table.field_names = ["Symbol", "Type", "Volume", "Open Price", "Current", "Profit", "Pips"]
    table.align["Symbol"] = "l"
    table.align["Profit"] = "r"
    
    total_profit = 0
    
    for pos in positions[:10]:  # Show only first 10
        profit = pos.get('profit', 0)
        total_profit += profit
        
        # Determine emoji based on profit
        profit_emoji = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
        
        table.add_row([
            pos.get('symbol', 'N/A'),
            pos.get('type', 'N/A'),
            f"{pos.get('volume', 0):.2f}",
            f"{pos.get('openPrice', 0):.5f}",
            f"{pos.get('currentPrice', 0):.5f}",
            f"{profit_emoji} ${profit:,.2f}",
            f"{pos.get('pips', 0):.1f}"
        ])
    
    # Add total row
    total_emoji = "🟢" if total_profit > 0 else "🔴" if total_profit < 0 else "⚪"
    table.add_row([
        "TOTAL", "", "", "", "", 
        f"{total_emoji} ${total_profit:,.2f}", ""
    ])
    
    return f'<pre>{table}</pre>'


def format_trade_history(trades: List[Any]) -> str:
    """
    Format trade history for display
    """
    if not trades:
        return "No trade history."
    
    table = PrettyTable()
    table.title = "📜 Trade History"
    table.field_names = ["Date", "Type", "Symbol", "Size", "Entry", "Exit", "Profit"]
    table.align["Profit"] = "r"
    
    for trade in trades[:10]:  # Show last 10 trades
        profit = trade.profit_loss or 0
        profit_emoji = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
        
        table.add_row([
            trade.created_at.strftime("%m/%d %H:%M"),
            trade.order_type[:4] + "...",
            trade.symbol,
            f"{trade.position_size:.2f}",
            f"{trade.entry_price:.5f}" if trade.entry_price else "MARKET",
            f"{trade.exit_price:.5f}" if trade.exit_price else "OPEN",
            f"{profit_emoji} ${profit:,.2f}"
        ])
    
    return f'<pre>{table}</pre>'


def format_number(num: float, decimals: int = 2, currency: bool = False) -> str:
    """
    Format number with thousand separators
    """
    if currency:
        return f"${num:,.{decimals}f}"
    return f"{num:,.{decimals}f}"


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime
    """
    return dt.strftime(format)


def format_duration(seconds: float) -> str:
    """
    Format duration in human readable format
    """
    return humanize.naturaldelta(timedelta(seconds=seconds))


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage
    """
    return f"{value * 100:.{decimals}f}%"


def create_progress_bar(percentage: float, length: int = 10) -> str:
    """
    Create text progress bar
    """
    filled = int(percentage * length)
    empty = length - filled
    return "█" * filled + "░" * empty


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format JSON data for display
    """
    return json.dumps(data, indent=indent, default=str)


def format_table(data: List[Dict[str, Any]], columns: List[str]) -> str:
    """
    Generic table formatter
    """
    table = PrettyTable()
    table.field_names = columns
    
    for row in data:
        table.add_row([row.get(col, 'N/A') for col in columns])
    
    return str(table)


def format_risk_warning(risk_level: str, message: str) -> str:
    """
    Format risk warning message
    """
    icons = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🟠',
        'critical': '🔴'
    }
    
    icon = icons.get(risk_level.lower(), '⚠️')
    return f"{icon} *Risk Warning:* {message}"


def format_success_message(message: str) -> str:
    """
    Format success message
    """
    return f"✅ {message}"


def format_error_message(message: str) -> str:
    """
    Format error message
    """
    return f"❌ {message}"