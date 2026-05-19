"""Process pending scheduled reminders. Run via cron every 5 minutes."""

from datetime import datetime

from backend.config import Config
from backend.database import get_conn
from backend.models.event_schedule import process_pending_schedules

if __name__ == "__main__":
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    conn = get_conn()
    try:
        sent = process_pending_schedules(conn)
        conn.commit()
        if sent:
            print(f"[{now}] Sent {sent} reminder(s)")
        else:
            print(f"[{now}] No pending reminders")
    except Exception as e:
        conn.rollback()
        print(f"[{now}] Worker error: {e}")
        raise
    finally:
        conn.close()
