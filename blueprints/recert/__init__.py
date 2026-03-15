from flask import Blueprint
bp = Blueprint('recert', __name__)
from . import routes  # noqa: E402,F401
