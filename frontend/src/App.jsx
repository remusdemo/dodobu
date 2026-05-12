import CreateEventPage from "./pages/CreateEventPage";
import TokenEventPage from "./pages/TokenEventPage";
import VerifyPage from "./pages/VerifyPage";

export default function App() {
  const path = window.location.pathname;
  const v = path.match(/^\/verify\/(.+)$/);
  if (v) return <VerifyPage token={v[1]} />;
  const m = path.match(/^\/event\/new\/(.+)$/);
  if (m) return <TokenEventPage token={m[1]} />;
  return <CreateEventPage />;
}
