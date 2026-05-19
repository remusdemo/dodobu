import json
import random
import threading
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from backend.config import Config
from backend.database import get_conn
from backend.models.event import create_event
from backend.models.event_schedule import compute_and_insert_schedules, SCHEDULE_OPTIONS
from backend.models.token import (
    create_token,
    set_verification_code,
    validate_token,
    verify_code_and_consume,
)
from backend.services.email_sender import send_email

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


def _send_verification_code(email, code):
    text = f"Your security code is: {code}\n\n—\nMemoBud"
    html = f"""<p>Your security code is:</p>
<h2 style="letter-spacing:6px;font-size:28px;margin:12px 0;">{code}</h2>
<p style="color:#999;font-size:12px;">— MemoBud</p>
"""
    send_email(email, "Your security code for MemoBud", text, html)


@tokens_bp.route("/api/tokens/<token>/request-code", methods=["POST"])
def request_code(token):
    conn = None
    try:
        conn = get_conn()

        validation = validate_token(conn, token)

        # Expired is ok for new_event/remind_again/general — code proves email ownership
        if not validation["valid"] and validation.get("reason") != "expired":
            return jsonify({"error": validation["reason"]}), 400

        purpose = validation.get("purpose")
        if purpose not in ("new_event", "remind_again", "general"):
            return jsonify({"error": "Code verification not available for this token"}), 400

        code = f"{random.randint(0, 9999):04d}"
        if not set_verification_code(conn, token, code):
            return jsonify({"error": "Token is no longer valid"}), 400

        conn.commit()

        threading.Thread(
            target=_send_verification_code,
            args=(validation["email"], code),
            daemon=True,
        ).start()

        return jsonify({"code_sent": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()


@tokens_bp.route("/api/tokens/<token>/create-event", methods=["POST"])
def create_event_from_magic_token(token):
    conn = None
    try:
        data = request.get_json()
        code = data.get("code")
        if not code:
            return jsonify({"error": "Security code is required"}), 400

        date_str = data.get("date")
        schedule_key = data.get("schedule", "1d,0d")

        if not date_str:
            return jsonify({"error": "Date is required"}), 400

        event_date = datetime.strptime(date_str, "%Y-%m-%d")
        if event_date.date() < date.today():
            return jsonify({"error": "Event date cannot be in the past"}), 400

        if schedule_key not in SCHEDULE_OPTIONS:
            return jsonify({"error": f"Invalid schedule option: {schedule_key}"}), 400

        conn = get_conn()

        verified = verify_code_and_consume(conn, token, code)
        if not verified:
            return jsonify({"error": "Invalid or expired security code"}), 400

        if verified["purpose"] == "remind_again":
            compute_and_insert_schedules(conn, verified["event_id"], event_date, schedule_key)

            cur = conn.cursor()
            cur.execute("SELECT description, event_date FROM event WHERE id = %s", (verified["event_id"],))
            row = cur.fetchone()
            cur.close()

            conn.commit()

            return jsonify({
                "event_id": verified["event_id"],
                "schedule": schedule_key,
                "description": row[0],
                "event_date": row[1].strftime("%Y-%m-%d"),
                "rescheduled": True,
            }), 201

        description = data.get("description")
        if not description:
            return jsonify({"error": "Description is required"}), 400

        schedule_json = json.dumps(SCHEDULE_OPTIONS[schedule_key])
        account_id = verified["account_id"]
        event_id = create_event(conn, account_id, description, event_date, schedule_json, "active")
        compute_and_insert_schedules(conn, event_id, event_date, schedule_key)
        manage_token = create_token(conn, account_id, purpose="general")

        conn.commit()

        return jsonify({
            "event_id": event_id,
            "schedule": schedule_key,
            "description": description,
            "event_date": event_date.strftime("%Y-%m-%d"),
            "manage_url": f"{Config.APP_BASE_URL}/manage/{manage_token}",
        }), 201

    except (ValueError, KeyError) as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()


@tokens_bp.route("/api/tokens/<token>/verify-code", methods=["POST"])
def verify_code(token):
    conn = None
    try:
        data = request.get_json()
        code = data.get("code") if data else None
        if not code:
            return jsonify({"error": "Security code is required"}), 400

        conn = get_conn()
        verified = verify_code_and_consume(conn, token, code)
        if not verified:
            return jsonify({"error": "Invalid or expired security code"}), 400

        conn.commit()
        return jsonify({"verified": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()
