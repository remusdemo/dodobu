import { useEffect, useState } from "react";
import {
  validateToken,
  requestSecurityCode,
  createEventWithCode,
  createEventFromToken,
} from "../api";

const SCHEDULE_LABELS = {
  "0d": "Day of event only",
  "1d,0d": "1 day before + day of",
  "3d,1d,0d": "3 days, 1 day before + day of",
};

export default function MagicTokenPage({ token, data: mockData }) {
  const [loading, setLoading] = useState(!mockData);
  const [error, setError] = useState(null);
  const [formError, setFormError] = useState(null);
  const [info, setInfo] = useState(mockData?.info || null);
  const [schedule, setSchedule] = useState("0d");
  const [date, setDate] = useState(mockData?.date || "");
  const [description, setDescription] = useState(mockData?.description || "");
  const [codeSent, setCodeSent] = useState(mockData?.codeSent || false);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(mockData?.success || null);

  useEffect(() => {
    if (mockData) return;
    validateToken(token)
      .then((data) => {
        if (!data.valid && data.reason !== "expired") {
          window.location.href = "/";
          return;
        }
        if (data.purpose === "delete_event") {
          window.location.href = `/event/${data.event_id}/delete?token=${token}`;
          return;
        }
        setInfo(data);
        if (data.purpose === "remind_again" && data.event_description) {
          setDescription(data.event_description);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, mockData]);

  function validateForm() {
    if (!description || !date) return false;
    if (date < new Date().toISOString().slice(0, 10)) {
      setFormError("Event date cannot be in the past");
      return false;
    }
    return true;
  }

  async function handleCreateDirect() {
    if (!validateForm()) return;
    setFormError(null);
    setSubmitting(true);
    try {
      const result = await createEventFromToken(token, { description, date, schedule });
      setSuccess(result);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRequestCode() {
    if (!validateForm()) return;
    setFormError(null);
    setSubmitting(true);
    try {
      await requestSecurityCode(token);
      setCodeSent(true);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateWithCode() {
    if (!code) return;
    setCodeError(null);
    setSubmitting(true);
    try {
      const result = await createEventWithCode(token, {
        description,
        date,
        schedule,
        code,
      });
      setSuccess(result);
    } catch (err) {
      setCodeError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p>Loading...</p>;

  if (error) {
    return (
      <div className="page">
        <h2>This link is invalid or has expired.</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (success) {
    return (
      <div className="page">
        <h2>{success.rescheduled ? "Reminder scheduled!" : "Event confirmed"}</h2>
        {success.rescheduled && (
          <p>"{success.description}" on {success.event_date}</p>
        )}
        {success.manage_url && (
          <p><a className="btn" href={success.manage_url}>Manage your events</a></p>
        )}
      </div>
    );
  }

  const isDirect = info?.valid;
  const isRemind = info?.purpose === "remind_again";

  return (
    <div className="page">
      <h1>{isRemind ? "Remind me again" : "Create a new event"}</h1>

      {formError && <p className="msg msg-err">{formError}</p>}

      {isRemind ? (
        <p>
          <strong>Description:</strong> {info?.event_description}
        </p>
      ) : (
        <textarea
          id="desc"
          placeholder="Event description"
          required
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      )}

      {!codeSent && (
        <>
          <input
            id="date"
            type="date"
            required
            min={new Date().toISOString().slice(0, 10)}
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <select value={schedule} onChange={(e) => setSchedule(e.target.value)}>
            {Object.entries(SCHEDULE_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <button className="btn" type="button" onClick={isDirect ? handleCreateDirect : handleRequestCode} disabled={submitting} style={{ marginTop: 8 }}>
            {submitting ? (isDirect ? "Scheduling..." : "Sending code...") : isRemind ? "Remind me again" : "Create Event"}
          </button>
        </>
      )}

      {codeSent && !success && (
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
            onClick={handleCreateWithCode}
            disabled={submitting || code.length !== 4}
            style={{ marginTop: 8 }}
          >
            {submitting ? "Verifying..." : "Verify & Create"}
          </button>
        </div>
      )}
    </div>
  );
}
