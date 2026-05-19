import { useEffect, useState } from "react";
import { deleteEvent, getManageEvents, requestSecurityCode, verifyCode } from "../api";

export default function ManagePage({ token, data: mockData }) {
  const [loading, setLoading] = useState(!mockData);
  const [error, setError] = useState(null);
  const [events, setEvents] = useState(mockData?.events || []);
  const [newEventToken, setNewEventToken] = useState(mockData?.new_event_token || null);
  const [needsCode, setNeedsCode] = useState(mockData?.needsCode || false);
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    if (mockData) return;
    getManageEvents(token)
      .then((data) => {
        setEvents(data.events);
        setNewEventToken(data.new_event_token);
        setNeedsCode(false);
      })
      .catch((err) => {
        if (err.status === 404) {
          window.location.href = "/";
          return;
        }
        if (err.status === 401) {
          setNeedsCode(true);
        } else {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [token, mockData]);

  async function handleRequestCode() {
    setSubmitting(true);
    try {
      await requestSecurityCode(token);
      setCodeSent(true);
    } catch (err) {
      setCodeError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyCode() {
    if (code.length !== 4) return;
    setCodeError(null);
    setSubmitting(true);
    try {
      await verifyCode(token, code);
      window.location.reload();
    } catch (err) {
      setCodeError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(eventId, deleteToken) {
    setDeleting(eventId);
    try {
      await deleteEvent(eventId, deleteToken);
      setEvents((prev) => prev.filter((e) => e.id !== eventId));
    } catch (err) {
      // ignore
    } finally {
      setDeleting(null);
    }
  }

  if (loading) return <p>Loading...</p>;

  if (error) {
    window.location.href = "/";
    return null;
  }

  if (needsCode) {
    return (
      <div className="page">
        <h1>Manage your reminders</h1>

        {!codeSent && (
          <>
            <p>This link has expired. Request a security code to continue.</p>
            {codeError && <p className="msg msg-err">{codeError}</p>}
            <button className="btn" type="button" onClick={handleRequestCode} disabled={submitting}>
              {submitting ? "Sending code..." : "Send security code"}
            </button>
          </>
        )}

        {codeSent && (
          <div>
            <p className="msg msg-ok">
              A 4-digit security code has been sent to your email.
            </p>
            <p>Enter the security code (valid for 5 minutes):</p>
            {codeError && <p className="msg msg-err">{codeError}</p>}
            <input
              className="code-input"
              placeholder="0000"
              maxLength={4}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            />
            <button
              className="btn"
              type="button"
              onClick={handleVerifyCode}
              disabled={submitting || code.length !== 4}
              style={{ marginTop: 8 }}
            >
              {submitting ? "Verifying..." : "Verify & Continue"}
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Your reminders</h1>

      {newEventToken && (
        <p style={{ marginBottom: 16 }}>
          <a className="btn" href={`/token/${newEventToken}`}>Create a new event</a>
        </p>
      )}

      {events.length === 0 && <p>No reminders yet.</p>}

      {events.map((e) => (
        <div key={e.id} className="row">
          <span className="row-text">
            <strong>{e.event_date}</strong> —{" "}
            {e.description.length > 300
              ? e.description.slice(0, 300) + "…"
              : e.description}
          </span>
          <button
            className="btn btn-danger"
            type="button"
            onClick={() => handleDelete(e.id, e.delete_token)}
            disabled={deleting === e.id}
            style={{ padding: "4px 10px", fontSize: "12px" }}
          >
            {deleting === e.id ? "..." : "Delete"}
          </button>
        </div>
      ))}
    </div>
  );
}
