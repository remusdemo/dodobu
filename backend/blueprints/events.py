import threading
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from backend.config import Config
from backend.database import get_conn
from backend.models.account import find_or_create_account, verify_account_by_token
from backend.models.event import create_event, activate_account_events, get_event_with_account
from backend.models.token import create_token, consume_token, validate_token
from backend.services.email_sender import send_email

events_bp = Blueprint("events", __name__)


def compute_next_send(event_date):
    return event_date - timedelta(days=1)


def build_validation_email(email, verification_token):
    link = f"{Config.APP_BASE_URL}/verify/{verification_token}"
    return {
        "to": email,
        "subject": "Verify your email for Reminder MVP",
        "body": f"""
Thanks for creating a reminder!

Please verify your email by clicking the link below:
{link}

This link expires in 48 hours.
""",
    }


def build_reminder_email(email, event, token):
    link = f"{Config.APP_BASE_URL}/event/new/{token}"
    return {
        "to": email,
        "subject": f"Reminder: {event['description']}",
        "body": f"""
Reminder Event

Description: {event['description']}
Event date: {event['event_date']}
Next reminder: {event['next_send_date']}

---

Create a new event:
{link}

⚠ This link expires in 48 hours
""",
    }


@events_bp.route("/api/events", methods=["POST"])
def create_event_route():
    conn = None
    cur = None
    try:
        data = request.get_json()
        email = data["email"]
        description = data["description"]
        date_str = data["date"]

        event_date = datetime.strptime(date_str, "%Y-%m-%d")
        next_send_date = compute_next_send(event_date)

        conn = get_conn()

        account_id, is_new, is_verified, verification_token = find_or_create_account(conn, email)
        event_id = create_event(conn, account_id, description, event_date, next_send_date)
        event_token = create_token(conn, account_id, event_id)

        validation_email = None
        if not is_verified and verification_token:
            validation_email = build_validation_email(email, verification_token)

        reminder_preview = build_reminder_email(email, {
            "description": description,
            "event_date": event_date,
            "next_send_date": next_send_date,
        }, event_token)

        conn.commit()

        if validation_email:
            threading.Thread(
                target=send_email,
                args=(validation_email["to"], validation_email["subject"], validation_email["body"]),
                daemon=True,
            ).start()

        return jsonify({
            "event_id": event_id,
            "token": event_token,
            "validation_email": validation_email,
            "reminder_preview": reminder_preview,
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@events_bp.route("/api/verify/<token>", methods=["POST"])
def verify_account_route(token):
    conn = None
    try:
        conn = get_conn()

        account_id = verify_account_by_token(conn, token)
        if not account_id:
            return jsonify({"error": "Invalid or already verified"}), 400

        count = activate_account_events(conn, account_id)

        conn.commit()

        return jsonify({
            "activated": count,
            "account_verified": True,
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()


@events_bp.route("/api/events/from-token/<token>", methods=["POST"])
def create_event_from_token(token):
    conn = None
    try:
        data = request.get_json()
        description = data["description"]
        date_str = data["date"]
        event_date = datetime.strptime(date_str, "%Y-%m-%d")
        next_send_date = compute_next_send(event_date)

        conn = get_conn()

        validation = validate_token(conn, token)
        if not validation["valid"]:
            return jsonify({"error": validation["reason"]}), 400

        account_id = validation["account_id"]
        event_id = create_event(conn, account_id, description, event_date, next_send_date)
        new_token = create_token(conn, account_id, event_id)
        consume_token(conn, token)

        reminder_preview = build_reminder_email(
            validation["email"],
            {
                "description": description,
                "event_date": event_date,
                "next_send_date": next_send_date,
            },
            new_token,
        )

        conn.commit()

        if reminder_preview:
            threading.Thread(
                target=send_email,
                args=(reminder_preview["to"], reminder_preview["subject"], reminder_preview["body"]),
                daemon=True,
            ).start()

        return jsonify({
            "event_id": event_id,
            "reminder_preview": reminder_preview,
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()


@events_bp.route("/api/events/<int:event_id>/preview")
def preview_event(event_id):
    conn = None
    cur = None
    try:
        conn = get_conn()

        event = get_event_with_account(conn, event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404

        token = create_token(conn, event["account_id"], event_id)
        email_payload = build_reminder_email(event["email"], event, token)

        conn.commit()

        return jsonify(email_payload)

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
