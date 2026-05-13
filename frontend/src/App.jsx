import CreateEventPage from "./pages/CreateEventPage";
import DeleteEventPage from "./pages/DeleteEventPage";
import TokenEventPage from "./pages/TokenEventPage";
import VerifyPage from "./pages/VerifyPage";

export default function App() {
  const path = window.location.pathname;
  const search = window.location.search;
  const v = path.match(/^\/verify\/(.+)$/);
  if (v) return <VerifyPage token={v[1]} />;
  const d = path.match(/^\/event\/(\d+)\/delete$/);
  if (d) {
    const params = new URLSearchParams(search);
    const token = params.get("token");
    if (token) return <DeleteEventPage eventId={parseInt(d[1])} token={token} />;
    return <p>Missing token</p>;
  }
  const m = path.match(/^\/event\/new\/(.+)$/);
  if (m) return <TokenEventPage token={m[1]} />;
  return <CreateEventPage />;
}
