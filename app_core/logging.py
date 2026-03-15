import logging
import json
import sys
import time
import uuid
from flask import g, request

class JsonRequestFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "time": int(time.time() * 1000),
        }
        # Attach request context if available
        try:
            payload.update({
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
                "user_agent": request.user_agent.string if request.user_agent else None,
            })
        except Exception:
            pass
        # Include exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

def setup_structured_logging(app):
    """Add JSON logging to stdout without breaking existing handlers."""
    # Only attach once
    if getattr(app, "_json_logging_attached", False):
        return app

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(JsonRequestFormatter())

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    # Request ID + access logs
    @app.before_request
    def _assign_request_id():
        g.request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())

    @app.after_request
    def _access_log(response):
        try:
            app.logger.info(
                f"{request.method} {request.path} {response.status_code}",
            )
        except Exception:
            pass
        return response

    app._json_logging_attached = True
    return app
