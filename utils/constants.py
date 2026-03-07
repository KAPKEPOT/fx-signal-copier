# fx/utils/constants.py

# Time constants
SECONDS_IN_MINUTE = 60
SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400
SECONDS_IN_WEEK = 604800

# Size constants
KB = 1024
MB = KB * 1024
GB = MB * 1024

# HTTP status codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_ERROR = 500

# Regular expressions
REGEX_EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
REGEX_PHONE = r'^\+?[1-9]\d{1,14}$'
REGEX_UUID = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
REGEX_USERNAME = r'^[a-zA-Z0-9_]{5,32}$'
REGEX_SYMBOL = r'^[A-Z]{6}$'

# Date formats
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
TIME_FORMAT = "%H:%M:%S"

# Log levels
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

# Progress bar symbols
PROGRESS_BAR = {
    'filled': '█',
    'empty': '░',
    'partial': '▒'
}

# Emoji icons
ICONS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'trade': '📈',
    'balance': '💰',
    'settings': '⚙️',
    'user': '👤',
    'admin': '👑',
    'time': '⏰',
    'chart': '📊',
    'profit_up': '🟢',
    'profit_down': '🔴',
    'neutral': '⚪'
}