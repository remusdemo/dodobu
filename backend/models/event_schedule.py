from datetime import datetime, timedelta


SCHEDULE_OPTIONS = {
    "0d": [
        {"offset": "0d", "label": "day of"},
    ],
    "1d,0d": [
        {"offset": "-1d", "label": "1 day before"},
        {"offset": "0d", "label": "day of"},
    ],
    "3d,1d,0d": [
        {"offset": "-3d", "label": "3 days before"},
        {"offset": "-1d", "label": "1 day before"},
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


def process_pending_schedules(conn, limit=5000):
    """Send reminders for pending schedule entries that are due.

    Uses FOR UPDATE SKIP LOCKED so multiple workers can run concurrently
    without stepping on each other. Limited to avoid unbounded runs.
    """
    from backend.services.email_sender import send_email

    cur = conn.cursor()
    cur.execute("""
        SELECT
            es.id,
            es.event_id,
            e.description,
            e.event_date,
            a.email
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
        schedule_id, event_id, description, event_date, email = row
        send_email(
            email,
            f"Reminder: {description}",
            f"""Your reminder for "{description}" on {event_date.strftime('%Y-%m-%d')} is here.

—
MemoBud
""",
        )

    if rows:
        ids = [r[0] for r in rows]
        cur.execute("""
            UPDATE event_schedule SET status = 'sent', sent_at = NOW()
            WHERE id = ANY(%s)
        """, (ids,))

    cur.close()
    return len(rows)
