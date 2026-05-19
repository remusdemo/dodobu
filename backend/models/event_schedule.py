from datetime import datetime, timedelta


SCHEDULE_OPTIONS = {
    "0d": [
        {"offset": "0d", "label": "day of"},
    ],
    "1d,0d": [
        {"offset": "-1d", "label": "1 day before"},
        {"offset": "0d", "label": "day of"},
    ],
    "7d,3d,0d": [
        {"offset": "-7d", "label": "7 days before"},
        {"offset": "-3d", "label": "3 days before"},
        {"offset": "0d", "label": "day of"},
    ],
}


def parse_offset(offset_str):
    """Return a timedelta from an offset string like '-3d', '-1d', '0d'."""
    days = int(offset_str.replace("d", ""))
    return timedelta(days=days)


def compute_send_dates(event_date, schedule_key):
    """Return list of (send_at, label) for entries still in the future."""
    entries = SCHEDULE_OPTIONS[schedule_key]
    now = datetime.utcnow()
    result = []
    for entry in entries:
        send_at = event_date + parse_offset(entry["offset"])
        send_at = send_at.replace(hour=9)  # 9 AM so same-day isn't instantly past
        if send_at >= now:
            result.append((send_at, entry["label"]))
    return result


def compute_and_insert_schedules(conn, event_id, event_date, schedule_key):
    """Compute send_at dates from schedule and insert into event_schedule."""
    dates = compute_send_dates(event_date, schedule_key)
    if not dates:
        return []

    cur = conn.cursor()
    for send_at, label in dates:
        cur.execute("""
            INSERT INTO event_schedule (event_id, send_at)
            VALUES (%s, %s)
        """, (event_id, send_at))
    cur.close()
    return dates


def build_reminder_email(description, date_str, delete_url, new_url, manage_url, remind_url=None):
    """Build reminder email text and HTML with action buttons."""
    remind_html = ""
    remind_text = ""
    if remind_url:
        remind_html = f"""
  <a href="{remind_url}"
     style="display:inline-block;padding:4px 10px;margin:2px;background:#27ae60;color:#fff;text-decoration:none;border-radius:3px;font-size:13px;">
    Remind me again
  </a>"""
        remind_text = f"\nRemind me again: {remind_url}"

    text = f""""{description}" due for {date_str}
{remind_text}
Delete this event: {delete_url}
Create a new event: {new_url}
Manage your events: {manage_url}

—
MemoBud
"""
    html = f"""<p style="background:#f0f0f0;padding:12px 16px;font-size:18px;border-radius:4px;">{description}</p>
<p style="color:#666;">due date: <strong>{date_str}</strong></p>
<br><br>
<p>
  <a href="{delete_url}"
     style="display:inline-block;padding:4px 10px;margin:2px;background:#c0392b;color:#fff;text-decoration:none;border-radius:3px;font-size:13px;">
    Delete this event
  </a>
  <a href="{new_url}"
     style="display:inline-block;padding:4px 10px;margin:2px;background:#2980b9;color:#fff;text-decoration:none;border-radius:3px;font-size:13px;">
    Create a new event
  </a>{remind_html}
</p>
<p style="margin-top:16px;">
  <a href="{manage_url}" style="color:#999;font-size:12px;">Manage your events</a>
</p>
<p style="color:#999;font-size:12px;">— MemoBud</p>
"""
    return text, html


def process_pending_schedules(conn, limit=5000):
    """Send reminders for pending schedule entries that are due.

    Uses FOR UPDATE SKIP LOCKED so multiple workers can run concurrently
    without stepping on each other. Limited to avoid unbounded runs.
    """
    from backend.config import Config
    from backend.services.email_sender import send_email
    from backend.models.token import create_token

    cur = conn.cursor()
    cur.execute("""
        SELECT
            es.id,
            es.event_id,
            e.description,
            e.event_date,
            a.email,
            a.id,
            NOT EXISTS (
                SELECT 1 FROM event_schedule es2
                WHERE es2.event_id = e.id
                  AND es2.status = 'pending'
                  AND es2.id != es.id
            ) AS is_last
        FROM event_schedule es
        JOIN event e ON e.id = es.event_id
        JOIN account a ON a.id = e.account_id
        WHERE es.send_at <= NOW()
          AND es.status = 'pending'
          AND e.deleted_at IS NULL
        ORDER BY es.send_at
        FOR UPDATE SKIP LOCKED
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()

    for row in rows:
        schedule_id, event_id, description, event_date, email, account_id, is_last = row

        new_token = create_token(conn, account_id, purpose="new_event")
        delete_token = create_token(conn, account_id, event_id, "delete_event")
        manage_token = create_token(conn, account_id, purpose="general")

        base = Config.APP_BASE_URL
        date_str = event_date.strftime("%Y-%m-%d")

        remind_url = None
        if is_last:
            remind_token = create_token(conn, account_id, event_id, "remind_again")
            remind_url = f"{base}/token/{remind_token}"

        text, html = build_reminder_email(
            description,
            date_str,
            f"{base}/event/{event_id}/delete?token={delete_token}",
            f"{base}/token/{new_token}",
            f"{base}/manage/{manage_token}",
            remind_url,
        )

        send_email(
            email,
            f"Reminder: {description}",
            text,
            html,
        )

    if rows:
        ids = [r[0] for r in rows]
        cur.execute("""
            UPDATE event_schedule SET status = 'sent', sent_at = NOW()
            WHERE id = ANY(%s)
        """, (ids,))

    cur.close()
    return len(rows)
