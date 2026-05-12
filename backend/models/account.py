import uuid


def find_or_create_account(conn, email):
    cur = conn.cursor()

    cur.execute("SELECT id, is_verified, verification_token FROM account WHERE email=%s", (email,))
    acc = cur.fetchone()

    if acc:
        account_id = acc[0]
        is_verified = acc[1]
        verification_token = acc[2]
        is_new = False
    else:
        verification_token = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO account (email, is_verified, verification_token)
            VALUES (%s, FALSE, %s)
            RETURNING id
        """, (email, verification_token))
        account_id = cur.fetchone()[0]
        is_new = True
        is_verified = False

    cur.close()
    return account_id, is_new, is_verified, verification_token


def verify_account_by_token(conn, token):
    cur = conn.cursor()
    cur.execute("""
        UPDATE account
        SET is_verified = TRUE, verification_token = NULL
        WHERE verification_token = %s AND is_verified = FALSE
        RETURNING id
    """, (token,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None
