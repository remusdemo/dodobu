from flask import Blueprint, jsonify
from backend.config import Config
from backend.database import get_conn
from backend.models.token import validate_token

tokens_bp = Blueprint("tokens", __name__)


@tokens_bp.route("/api/version")
def version():
    return jsonify({"version": Config.VERSION})


@tokens_bp.route("/api/tokens/<token>")
def check_token(token):
    conn = get_conn()
    try:
        result = validate_token(conn, token)
        return jsonify(result)
    finally:
        conn.close()
