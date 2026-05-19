const BASE = "/api";

async function request(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`);
    err.data = data;
    err.status = res.status;
    throw err;
  }
  return data;
}

export function createEvent({ email, description, date, schedule }) {
  return request(`${BASE}/events`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, description, date, schedule }),
  });
}

export function validateToken(token) {
  return request(`${BASE}/tokens/${token}`);
}

export function createEventFromToken(token, { description, date, schedule }) {
  return request(`${BASE}/events/from-token/${token}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, date, schedule }),
  });
}

export function verifyAccount(token) {
  return request(`${BASE}/verify/${token}`, { method: "POST" });
}

export function getVersion() {
  return request(`${BASE}/version`);
}

export function getEmailPreview(eventId) {
  return request(`${BASE}/events/${eventId}/preview`);
}

export function getEvent(eventId, token) {
  return request(`${BASE}/events/${eventId}?token=${encodeURIComponent(token)}`);
}

export function resendVerification(email) {
  return request(`${BASE}/verify/resend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export function deleteEvent(eventId, token) {
  return request(`${BASE}/events/${eventId}/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
}

export function requestSecurityCode(token) {
  return request(`${BASE}/tokens/${token}/request-code`, { method: "POST" });
}

export function createEventWithCode(token, { description, date, schedule, code }) {
  return request(`${BASE}/tokens/${token}/create-event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, date, schedule, code }),
  });
}

export function getManageEvents(token) {
  return request(`${BASE}/manage/${token}`);
}

export function verifyCode(token, code) {
  return request(`${BASE}/tokens/${token}/verify-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
}

