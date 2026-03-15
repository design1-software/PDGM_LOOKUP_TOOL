import sys
import types
import os
import pytest

# Set testing env before any app imports
os.environ['TESTING'] = '1'
os.environ['FLASK_ENV'] = 'testing'
os.environ.setdefault('OPENAI_API_KEY', 'test-key')


@pytest.fixture(autouse=True, scope="session")
def _stub_external_modules():
    """Stub openai to avoid real API calls in tests."""
    if "openai" not in sys.modules:
        openai_stub = types.ModuleType("openai")

        class _DummyOpenAI:
            def __init__(self, *args, **kwargs):
                pass

            class chat:
                class completions:
                    @staticmethod
                    def create(*args, **kwargs):
                        class _Resp:
                            class _Choice:
                                class _Msg:
                                    content = "Focus of Care: I10 Essential hypertension A MMTA_OTHER  ICD-10: I10\nDescription: Essential hypertension\nPDGM Group: MMTA - Other\nComorbidity Group: No_group\nPrimary Awarding: 1\nCode First: 0\nBillable: Yes\nReason: Test"

                                message = _Msg()

                            choices = [_Choice()]

                        return _Resp()

        class _DummyError(Exception):
            pass

        openai_stub.OpenAI = _DummyOpenAI
        openai_stub.RateLimitError = _DummyError
        openai_stub.OpenAIError = _DummyError
        sys.modules["openai"] = openai_stub

    yield


@pytest.fixture
def app():
    from app_core import create_app
    from app_core.config import TestingConfig
    application = create_app(TestingConfig)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    from models.user import db as _db
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
