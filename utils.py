import os
import sys
import json
import urllib.request
import base64
import mimetypes
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from flask import jsonify, request, current_app
from flask_login import current_user
from cryptography.fernet import Fernet

# --- Timezone configuration ---
# We keep this here so it's a single source of truth for time
try:
    from zoneinfo import ZoneInfo
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        class ZoneInfo:
            def __init__(self, key): pass

BANGKOK_TZ = timezone.utc
try:
    real_tz = ZoneInfo("Asia/Bangkok")
    datetime.now(real_tz)
    BANGKOK_TZ = real_tz
except Exception as e:
    print(f"Warning: Timezone 'Asia/Bangkok' failed ({e}). Using UTC+7 offset.", file=sys.stderr)
    BANGKOK_TZ = timezone(timedelta(hours=7))

def now_bangkok():
    return datetime.now(BANGKOK_TZ)

def current_bangkok_naive():
    return now_bangkok().replace(tzinfo=None)

def ensure_bangkok(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Treat naive datetimes from DB as UTC and convert to Bangkok
        return dt.replace(tzinfo=timezone.utc).astimezone(BANGKOK_TZ)
    return dt.astimezone(BANGKOK_TZ)

# --- Data Parsing Helpers ---
def _parse_decimal(value: str):
    if value is None: return None
    cleaned = str(value).replace(',', '').strip()
    if not cleaned: return None
    try: return Decimal(cleaned)
    except (InvalidOperation, ValueError): return None

def _parse_bool(value: str):
    if value is None: return None
    normalized = str(value).strip().lower()
    if normalized in ('yes', 'y', 'true', '1'): return True
    if normalized in ('no', 'n', 'false', '0'): return False
    return None

def _decimal_to_str(value):
    if value is None: return None
    try:
        if isinstance(value, str):
            value = float(value.replace(',', '').strip())
        return format(value, 'f')
    except Exception:
        return str(value)

def _parse_date(value):
    if not value: return None
    text = str(value).strip()
    if not text or text.lower() in ('null', 'none'): return None
    if 'T' in text: text = text.split('T')[0]
    elif ' ' in text: text = text.split(' ')[0]
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%y'):
        try: return datetime.strptime(text, fmt).date()
        except ValueError: continue
    return None

def _clean(value: str):
    if value is None: return None
    text = str(value).strip()
    return text or None

def _date_to_iso(value):
    if value is None: return None
    return value.isoformat()

# --- File Helpers ---
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_image_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# --- Telegram Notification ---
def send_telegram_msg(message):
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8214911655:AAG5RKU6m75AOc3Wws0FqVBqn1CicDLsVWI')
        group_id = os.environ.get('TELEGRAM_GROUP_ID', '-5241471050')
        api_base = os.environ.get('TELEGRAM_API_BASE_URL', 'http://127.0.0.1:3200')
        url = f"{api_base}/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": group_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Telegram Notification Failed: {e}")

# --- Encryption Helpers ---
KEY_FILE = None # Will be set during app initialization if needed, or use env

def get_encryption_key():
    # Attempt to get from env first
    key_str = os.environ.get('ENCRYPTION_KEY', 'Z7wQp9L2Xn5R8vA3mJ6kH1yT4gF0cB9dE5sS8xV2N1M=')
    try:
        return key_str.encode() if isinstance(key_str, str) else key_str
    except Exception:
        return b'Z7wQp9L2Xn5R8vA3mJ6kH1yT4gF0cB9dE5sS8xV2N1M='

# Initialize global cipher suite lazily or using a fixed key to avoid init order issues
_CIPHER_SUITE = None

def get_cipher():
    global _CIPHER_SUITE
    if _CIPHER_SUITE is None:
        _CIPHER_SUITE = Fernet(get_encryption_key())
    return _CIPHER_SUITE

def encrypt_data(data: bytes) -> bytes:
    try:
        return get_cipher().encrypt(data)
    except Exception:
        return data

def decrypt_data(data: bytes) -> bytes:
    try:
        return get_cipher().decrypt(data)
    except Exception:
        return data

# --- Auth Decorator ---
def roles_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                return jsonify({"error": "Unauthorized"}), 403
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

# --- Jinja Filter ---
def bangkok_datetime_filter(value, format='%d-%m-%Y %H:%M'):
    if value is None: return ""
    return ensure_bangkok(value).strftime(format)
