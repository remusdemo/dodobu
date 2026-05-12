import { useEffect, useState } from "react";
import { verifyAccount } from "../api";

export default function VerifyPage({ token }) {
  const [state, setState] = useState({ loading: true });

  useEffect(() => {
    verifyAccount(token)
      .then((result) => setState(result))
      .catch((err) => setState({ error: err.message }));
  }, [token]);

  if (state.loading) {
    return <p>Verifying...</p>;
  }

  if (state.error) {
    return <h1>This link is invalid or has already been used.</h1>;
  }

  const events = state.activated === 1 ? "1 event" : `${state.activated} events`;

  return (
    <div>
      <h2>Email verified!</h2>
      <p>Your account is now verified. {events} activated.</p>
    </div>
  );
}
