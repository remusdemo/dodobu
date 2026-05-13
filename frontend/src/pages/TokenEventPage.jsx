import { useEffect, useState } from "react";
import { validateToken, createEventFromToken } from "../api";

const SCHEDULE_LABELS = {
  "0d": "Day of event only",
  "1d,0d": "1 day before + day of",
  "3d,1d,0d": "3 days, 1 day before + day of",
};

export default function TokenEventPage({ token }) {
  const [validation, setValidation] = useState({ loading: true });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);
  const [schedule, setSchedule] = useState("1d,0d");

  useEffect(() => {
    validateToken(token)
      .then((res) => {
        if (!res.valid) {
          const params = res.email ? `?email=${encodeURIComponent(res.email)}` : "";
          window.location.href = "/" + params;
          return;
        }
        setValidation({ ok: true });
      })
      .catch(() => window.location.href = "/");
  }, [token]);

  async function handleCreate() {
    const description = document.getElementById("desc").value;
    const date = document.getElementById("date").value;
    if (!description || !date) return;

    setError(null);
    setSubmitting(true);
    try {
      const result = await createEventFromToken(token, { description, date, schedule });
      setDone(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (validation.loading) {
    return <p>Validating link...</p>;
  }

  if (done) {
    return (
      <div>
        <h2>Event created!</h2>

        {done.schedule_entries && done.schedule_entries.length > 0 && (
          <>
            <p>Scheduled reminders:</p>
            <ul>
              {done.schedule_entries.map((e, i) => (
                <li key={i}>{e.label} — {e.send_at}</li>
              ))}
            </ul>
          </>
        )}

        <a href="/">Create another event</a>
      </div>
    );
  }

  return (
    <div>
      <h1>Create New Event</h1>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <input id="desc" placeholder="event description" required />
      <br /><br />
      <input id="date" type="date" required />
      <br /><br />
      <select value={schedule} onChange={(e) => setSchedule(e.target.value)}>
        {Object.entries(SCHEDULE_LABELS).map(([key, label]) => (
          <option key={key} value={key}>{label}</option>
        ))}
      </select>
      <br /><br />
      <button type="button" onClick={handleCreate} disabled={submitting}>
        {submitting ? "Creating..." : "Create Event"}
      </button>
    </div>
  );
}
