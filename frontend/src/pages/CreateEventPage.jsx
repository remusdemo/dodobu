import { useEffect, useState } from "react";
import { createEvent, getVersion } from "../api";

export default function CreateEventPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [version, setVersion] = useState(null);
  const [success, setSuccess] = useState(null);

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
      const result = await createEvent({ email, description, date });
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
        <h2>Verify your email to activate the reminder</h2>

        <h3>Validation email sent:</h3>
        <p><strong>TO:</strong> {success.validation_email.to}</p>
        <p><strong>SUBJECT:</strong> {success.validation_email.subject}</p>
        <pre>{success.validation_email.body}</pre>

        <hr />

        <h3>Reminder email (will be sent after verification):</h3>
        <p><strong>TO:</strong> {success.reminder_preview.to}</p>
        <p><strong>SUBJECT:</strong> {success.reminder_preview.subject}</p>
        <pre>{success.reminder_preview.body}</pre>
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
