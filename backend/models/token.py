import uuid
from datetime import datetime, timedelta


def create_token(conn, account_id, event_id=None, purpose="general"):
    cur = conn.cursor()
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=7)

    cur.execute("""
        INSERT INTO event_link_token (account_id, event_id, token, expires_at, purpose)
        VALUES (%s, %s, %s, %s, %s)
    """, (account_id, event_id, token, expires_at, purpose))

    cur.close()
    return token


def validate_token(conn, token):
    cur = conn.cursor()
    cur.execute("""
        SELECT t.account_id, t.event_id, t.expires_at, a.is_verified, a.email, t.purpose,
               e.description
        FROM event_link_token t
        JOIN account a ON a.id = t.account_id
        LEFT JOIN event e ON e.id = t.event_id
        WHERE t.token=%s
    """, (token,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return {"valid": False, "reason": "not found"}

    account_id, event_id, expires_at, is_verified, email, purpose, description = row

    if expires_at < datetime.utcnow():
        return {"valid": False, "reason": "expired", "email": email, "purpose": purpose}

    return {
        "valid": True,
        "account_id": account_id,
        "event_id": event_id,
        "is_verified": is_verified,
        "email": email,
        "purpose": purpose,
        "event_description": description,
    }


def consume_token(conn, token):
    cur = conn.cursor()
    cur.execute("""
        UPDATE event_link_token
        SET used_at = NOW()
        WHERE token = %s
    """, (token,))
    cur.close()


def set_verification_code(conn, token, code):
    cur = conn.cursor()
    cur.execute("""
        UPDATE event_link_token
        SET verification_code = %s, verification_code_expires_at = NOW() + INTERVAL '5 minutes'
        WHERE token = %s
          AND (expires_at > NOW() OR purpose IN ('new_event', 'remind_again', 'general'))
    """, (code, token))
    updated = cur.rowcount
    cur.close()
    return updated > 0


def verify_code_and_consume(conn, token, code):
    cur = conn.cursor()
    cur.execute("""
        SELECT t.account_id, t.event_id, t.purpose, a.email,
               t.expires_at > NOW() AS not_expired,
               t.verification_code_expires_at > NOW() AS code_valid
        FROM event_link_token t
        JOIN account a ON a.id = t.account_id
        WHERE t.token = %s
          AND t.verification_code = %s
    """, (token, code))
    row = cur.fetchone()

    if not row:
        cur.close()
        return None

    account_id, event_id, purpose, email, not_expired, code_valid = row

    if not code_valid:
        cur.close()
        return None

    if not not_expired and purpose not in ("new_event", "remind_again", "general"):
        cur.close()
        return None

    # Valid code renews all account tokens for 3 days
    cur.execute("""
        UPDATE event_link_token SET expires_at = NOW() + INTERVAL '3 days'
        WHERE account_id = %s AND expires_at < NOW()
    """, (account_id,))
    cur.close()
    return {"account_id": account_id, "event_id": event_id, "purpose": purpose, "email": email}
