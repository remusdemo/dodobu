import { useEffect, useState } from "react";
import { getEvent, deleteEvent } from "../api";

export default function DeleteEventPage({ eventId, token }) {
  const [state, setState] = useState({ loading: true });
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getEvent(eventId, token)
      .then((event) => setState({ event }))
      .catch((err) => setState({ error: err.message }));
  }, [eventId, token]);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteEvent(eventId, token);
      setState({ deleted: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(false);
    }
  }

  if (state.loading) {
    return <p>Loading...</p>;
  }

  if (state.error) {
    return <p style={{ color: "red" }}>{state.error}</p>;
  }

  if (state.deleted) {
    return (
      <div>
        <h2>Event deleted</h2>
        <p>The event &ldquo;{state.event.description}&rdquo; has been deleted. No more reminders will be sent.</p>
        <a href="/">Create a new event</a>
      </div>
    );
  }

  return (
    <div>
      <h2>Delete event</h2>
      <p>Do you want to delete event &ldquo;{state.event.description}&rdquo;?</p>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <button type="button" onClick={handleDelete} disabled={deleting}>
        {deleting ? "Deleting..." : "Confirm delete"}
      </button>
      {" "}
      <a href="/">Cancel</a>
    </div>
  );
}
