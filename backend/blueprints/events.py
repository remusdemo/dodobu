import json
import threading
from datetime import date, datetime

from flask import Blueprint, jsonify, request

from backend.config import Config
from backend.database import get_conn
from backend.models.account import find_or_create_account, verify_account_by_token, get_verification_token_by_email
from backend.models.event import create_event, activate_account_events, get_account_events, get_event_by_id, soft_delete_event
from backend.models.event_schedule import build_reminder_email as build_reminder_html, compute_and_insert_schedules, SCHEDULE_OPTIONS
from backend.models.token import create_token, validate_token
from backend.services.email_sender import send_email

events_bp = Blueprint("events", __name__)


def _testing_only(f):
    from functools import wraps
    from flask import abort
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not Config.TESTING_ENABLED:
            abort(404)
        return f(*args, **kwargs)
    return wrapper


def build_verification_email_html(link):
    return f"""<p>Thanks for creating a reminder!</p>
<p>Please verify your email by clicking the link below:</p>
<p><a href="{link}" style="display:inline-block;padding:6px 14px;background:#2980b9;color:#fff;text-decoration:none;border-radius:3px;font-size:14px;">Verify my email</a></p>
<p style="color:#999;font-size:12px;">— MemoBud</p>
"""


def build_validation_email(email, verification_token):
    link = f"{Config.APP_BASE_URL}/verify/{verification_token}"
    return {
        "to": email,
        "subject": "Confirm your email for MemoBud",
        "body": f"""Thanks for creating a reminder!

Please verify your email by clicking the link below:
{link}

—
MemoBud
""",
        "html": build_verification_email_html(link),
    }


