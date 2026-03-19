import os


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

    # Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///pdgm_dev.db'


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///pdgm.db')

    @staticmethod
    def init_app(app):
        # Fix Heroku/Render postgres:// -> postgresql://
        uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if uri.startswith('postgres://'):
            app.config['SQLALCHEMY_DATABASE_URI'] = uri.replace(
                'postgres://', 'postgresql://', 1
            )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
