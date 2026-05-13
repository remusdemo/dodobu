def create_event(conn, account_id, description, event_date, schedule):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO event (account_id, description, event_date, schedule)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (account_id, description, event_date, schedule))
    event_id = cur.fetchone()[0]
    cur.close()
    return event_id


def activate_account_events(conn, account_id):
    cur = conn.cursor()
    cur.execute("""
        UPDATE event SET status = 'active'
        WHERE account_id = %s AND status = 'pending_verification'
    """, (account_id,))
    count = cur.rowcount
    cur.close()
    return count


def get_pending_events(conn, account_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, description, event_date
        FROM event
        WHERE account_id = %s AND status = 'pending_verification'
        ORDER BY id
    """, (account_id,))
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id": r[0],
            "description": r[1],
            "event_date": r[2],
        }
        for r in rows
    ]


def get_event_by_id(conn, event_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT description, event_date
        FROM event
        WHERE id = %s AND deleted_at IS NULL
    """, (event_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {"id": event_id, "description": row[0], "event_date": row[1]}


def soft_delete_event(conn, event_id):
    cur = conn.cursor()
    cur.execute("""
        UPDATE event SET deleted_at = NOW()
        WHERE id = %s AND deleted_at IS NULL
    """, (event_id,))
    deleted = cur.rowcount
    if deleted:
        cur.execute("""
            UPDATE event_schedule SET status = 'skipped'
            WHERE event_id = %s AND status = 'pending'
        """, (event_id,))
    cur.close()
    return deleted > 0


def get_event_with_account(conn, event_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            e.description,
            e.event_date,
            a.email,
            a.id
        FROM event e
        JOIN account a ON a.id = e.account_id
        WHERE e.id=%s
    """, (event_id,))
    row = cur.fetchone()
    cur.close()

    if not row:
        return None

    description, event_date, email, account_id = row
    return {
        "description": description,
        "event_date": event_date,
        "email": email,
        "account_id": account_id,
    }
