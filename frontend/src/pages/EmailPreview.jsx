import { useEffect, useState } from "react";
import { getEmailPreview } from "../api";

export default function EmailPreview({ eventId }) {
  const [email, setEmail] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getEmailPreview(eventId)
      .then(setEmail)
      .catch((err) => setError(err.message));
  }, [eventId]);

  if (error) {
    return <h1>Event not found</h1>;
  }

  if (!email) {
    return <p>Loading preview...</p>;
  }

  return (
    <div>
      <h1>Email Preview</h1>
      <h3>TO: {email.to}</h3>
      <h3>SUBJECT: {email.subject}</h3>
      <pre>{email.body}</pre>
    </div>
  );
}
