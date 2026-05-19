# Dodobu — flow design & code pointers

## A. First reminder + email verification

### Product design
1. User lands on `/` and fills the form (email, description, date, schedule).
2. **New email** → event `pending_verification`, verification email sent, UI shows "Check your email to confirm".
3. **Existing verified** → event `active`, no verification email.
4. **Existing unverified** → API returns 409, UI shows "Please verify your email to create more reminders" + resend button.
5. User clicks verification link (`/verify/<token>`) → `VerifyPage` → `POST /api/verify/<token>` → account verified, all `pending_verification` events flip to `active`.

### Code pointers

| Layer | File | Key symbols |
|-------|------|-------------|
| Frontend page | `frontend/src/pages/CreateEventPage.jsx` | `handleCreate()`, `handleResend()`, `needsVerification` / `success` states |
| Frontend API | `frontend/src/api.js` | `createEvent()`, `resendVerification()`, `verifyAccount()` |
| Routing | `frontend/src/App.jsx:23` | `/` renders `<CreateEventPage />` |
| Backend route | `backend/blueprints/events.py:77` | `create_event_route()` — `POST /api/events` |
| Backend route | `backend/blueprints/events.py:154` | `verify_account_route()` — `POST /api/verify/<token>` |
| Backend route | `backend/blueprints/events.py:183` | `resend_verification_route()` — `POST /api/verify/resend` |
| Account model | `backend/models/account.py` | `find_or_create_account()`, `verify_account_by_token()` |
| Event model | `backend/models/event.py:1` | `create_event()` — status defaults to `"pending_verification"` |
| Event model | `backend/models/event.py:13` | `activate_account_events()` — flips pending → active |
| Email template | `backend/blueprints/events.py:18` | `build_validation_email()` |

---

## B. Send reminder by worker

### Product design
1. Cron runs `python worker.py` every ~5 min.
2. Queries `event_schedule` where `send_at <= NOW()` and `status = 'pending'` (active, non-deleted events). Uses `FOR UPDATE SKIP LOCKED`.
3. Builds reminder email with 3 buttons:
   - **Delete this event** — `/event/<id>/delete?token=…` (purpose `delete_event`)
   - **Create a new event** — `/token/<token>` (purpose `new_event`)
   - **Remind me again** — `/token/<token>` (purpose `remind_again`, only on the **last** pending schedule for that event)
4. Sends via Resend, marks schedule as `sent`.

### Code pointers

| Layer | File | Key symbols |
|-------|------|-------------|
| Worker entry | `worker.py` | `process_pending_schedules(conn)` |
| Schedule model | `backend/models/event_schedule.py:55` | `process_pending_schedules()` |
| Token model | `backend/models/token.py:5` | `create_token()` — TTL = 7 days |
| Schedule options | `backend/models/event_schedule.py:4` | `SCHEDULE_OPTIONS` |
| Email sender | `backend/services/email_sender.py` | `send_email()` via Resend |

---

## C. "Create a new event" — valid token

### Product design
1. User clicks "Create a new event" in reminder email → `/token/<token>` (purpose `new_event`).
2. Token is **valid**. `MagicTokenPage`: `isDirect = true` — no verification code.
3. User fills description, date, schedule → clicks "Create Event".
4. Event created. Status = `active` if account verified, else `pending_verification`.
5. Token is **not consumed** — same link works repeatedly. UI shows "Event created!".

### Code pointers

| Layer | File | Key symbols |
|-------|------|-------------|
| Frontend page | `frontend/src/pages/MagicTokenPage.jsx` | `isDirect = info?.valid` (line 123), `handleCreateDirect()` (line 54), `validateForm()` (line 45) |
| Frontend API | `frontend/src/api.js:27` | `createEventFromToken()` → `POST /api/events/from-token/<token>` |
| Routing | `frontend/src/App.jsx:21` | `/token/<token>` → `<MagicTokenPage />` |
| Backend route | `backend/blueprints/events.py:219` | `create_event_from_token()` — no email sent, token not consumed |
| Token validation | `backend/models/token.py:19` | `validate_token()` — checks `expires_at > NOW()` only, no `used_at` |

