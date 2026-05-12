import { useEffect, useState } from "react";
import { validateToken, createEventFromToken } from "../api";

export default function TokenEventPage({ token }) {
  const [validation, setValidation] = useState({ loading: true });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(null);

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
      const result = await createEventFromToken(token, { description, date });
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

        <h3>Reminder email will be sent:</h3>
        <p><strong>TO:</strong> {done.reminder_preview.to}</p>
        <p><strong>SUBJECT:</strong> {done.reminder_preview.subject}</p>
        <pre>{done.reminder_preview.body}</pre>
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
      <button type="button" onClick={handleCreate} disabled={submitting}>
        {submitting ? "Creating..." : "Create Event"}
      </button>
    </div>
  );
}
