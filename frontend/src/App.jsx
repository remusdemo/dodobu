import CreateEventPage from "./pages/CreateEventPage";
import DeleteEventPage from "./pages/DeleteEventPage";
import MagicTokenPage from "./pages/MagicTokenPage";
import ManagePage from "./pages/ManagePage";
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

  const t = path.match(/^\/token\/(.+)$/);
  if (t) return <MagicTokenPage token={t[1]} />;

  const mg = path.match(/^\/manage\/(.+)$/);
  if (mg) return <ManagePage token={mg[1]} />;

  const TOKEN_MOCK = {
    "token-valid": {
      success: { rescheduled: false, manage_url: "/manage/mock-manage-token" },
    },
    "token-expired": {
      info: { valid: false, purpose: "new_event" },
      description: "Dentist appointment",
      date: "2026-06-15",
      codeSent: true,
    },
  };
  const MANAGE_MOCK = {
    "manage-valid": {
      new_event_token: "mock-new-token",
      events: [
        { id: 1, description: "Dentist appointment", event_date: "2026-06-15", status: "active", delete_token: "mock-delete-1" },
        { id: 2, description: "Pick up dry cleaning before they close for the weekend", event_date: "2026-05-20", status: "active", delete_token: "mock-delete-2" },
      ],
    },
    "manage-expired": {
      needsCode: true,
    },
  };
  const VERIFY_MOCK = {
    verify: { activated: 3, account_verified: true, manage_url: "/manage/mock-manage-token" },
  };
  const tp = path.match(/^\/testing\/page\/(.+)$/);
  if (tp && TOKEN_MOCK[tp[1]]) return <MagicTokenPage data={TOKEN_MOCK[tp[1]]} />;
  if (tp && MANAGE_MOCK[tp[1]]) return <ManagePage data={MANAGE_MOCK[tp[1]]} />;
  if (tp && VERIFY_MOCK[tp[1]]) return <VerifyPage data={VERIFY_MOCK[tp[1]]} />;

  return <CreateEventPage />;
}
