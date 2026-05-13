import { useEffect, useState } from "react";
import { createEvent, getVersion } from "../api";

const SCHEDULE_LABELS = {
  "0d": "Day of event only",
  "1d,0d": "1 day before + day of",
  "3d,1d,0d": "3 days, 1 day before + day of",
};

export default function CreateEventPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [version, setVersion] = useState(null);
  const [success, setSuccess] = useState(null);
  const [schedule, setSchedule] = useState("1d,0d");

  useEffect(() => {
    getVersion().then((v) => setVersion(v.version)).catch(() => {});
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const email = params.get("email");
    if (email) {
      document.getElementById("email").value = email;
    }
  }, []);

  async function handleCreate() {
    const email = document.getElementById("email").value;
    const description = document.getElementById("desc").value;
    const date = document.getElementById("date").value;
    if (!email || !description || !date) return;

    setError(null);
    setLoading(true);
    try {
      const result = await createEvent({ email, description, date, schedule });
      setSuccess(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div>
        <h2>Check your email to confirm</h2>

        {success.schedule_entries && success.schedule_entries.length > 0 && (
          <>
            <p>Scheduled reminders:</p>
            <ul>
              {success.schedule_entries.map((e, i) => (
                <li key={i}>{e.label} — {e.send_at}</li>
              ))}
            </ul>
          </>
        )}

        {(!success.schedule_entries || success.schedule_entries.length === 0) && (
          <p>All reminder dates are in the past — no reminders will be sent.</p>
        )}

        <a href="/">Create another event</a>
      </div>
    );
  }

  return (
    <div>
      <h1>Reminder MVP</h1>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <input id="email" placeholder="email" required />
      <br /><br />
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
      <button type="button" onClick={handleCreate} disabled={loading}>
        {loading ? "Creating..." : "Create Event"}
      </button>

      {version && (
        <p style={{ fontSize: "0.75rem", color: "#999", marginTop: "2rem" }}>
          v{version}
        </p>
      )}
    </div>
  );
}
