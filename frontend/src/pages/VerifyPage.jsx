import { useEffect, useState } from "react";
import { verifyAccount } from "../api";

export default function VerifyPage({ token, data: mockData }) {
  const [state, setState] = useState(mockData || { loading: true });

  useEffect(() => {
    if (mockData) return;
    verifyAccount(token)
      .then((result) => setState(result))
      .catch((err) => setState({ error: err.message }));
  }, [token, mockData]);

  if (state.loading) {
    return <div className="page"><p>Verifying...</p></div>;
  }

  if (state.error) {
    return <div className="page"><h1>This link is invalid or has already been used.</h1></div>;
  }

  const events = state.activated === 1 ? "1 event" : `${state.activated} events`;

  return (
    <div className="page">
      <h2>Email verified!</h2>
      <p>Your account is now verified. {events} activated.</p>
      {state.manage_url && (
        <p><a className="btn" href={state.manage_url}>Manage your events</a></p>
      )}
    </div>
  );
}
