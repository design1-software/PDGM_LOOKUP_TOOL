from flask import Blueprint
bp = Blueprint('referral', __name__)
from . import routes  # noqa: E402,F401
