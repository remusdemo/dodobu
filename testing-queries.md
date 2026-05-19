
 http://localhost:5000/testing/home


# Testing queries

## Backdate `event_schedule.sent_at` for a given event id

```sql
UPDATE event_schedule SET send_at = NOW() - INTERVAL '1 day' WHERE event_id = <event_id>;
```

## Backdate `event_link_token.expires_at` for a given event id

```sql
UPDATE event_link_token SET expires_at = NOW() - INTERVAL '1 day' WHERE id = 2;
```
