from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import sys

# Initialize extensions without app context to avoid circular imports
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Rate Limiter setup
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
except ImportError:
    class MockLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
        def init_app(self, app):
            pass
    limiter = MockLimiter()
