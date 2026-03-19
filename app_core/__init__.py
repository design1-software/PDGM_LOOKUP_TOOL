"""Application factory for PDGM Lookup Tool MVP."""

import os
from flask import Flask
from models.user import db, User
from .extensions import mail, cache, migrate
from .config import DevelopmentConfig, ProductionConfig, TestingConfig
from .errors import register_error_handlers


def create_app(config=None):
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
    )

    # Load config
    if config:
        app.config.from_object(config)
    elif os.getenv('FLASK_ENV') == 'testing' or os.getenv('TESTING'):
        app.config.from_object(TestingConfig)
    elif os.getenv('FLASK_ENV') == 'production' or os.getenv('ENVIRONMENT') == 'production':
        app.config.from_object(ProductionConfig)
        ProductionConfig.init_app(app)
    else:
        app.config.from_object(DevelopmentConfig)

    # Engine options for PostgreSQL connection health
    engine_opts = app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {})
    engine_opts['pool_pre_ping'] = True

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    cache.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    from blueprints.api import bp as api_bp
    from blueprints.main import bp as main_bp
    from blueprints.recert import bp as recert_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(recert_bp)

    # Register auth blueprint
    from app_core.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    return app
