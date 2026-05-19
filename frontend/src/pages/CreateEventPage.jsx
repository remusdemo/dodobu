import { useEffect, useState } from "react";
import { createEvent, getVersion, resendVerification } from "../api";

const SCHEDULE_LABELS = {
  "0d": "Day of event only",
  "1d,0d": "1 day before + day of",
  "7d,3d,0d": "7 days, 3 days before + day of",
};

export default function CreateEventPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [needsVerification, setNeedsVerification] = useState(null);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSent, setResendSent] = useState(false);
  const [version, setVersion] = useState(null);
  const [success, setSuccess] = useState(null);
  const [schedule, setSchedule] = useState("0d");

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
    setNeedsVerification(null);
    setResendSent(false);
    setLoading(true);
    try {
      const result = await createEvent({ email, description, date, schedule });
      setSuccess(result);
    } catch (err) {
      if (err.data?.needs_verification) {
        setNeedsVerification(err.data.email);
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setResendLoading(true);
    setResendSent(false);
    try {
      await resendVerification(needsVerification);
      setResendSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setResendLoading(false);
    }
  }

  if (needsVerification) {
    return (
      <div className="page">
        <h2>Please verify your email to create more reminders.</h2>

        {resendSent && <p className="msg msg-ok">Verification email sent!</p>}
        {error && <p className="msg msg-err">{error}</p>}

        <button className="btn" type="button" onClick={handleResend} disabled={resendLoading}>
          {resendLoading ? "Sending..." : "Resend verification email"}
        </button>

        <br /><br />
        <a className="link" href="/">Back</a>
      </div>
    );
  }

  if (success) {
    if (success.validation_email) {
      return (
        <div className="page">
          <h2>Confirm your email</h2>
          <p>Check your inbox to validate your first reminder and create new ones.</p>
        </div>
      );
    }

    return (
      <div className="page">
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

        <a className="link" href="/">Create another event</a>
      </div>
    );
  }

  return (
    <div className="page">
      <h1><img src="/dodobu.png" alt="" class="home-icon" /> Create a reminder</h1>

      {error && <p className="msg msg-err">{error}</p>}

      <input id="email" placeholder="Email" required />
      <textarea id="desc" placeholder="Event description" required />
      <input id="date" type="date" required />
      <select value={schedule} onChange={(e) => setSchedule(e.target.value)}>
        {Object.entries(SCHEDULE_LABELS).map(([key, label]) => (
          <option key={key} value={key}>{label}</option>
        ))}
      </select>
      <button className="btn" type="button" onClick={handleCreate} disabled={loading} style={{ marginTop: 8 }}>
        {loading ? "Creating..." : "Create Event"}
      </button>

      {version && <p className="version">v{version}</p>}
    </div>
  );
}
