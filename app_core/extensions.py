"""Centralized extension objects for the PDGM Tool MVP."""

from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

login_manager = LoginManager()
mail = Mail()
cache = Cache()
migrate = Migrate()
import os
_redis_url = os.getenv("REDIS_URL") or os.getenv("REDISCLOUD_URL")
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri=_redis_url if _redis_url else "memory://",
)
