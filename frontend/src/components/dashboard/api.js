import { notifyTicketUpdate } from "./useDashboard";
export const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export function authHeaders(includeJson = true) {
  const token = localStorage.getItem("token");
  return {
    ...(includeJson ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export function toWsUrl(httpUrl) {
  return httpUrl.replace(/^http/, "ws");
}

export function extractErrorMessage(data, fallback) {
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail) && data.detail[0]?.msg) return data.detail[0].msg;
  return fallback;
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : null;

  if (!response.ok) {
    throw new Error(
      extractErrorMessage(data, `Request failed (${response.status})`)
    );
  }

  if (options.method && options.method !== "GET") notifyTicketUpdate();
  return data;
}

export function normalizeTicket(ticket) {
  if (!ticket) return null;

  return {
    ...ticket,
    customerName: ticket.customer_name ?? `Customer #${ticket.customer_id}`,
    customerEmail: ticket.customer_email ?? null,
    assignedAgentId: ticket.assigned_agent_id ?? null,
    createdAt: ticket.created_at,
    updatedAt: ticket.updated_at,
  };
}

export function normalizeDraft(draft) {
  if (!draft) return null;

  return {
    ...draft,
    ticketId: draft.ticket_id,
    reviewedBy: draft.reviewed_by,
    draftText: draft.draft_text,
    reviewedAt: draft.reviewed_at,
    createdAt: draft.created_at,
  };
}

export function normalizeResolution(resolution) {
  if (!resolution) return null;

  return {
    ...resolution,
    ticketId: resolution.ticket_id,
    resolvedBy: resolution.resolved_by,
    resolutionText: resolution.resolution_text,
    createdAt: resolution.created_at,
  };
}

export async function fetchTickets({ completed = false } = {}) {
  const path = completed ? "/tickets/completed" : "/tickets/";
  const data = await requestJson(path, { headers: authHeaders(false) });
  return Array.isArray(data) ? data.map(normalizeTicket) : [];
}

export async function fetchTicket(ticketId) {
  const data = await requestJson(`/tickets/${ticketId}`, {
    headers: authHeaders(false),
  });
  return normalizeTicket(data);
}

export async function fetchTicketEvents(ticketId) {
  const data = await requestJson(`/tickets/${ticketId}/event`, {
    headers: authHeaders(false),
  });
  return Array.isArray(data) ? data : [];
}

export async function fetchTicketDrafts(ticketId) {
  const data = await requestJson(`/tickets/${ticketId}/drafts`, {
    headers: authHeaders(false),
  });
  return Array.isArray(data) ? data.map(normalizeDraft) : [];
}

export async function fetchTicketResolution(ticketId) {
  const data = await requestJson(`/tickets/${ticketId}/resolution`, {
    headers: authHeaders(false),
  });
  return normalizeResolution(data);
}

export async function fetchResolutions() {
  const data = await requestJson("/tickets/resolution", {
    headers: authHeaders(false),
  });
  return Array.isArray(data) ? data.map(normalizeResolution) : [];
}

export async function fetchCurrentUser() {
  return requestJson("/auth/me", {
    headers: authHeaders(false),
  });
}

export async function submitDraftReview(ticketId, draftId, payload) {
  return requestJson(`/tickets/${ticketId}/drafts/${draftId}/review`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
}

export async function submitClarification(ticketId, answer) {
  return requestJson(`/tickets/${ticketId}/clarify`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ answer }),
  });
}

export async function submitManualResolution(ticketId, resolutionText) {
  return requestJson(`/tickets/${ticketId}/resolve-manually`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ resolution_text: resolutionText }),
  });
}
