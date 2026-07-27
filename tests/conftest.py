import sys
import types
import os
import pytest

# Set testing env before any app imports
os.environ['TESTING'] = '1'
os.environ['FLASK_ENV'] = 'testing'
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-key')


@pytest.fixture(autouse=True, scope="session")
def _stub_external_modules():
    """Stub anthropic to avoid real API calls in tests."""
    if "anthropic" not in sys.modules:
        anthropic_stub = types.ModuleType("anthropic")

        _DUMMY_RESPONSE_TEXT = (
            "Focus of Care: I10 Essential hypertension A MMTA_OTHER  ICD-10: I10\n"
            "Description: Essential hypertension\n"
            "PDGM Group: MMTA - Other\n"
            "Comorbidity Group: No_group\n"
            "Primary Awarding: 1\n"
            "Code First: 0\n"
            "Billable: Yes\n"
            "Reason: Test"
        )

        class _ContentBlock:
            def __init__(self):
                self.text = _DUMMY_RESPONSE_TEXT

        class _DummyMessages:
            def create(self, *args, **kwargs):
                class _Resp:
                    content = [_ContentBlock()]
                return _Resp()

        class _DummyAnthropic:
            def __init__(self, *args, **kwargs):
                self.messages = _DummyMessages()

        class _DummyError(Exception):
            pass

        anthropic_stub.Anthropic = _DummyAnthropic
        anthropic_stub.RateLimitError = _DummyError
        anthropic_stub.APIError = _DummyError
        sys.modules["anthropic"] = anthropic_stub

    yield


@pytest.fixture
def app():
    from app_core import create_app
    from app_core.config import TestingConfig
    application = create_app(TestingConfig)
    yield application


@pytest.fixture
def anon_client(app):
    """A client that has NOT completed the lead-capture gate.

    Use this to assert the gate itself behaves; every other test wants
    ``client``.
    """
    return app.test_client()


@pytest.fixture
def client(app):
    """A client past the lead-capture gate.

    Most API routes are wrapped in @require_lead_capture, which 403s unless
    ``lead_captured`` is in the session. Without this the endpoint tests only
    ever exercised the gate and never reached the handlers they were written
    to cover.
    """
    test_client = app.test_client()
    with test_client.session_transaction() as sess:
        sess['lead_captured'] = True
        sess['lead_email'] = 'test@example.com'
        sess['lead_name'] = 'Test User'
    return test_client


@pytest.fixture
def db(app):
    from models.user import db as _db
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
