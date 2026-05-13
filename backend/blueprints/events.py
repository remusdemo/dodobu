import json
import threading
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from backend.config import Config
from backend.database import get_conn
from backend.models.account import find_or_create_account, verify_account_by_token
from backend.models.event import create_event, activate_account_events, get_event_by_id, soft_delete_event, get_event_with_account
from backend.models.event_schedule import compute_and_insert_schedules, SCHEDULE_OPTIONS
from backend.models.token import create_token, consume_token, validate_token
from backend.services.email_sender import send_email

events_bp = Blueprint("events", __name__)


def build_validation_email(email, verification_token):
    link = f"{Config.APP_BASE_URL}/verify/{verification_token}"
    return {
        "to": email,
        "subject": "Confirm your email for MemoBud",
        "body": f"""
Thanks for creating a reminder!

Please verify your email by clicking the link below:
{link}

This link expires in 48 hours.
""",
    }


def build_reminder_email(email, event, schedule_entries, token):
    schedule_lines = "\n".join(f"  - {e[1]} (sends {e[0].strftime('%Y-%m-%d %H:%M')})" for e in schedule_entries)
    new_link = f"{Config.APP_BASE_URL}/event/new/{token}"
    delete_link = f"{Config.APP_BASE_URL}/event/{event['id']}/delete?token={token}"
    return {
        "to": email,
        "subject": f"Reminder: {event['description']}",
        "body": f"""
Reminder Event

Description: {event['description']}
Event date: {event['event_date']}

Scheduled reminders:
{schedule_lines}

---

Create a new event:
{new_link}

Delete this event:
{delete_link}

⚠ Links expire in 48 hours
""",
    }


def validate_event_date(date_str):
    event_date = datetime.strptime(date_str, "%Y-%m-%d")
    if event_date.date() < date.today():
        raise ValueError("Event date cannot be in the past")
    return event_date


def validate_schedule(schedule_key):
    if schedule_key not in SCHEDULE_OPTIONS:
        raise ValueError(f"Invalid schedule option: {schedule_key}")
    return schedule_key


@events_bp.route("/api/events", methods=["POST"])
def create_event_route():
    conn = None
    try:
        data = request.get_json()
        email = data["email"]
        description = data["description"]
        date_str = data["date"]
        schedule_key = data.get("schedule", "1d,0d")

        event_date = validate_event_date(date_str)
        schedule_key = validate_schedule(schedule_key)
        schedule_json = json.dumps(SCHEDULE_OPTIONS[schedule_key])

        conn = get_conn()

        account_id, is_new, is_verified, verification_token = find_or_create_account(conn, email)
        event_id = create_event(conn, account_id, description, event_date, schedule_json)
        event_token = create_token(conn, account_id, event_id)

        schedule_entries = compute_and_insert_schedules(conn, event_id, event_date, schedule_key)

        validation_email = None
        if not is_verified and verification_token:
            validation_email = build_validation_email(email, verification_token)

        reminder_preview = build_reminder_email(email, {
            "id": event_id,
            "description": description,
            "event_date": event_date,
        }, schedule_entries, event_token)

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
            "schedule": schedule_key,
            "schedule_entries": [
                {"send_at": e[0].isoformat(), "label": e[1]}
                for e in schedule_entries
            ],
            "validation_email": validation_email,
            "reminder_preview": reminder_preview,
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
        schedule_key = data.get("schedule", "1d,0d")

        event_date = validate_event_date(date_str)
        schedule_key = validate_schedule(schedule_key)
        schedule_json = json.dumps(SCHEDULE_OPTIONS[schedule_key])

        conn = get_conn()

        validation = validate_token(conn, token)
        if not validation["valid"]:
            return jsonify({"error": validation["reason"]}), 400

        account_id = validation["account_id"]
        event_id = create_event(conn, account_id, description, event_date, schedule_json)
        new_token = create_token(conn, account_id, event_id)
        consume_token(conn, token)

        schedule_entries = compute_and_insert_schedules(conn, event_id, event_date, schedule_key)

        reminder_preview = build_reminder_email(
            validation["email"],
            {
                "id": event_id,
                "description": description,
                "event_date": event_date,
            },
            schedule_entries,
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
            "schedule": schedule_key,
            "schedule_entries": [
                {"send_at": e[0].isoformat(), "label": e[1]}
                for e in schedule_entries
            ],
            "reminder_preview": reminder_preview,
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


@events_bp.route("/api/events/<int:event_id>")
def get_event_route(event_id):
    conn = None
    try:
        token = request.args.get("token")
        if not token:
            return jsonify({"error": "Missing token"}), 400

        conn = get_conn()

        validation = validate_token(conn, token)
        if not validation["valid"]:
            return jsonify({"error": validation["reason"]}), 400

        if validation["event_id"] != event_id:
            return jsonify({"error": "Token does not match event"}), 403

        event = get_event_by_id(conn, event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404

        return jsonify(event)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()


@events_bp.route("/api/events/<int:event_id>/delete", methods=["POST"])
def delete_event_route(event_id):
    conn = None
    try:
        data = request.get_json()
        token = data.get("token") if data else None
        if not token:
            return jsonify({"error": "Missing token"}), 400

        conn = get_conn()

        validation = validate_token(conn, token)
        if not validation["valid"]:
            return jsonify({"error": validation["reason"]}), 400

        if validation["event_id"] != event_id:
            return jsonify({"error": "Token does not match event"}), 403

        deleted = soft_delete_event(conn, event_id)
        if not deleted:
            return jsonify({"error": "Event not found or already deleted"}), 404

        conn.commit()

        return jsonify({"deleted": True})

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
    try:
        conn = get_conn()

        event = get_event_with_account(conn, event_id)
        if not event:
            return jsonify({"error": "Event not found"}), 404

        event["id"] = event_id
        token = create_token(conn, event["account_id"], event_id)
        email_payload = build_reminder_email(event["email"], event, [], token)

        conn.commit()

        return jsonify(email_payload)

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()