---

## D. "Create a new event" — expired token

### Product design
1. User clicks "Create a new event" → token is **expired** (`valid: false, reason: "expired"`).
2. `isDirect = false` → verification code flow.
3. User fills description, date, schedule → clicks "Create Event" → 4-digit code emailed.
4. UI shows code input. User enters code → clicks "Verify & Create".
5. Backend verifies code. Expired tokens with `new_event`/`remind_again` purpose are accepted — code proves email ownership.
6. **Valid code renews the token** (`expires_at` extended by 7 days).
7. Event created as `active`. UI shows "Event created!".

### Code pointers

| Layer | File | Key symbols |
|-------|------|-------------|
| Frontend page | `frontend/src/pages/MagicTokenPage.jsx` | `handleRequestCode()` (line 68), `handleCreateWithCode()` (line 82), `formError` state |
| Frontend API | `frontend/src/api.js:67` | `requestSecurityCode(token)` |
| Frontend API | `frontend/src/api.js:71` | `createEventWithCode(token, {…})` |
| Backend — request code | `backend/blueprints/tokens.py:46` | `request_code()` — accepts `reason="expired"` for `new_event`/`remind_again` |
| Backend — create with code | `backend/blueprints/tokens.py:86` | `create_event_from_magic_token()` |
| Token — set code | `backend/models/token.py:61` | `set_verification_code()` — no `used_at` check |
| Token — verify & renew | `backend/models/token.py:74` | `verify_code_and_consume()` — skips expiry for `new_event`/`remind_again`, renews `expires_at` +7d |
| Code email | `backend/blueprints/tokens.py:37` | `_send_verification_code()` |

---

## E. "Remind me again" — valid token

### Product design
Same as C, but `purpose="remind_again"`. Heading says "Remind me again", description is read-only (reuses original event description). User picks date + schedule → clicks "Remind me again" → direct create.

### Code pointers

| Layer | File | Key symbols |
|-------|------|-------------|
| Frontend page | `frontend/src/pages/MagicTokenPage.jsx` | `isRemind` (line 125), `isDirect = true`, `handleCreateDirect()` |
| Token creation | `backend/models/event_schedule.py:104` | `create_token(…, "remind_again")` — only on `is_last` |
| Backend route | `backend/blueprints/events.py:219` | `create_event_from_token()` — same as flow C |

---

## F. "Remind me again" — expired token

### Product design
Same as D, but `purpose="remind_again"`. Heading says "Remind me again", description is read-only. Expired → verification code → code renews token → event created as `active`.

### Code pointers

| Layer | File | Key symbols |
|-------|------|-------------|
| Frontend page | `frontend/src/pages/MagicTokenPage.jsx` | `isDirect = false`, `isRemind = true`, `handleRequestCode()` → `handleCreateWithCode()` |
| Backend | `backend/blueprints/tokens.py:46` | `request_code()` — accepts expired `remind_again` |
| Backend | `backend/models/token.py:74` | `verify_code_and_consume()` — renews expiry on valid code |

---

## Key design rules

- **Tokens are reusable** — no `used_at` checks anywhere. Same link can create multiple events.
- **Valid token** = direct create. **Expired token** = verification code then create.
- **Code renewal**: a valid code extends `expires_at` by 7 days (not at request time).
- **Worker emails only**: no reminder emails sent outside `process_pending_schedules`. The `create_event_from_token` endpoint does not send email.
- **Date validation**: client-side via `validateForm()` + `min` on `<input type="date">`, server-side via `validate_event_date()`.
- **Form errors stay on form**: submission errors use `formError` state (not `error`) so the form remains visible.
