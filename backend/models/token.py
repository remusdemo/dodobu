import uuid
from datetime import datetime, timedelta


def create_token(conn, account_id, event_id):
    cur = conn.cursor()
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=48)

    cur.execute("""
        INSERT INTO event_link_token (account_id, event_id, token, expires_at)
        VALUES (%s, %s, %s, %s)
    """, (account_id, event_id, token, expires_at))

    cur.close()
    return token


def validate_token(conn, token):
    cur = conn.cursor()
    cur.execute("""
        SELECT t.account_id, t.event_id, t.expires_at, t.used_at, a.is_verified, a.email
        FROM event_link_token t
        JOIN account a ON a.id = t.account_id
        WHERE t.token=%s
    """, (token,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return {"valid": False, "reason": "not found"}

    account_id, event_id, expires_at, used_at, is_verified, email = row

    if used_at:
        return {"valid": False, "reason": "already used", "email": email}

    if expires_at < datetime.utcnow():
        return {"valid": False, "reason": "expired", "email": email}

    return {"valid": True, "account_id": account_id, "event_id": event_id, "is_verified": is_verified, "email": email}


def consume_token(conn, token):
    cur = conn.cursor()
    cur.execute("""
        UPDATE event_link_token
        SET used_at = NOW()
        WHERE token = %s
    """, (token,))
    cur.close()