def build_reminder_email(email, event, schedule_entries, token):
    schedule_lines = "\n".join(f"  - {e[1]} (sends {e[0].strftime('%Y-%m-%d %H:%M')})" for e in schedule_entries)
    new_link = f"{Config.APP_BASE_URL}/token/{token}"
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

        if not is_new and not is_verified:
            conn.rollback()
            return jsonify({
                "error": "Please verify your email to create more reminders.",
                "needs_verification": True,
                "email": email,
            }), 409

        status = "active" if is_verified else "pending_verification"
        event_id = create_event(conn, account_id, description, event_date, schedule_json, status)
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
                args=(validation_email["to"], validation_email["subject"], validation_email["body"], validation_email["html"]),
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

        # Get email before verification clears the token
        cur = conn.cursor()
        cur.execute(
            "SELECT email FROM account WHERE verification_token = %s AND is_verified = FALSE",
            (token,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return jsonify({"error": "Invalid or already verified"}), 400
        email = row[0]

        account_id = verify_account_by_token(conn, token)
        count = activate_account_events(conn, account_id)

        # Create a manage token and send confirmation email
        manage_token = create_token(conn, account_id, purpose="general")
        manage_url = f"{Config.APP_BASE_URL}/manage/{manage_token}"

        threading.Thread(
            target=send_email,
            args=(
                email,
                "Your email is confirmed — MemoBud",
                f"Your email is confirmed! Manage your events here:\n{manage_url}\n\n—\nMemoBud",
                f"""<p>Your email is confirmed!</p>
<p><a href="{manage_url}" style="display:inline-block;padding:6px 14px;background:#2980b9;color:#fff;text-decoration:none;border-radius:3px;font-size:14px;">Manage your events</a></p>
<p style="color:#999;font-size:12px;">— MemoBud</p>""",
            ),
            daemon=True,
        ).start()

        conn.commit()

        return jsonify({
            "activated": count,
            "account_verified": True,
            "manage_url": manage_url,
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()


@events_bp.route("/api/verify/resend", methods=["POST"])
def resend_verification_route():
    conn = None
    try:
        data = request.get_json()
        email = data.get("email")
        if not email:
            return jsonify({"error": "Email is required"}), 400

        conn = get_conn()
        verification_token = get_verification_token_by_email(conn, email)
        if not verification_token:
            return jsonify({"error": "Email not found or already verified"}), 404

        validation_email = build_validation_email(email, verification_token)
        conn.commit()

        threading.Thread(
            target=send_email,
            args=(validation_email["to"], validation_email["subject"], validation_email["body"], validation_email["html"]),
            daemon=True,
        ).start()

        return jsonify({"sent": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()


@events_bp.route("/testing")
@_testing_only
def testing_home():
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Testing</title></head>
<body style="font-family:sans-serif;max-width:480px;margin:40px auto;">

<h2>Pages</h2>
<h3>Create event</h3>
<ul>
  <li><a href="/">/</a> — create reminder form</li>
  <li><a href="/testing/page/verify">/testing/page/verify</a> — after email verify</li>
</ul>

<h3>Magic token</h3>
<ul>
  <li><a href="/testing/page/token-valid">/testing/page/token-valid</a> — new-event success</li>
  <li><a href="/testing/page/token-expired">/testing/page/token-expired</a> — code entry screen</li>
</ul>

<h3>Manage</h3>
<ul>
  <li><a href="/testing/page/manage-valid">/testing/page/manage-valid</a> — event list</li>
  <li><a href="/testing/page/manage-expired">/testing/page/manage-expired</a> — expired, code entry</li>
</ul>

<h2>Email templates</h2>
<ul>
  <li><a href="/testing/templates?k=reminder-email">/testing/templates?k=reminder-email</a></li>
  <li><a href="/testing/templates?k=verification-email">/testing/templates?k=verification-email</a></li>
  <li><a href="/testing/templates?k=verification-code">/testing/templates?k=verification-code</a></li>
</ul>

</body></html>"""


@events_bp.route("/testing/templates")
@_testing_only
def preview_templates():
    k = request.args.get("k", "reminder-email")

    if k == "reminder-email":
        text, html = build_reminder_html(
            description="Dentist appointment",
            date_str="2026-06-15",
            delete_url="#delete",
            new_url="#new",
            manage_url="#manage",
            remind_url="#remind",
        )
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Reminder Email Preview</title></head>
<body style="font-family:sans-serif;max-width:480px;margin:40px auto;">
  <h3>Subject: Reminder: Dentist appointment</h3>
  <hr>
  {html}
  <hr>
  <details><summary>Plain text</summary><pre>{text}</pre></details>
</body></html>"""

    if k == "verification-email":
        link = f"{Config.APP_BASE_URL}/verify/mock-token-abc123"
        html = build_verification_email_html(link)
        text = build_validation_email("user@example.com", "mock-token-abc123")["body"]
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Verification Email Preview</title></head>
<body style="font-family:sans-serif;max-width:480px;margin:40px auto;">
  <h3>Subject: Confirm your email for MemoBud</h3>
  <hr>
  {html}
  <hr>
  <details><summary>Plain text</summary><pre>{text}</pre></details>
</body></html>"""

    if k == "verification-code":
        code = "4829"
        html = f"""<p>Your security code is:</p>
<h2 style="letter-spacing:6px;font-size:28px;margin:12px 0;">{code}</h2>
<p style="color:#999;font-size:12px;">— MemoBud</p>
"""
        text = f"Your security code is: {code}\n\n—\nMemoBud"
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Security Code Email Preview</title></head>
<body style="font-family:sans-serif;max-width:480px;margin:40px auto;">
  <h3>Subject: Your security code for MemoBud</h3>
  <hr>
  {html}
  <hr>
  <details><summary>Plain text</summary><pre>{text}</pre></details>
</body></html>"""

    return "<p>Unknown template. Use ?k=reminder-email, verification-email, or verification-code</p>", 404


@events_bp.route("/api/events/from-token/<token>", methods=["POST"])
def create_event_from_token(token):
    conn = None
    try:
        data = request.get_json()
        date_str = data["date"]
        schedule_key = data.get("schedule", "1d,0d")

        event_date = validate_event_date(date_str)
        schedule_key = validate_schedule(schedule_key)

        conn = get_conn()

        validation = validate_token(conn, token)
        if not validation["valid"]:
            return jsonify({"error": validation["reason"]}), 400

        if validation.get("purpose") == "remind_again":
            compute_and_insert_schedules(conn, validation["event_id"], event_date, schedule_key)

            cur = conn.cursor()
            cur.execute("SELECT description, event_date FROM event WHERE id = %s", (validation["event_id"],))
            row = cur.fetchone()
            cur.close()

            conn.commit()

            return jsonify({
                "event_id": validation["event_id"],
                "schedule": schedule_key,
                "description": row[0],
                "event_date": row[1].strftime("%Y-%m-%d"),
                "rescheduled": True,
            }), 201

        description = data["description"]
        schedule_json = json.dumps(SCHEDULE_OPTIONS[schedule_key])
        account_id = validation["account_id"]
        is_verified = validation["is_verified"]
        status = "active" if is_verified else "pending_verification"
        event_id = create_event(conn, account_id, description, event_date, schedule_json, status)
        new_token = create_token(conn, account_id, event_id)

        schedule_entries = compute_and_insert_schedules(conn, event_id, event_date, schedule_key)
        manage_token = create_token(conn, account_id, purpose="general")

        conn.commit()

        return jsonify({
            "event_id": event_id,
            "schedule": schedule_key,
            "description": description,
            "event_date": event_date.strftime("%Y-%m-%d"),
            "manage_url": f"{Config.APP_BASE_URL}/manage/{manage_token}",
            "schedule_entries": [
                {"send_at": e[0].isoformat(), "label": e[1]}
                for e in schedule_entries
            ],
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

        if validation.get("purpose") != "delete_event" or validation["event_id"] != event_id:
            return jsonify({"error": "Token not authorized for this action"}), 403

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


@events_bp.route("/api/manage/<token>")
def manage_events(token):
    conn = None
    try:
        conn = get_conn()
        validation = validate_token(conn, token)
        if not validation["valid"]:
            if validation.get("reason") == "not found":
                return jsonify(validation), 404
            return jsonify(validation), 401

        account_id = validation["account_id"]
        events = get_account_events(conn, account_id)

        # Attach a delete_event token to each event
        for e in events:
            cur = conn.cursor()
            cur.execute(
                """SELECT token FROM event_link_token
                   WHERE account_id = %s AND event_id = %s AND purpose = 'delete_event'
                     AND used_at IS NULL
                   LIMIT 1""",
                (account_id, e["id"]),
            )
            row = cur.fetchone()
            cur.close()
            if row:
                e["delete_token"] = row[0]
            else:
                e["delete_token"] = create_token(conn, account_id, e["id"], "delete_event")

        # Reuse or create an account-level new_event token
        cur = conn.cursor()
        cur.execute(
            """SELECT token FROM event_link_token
               WHERE account_id = %s AND purpose = 'new_event' AND event_id IS NULL
                 AND expires_at > NOW() AND used_at IS NULL
               LIMIT 1""",
            (account_id,),
        )
        row = cur.fetchone()
        cur.close()
        new_event_token = row[0] if row else create_token(conn, account_id, purpose="new_event")

        conn.commit()

        return jsonify({
            "email": validation["email"],
            "events": events,
            "new_event_token": new_event_token,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()
