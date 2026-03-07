# fx/services/helpers.py
import re
import secrets
import string
from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import CallbackContext
import hashlib
import uuid


def sanitize_input(text: str) -> str:
    """
    Sanitize user input
    """
    if not text:
        return ""
    
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove any control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char == '\n')
    
    return text.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_mentions(text: str) -> List[str]:
    """
    Extract @mentions from text
    """
    return re.findall(r'@(\w+)', text)


def parse_command_args(text: str) -> List[str]:
    """
    Parse command arguments, handling quoted strings
    """
    args = []
    current = []
    in_quotes = False
    quote_char = None
    
    for char in text:
        if char in ['"', "'"] and not in_quotes:
            in_quotes = True
            quote_char = char
        elif char == quote_char and in_quotes:
            in_quotes = False
            quote_char = None
        elif char == ' ' and not in_quotes:
            if current:
                args.append(''.join(current))
                current = []
        else:
            current.append(char)
    
    if current:
        args.append(''.join(current))
    
    return args


def chunk_text(text: str, max_length: int = 4096) -> List[str]:
    """
    Split long text into chunks for Telegram
    """
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 <= max_length:
            if current_chunk:
                current_chunk += '\n' + line
            else:
                current_chunk = line
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def safe_send_message(update: Update, text: str, **kwargs) -> None:
    """
    Safely send a message with error handling
    """
    try:
        if update.callback_query:
            update.callback_query.message.reply_text(text, **kwargs)
        else:
            update.message.reply_text(text, **kwargs)
    except Exception as e:
        # Log error but don't raise
        print(f"Failed to send message: {e}")


def get_user_language(update: Update, context: CallbackContext) -> str:
    """
    Get user's preferred language
    """
    # Check context first
    if context.user_data and 'language' in context.user_data:
        return context.user_data['language']
    
    # Check user object
    if update.effective_user and update.effective_user.language_code:
        return update.effective_user.language_code.split('-')[0]
    
    # Default to English
    return 'en'


def localize_text(text_key: str, language: str, **kwargs) -> str:
    """
    Get localized text
    """
    # Simple translation dictionary
    translations = {
        'welcome': {
            'en': "Welcome!",
            'es': "¡Bienvenido!",
            'fr': "Bienvenue!",
            'de': "Willkommen!",
            'pt': "Bem-vindo!",
            'ru': "Добро пожаловать!",
            'zh': "欢迎！",
            'ja': "ようこそ！",
            'ar': "مرحبا!",
            'hi': "स्वागत है!"
        },
        'trade_executed': {
            'en': "Trade executed successfully!",
            'es': "¡Operación ejecutada con éxito!",
            'fr': "Transaction exécutée avec succès!",
            'de': "Trade erfolgreich ausgeführt!",
        },
    }
    
    # Get translation or fallback to English
    text = translations.get(text_key, {}).get(language, 
           translations.get(text_key, {}).get('en', text_key))
    
    # Format with kwargs
    if kwargs:
        try:
            text = text.format(**kwargs)
        except:
            pass
    
    return text


def generate_referral_code(user_id: int, length: int = 8) -> str:
    """
    Generate unique referral code for user
    """
    # Combine user ID with random string
    random_part = secrets.token_hex(4)
    user_part = hashlib.md5(str(user_id).encode()).hexdigest()[:4]
    code = f"{user_part}{random_part}".upper()
    
    return code[:length]


def calculate_pips(entry: float, exit: float, symbol: str) -> float:
    """
    Calculate pips between two prices
    """
    multiplier = get_pip_value(symbol)
    return abs(entry - exit) / multiplier


def get_pip_value(symbol: str) -> float:
    """
    Get pip value for symbol
    """
    if 'JPY' in symbol:
        return 0.01
    elif symbol in ['XAUUSD', 'GOLD']:
        return 0.1
    elif symbol in ['XAGUSD', 'SILVER']:
        return 0.001
    elif symbol in ['BTCUSD', 'ETHUSD']:
        return 1.0
    else:
        return 0.0001


def parse_timeframe(timeframe: str) -> timedelta:
    """
    Parse timeframe string to timedelta
    """
    timeframe = timeframe.upper()
    number = int(re.findall(r'\d+', timeframe)[0]) if re.findall(r'\d+', timeframe) else 1
    
    if 'M' in timeframe:
        return timedelta(minutes=number)
    elif 'H' in timeframe:
        return timedelta(hours=number)
    elif 'D' in timeframe:
        return timedelta(days=number)
    elif 'W' in timeframe:
        return timedelta(weeks=number)
    else:
        return timedelta(minutes=1)


def generate_trade_id() -> str:
    """
    Generate unique trade ID
    """
    return str(uuid.uuid4())


def dict_to_obj(data: Dict[str, Any], obj_class: Any) -> Any:
    """
    Convert dictionary to object
    """
    obj = obj_class()
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
    return obj


def obj_to_dict(obj: Any, exclude: List[str] = None) -> Dict[str, Any]:
    """
    Convert object to dictionary
    """
    exclude = exclude or []
    result = {}
    
    for key, value in obj.__dict__.items():
        if not key.startswith('_') and key not in exclude:
            result[key] = value
    
    return result


def is_valid_email(email: str) -> bool:
    """
    Basic email validation
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    """
    Basic phone validation
    """
    cleaned = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\+?[1-9]\d{7,14}$', cleaned))


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive information
    """
    if len(text) <= visible_chars:
        return '*' * len(text)
    
    visible = text[-visible_chars:]
    masked = '*' * (len(text) - visible_chars)
    return masked + visible