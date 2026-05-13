const BASE = "/api";

async function request(url, options) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
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

export function deleteEvent(eventId, token) {
  return request(`${BASE}/events/${eventId}/delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
}
