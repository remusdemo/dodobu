"""Process pending scheduled reminders. Run via cron every 5 minutes."""

from backend.config import Config
from backend.database import get_conn
from backend.models.event_schedule import process_pending_schedules

if __name__ == "__main__":
    conn = get_conn()
    try:
        sent = process_pending_schedules(conn)
        conn.commit()
        if sent:
            print(f"Sent {sent} reminder(s)")
        else:
            print("No pending reminders")
    except Exception as e:
        conn.rollback()
        print(f"Worker error: {e}")
        raise
    finally:
        conn.close()
