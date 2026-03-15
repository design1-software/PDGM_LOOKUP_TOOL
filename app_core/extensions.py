"""Centralized extension objects for the PDGM Tool MVP."""

from flask_login import LoginManager
from flask_mail import Mail
from flask_caching import Cache
from flask_migrate import Migrate

login_manager = LoginManager()
mail = Mail()
cache = Cache()
migrate = Migrate()
