import { useCallback, useEffect, useState } from "react";
import { fetchTicketEvents } from "../components/dashboard/api";
import useLiveSocket from "./useLiveSocket";

export function mergeEvents(current, incoming) {
  const byId = new Map(current.map((event) => [event.id, event]));
  for (const event of incoming) if (event.id != null) byId.set(event.id, event);
  return [...byId.values()].sort(
    (a, b) => new Date(a.created_at) - new Date(b.created_at) || a.id - b.id,
  );
}

export default function useTicketWebSocket(ticketId) {
  const [snapshot, setSnapshot] = useState({
    ticketId: null,
    events: [],
    loaded: false,
    error: "",
  });
  const receive = useCallback(
    (incoming) => {
      const rows =
        incoming.type === "history"
          ? incoming.events
          : incoming.id != null
            ? [incoming]
            : [];
      setSnapshot((previous) => ({
        ticketId,
        events: mergeEvents(
          previous.ticketId === ticketId ? previous.events : [],
          rows,
        ),
        loaded: true,
        error: "",
      }));
    },
    [ticketId],
  );
  useEffect(() => {
    if (!ticketId) return;
    let stopped = false;
    let pending = false;
    async function load() {
      if (pending) return;
      pending = true;
      try {
        const events = await fetchTicketEvents(ticketId);
        if (!stopped) receive({ type: "history", events });
      } catch (err) {
        if (!stopped)
          setSnapshot((previous) => ({
            ticketId,
            events: previous.ticketId === ticketId ? previous.events : [],
            loaded: true,
            error: err.message || "Could not load ticket history.",
          }));
      } finally {
        pending = false;
      }
    }
    load();
    const interval = setInterval(load, 5000);
    window.addEventListener("focus", load);
    return () => {
      stopped = true;
      clearInterval(interval);
      window.removeEventListener("focus", load);
    };
  }, [ticketId, receive]);
  const connectionStatus = useLiveSocket(
    ticketId ? `/tickets/${ticketId}/stream` : null,
    receive,
  );
  const current =
    snapshot.ticketId === ticketId
      ? snapshot
      : { events: [], loaded: false, error: "" };
  return {
    events: current.events,
    loading: !current.loaded,
    error: current.error,
    connectionStatus,
  };
}
