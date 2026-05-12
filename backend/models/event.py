def create_event(conn, account_id, description, event_date, next_send_date):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO event (account_id, description, event_date, next_send_date)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (account_id, description, event_date, next_send_date))
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
        SELECT id, description, event_date, next_send_date
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
            "next_send_date": r[3],
        }
        for r in rows
    ]


def get_event_with_account(conn, event_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT
            e.description,
            e.event_date,
            e.next_send_date,
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

    description, event_date, next_send_date, email, account_id = row
    return {
        "description": description,
        "event_date": event_date,
        "next_send_date": next_send_date,
        "email": email,
        "account_id": account_id,
    }
