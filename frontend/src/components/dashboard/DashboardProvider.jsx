import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCurrentUser, fetchTickets } from "./api";
import { bucketTickets } from "./ticketBuckets";
import { DashboardContext } from "./useDashboard";
import useLiveSocket from "../../hooks/useLiveSocket";

export default function DashboardProvider({ children }) {
  const [tickets, setTickets] = useState([]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const active = useRef(false);
  const inFlight = useRef(null);
  const dirty = useRef(false);
  const refresh = useCallback(async function refreshTickets() {
    if (!active.current) return;
    if (inFlight.current) {
      dirty.current = true;
      return inFlight.current;
    }
    const request = (async () => {
      try {
        const rows = await fetchTickets();
        if (!active.current) return;
        setTickets(rows);
        setLastRefreshed(new Date());
        setError("");
      } catch (err) {
        if (active.current)
          setError(
            err.message || "Could not refresh tickets. Retrying automatically.",
          );
      } finally {
        if (active.current) setLoading(false);
      }
    })();
    inFlight.current = request;
    await request;
    inFlight.current = null;
    if (dirty.current && active.current) {
      dirty.current = false;
      return refreshTickets();
    }
  }, []);

  useEffect(() => {
    active.current = true;
    refresh();
    fetchCurrentUser()
      .then((value) => {
        if (active.current) setUser(value);
      })
      .catch(() => {});
    const interval = setInterval(refresh, 5000);
    const onStorage = (event) => {
      if (event.key === "tickets-updated") refresh();
    };
    const onVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };
    window.addEventListener("focus", refresh);
    window.addEventListener("tickets-updated", refresh);
    window.addEventListener("storage", onStorage);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      active.current = false;
      clearInterval(interval);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("tickets-updated", refresh);
      window.removeEventListener("storage", onStorage);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [refresh]);
  const connectionStatus = useLiveSocket(
    "/tickets/updates/stream",
    refresh,
    refresh,
  );
  return (
    <DashboardContext.Provider
      value={{
        tickets,
        user,
        buckets: bucketTickets(tickets),
        loading,
        error,
        lastRefreshed,
        refresh,
        connectionStatus,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}
