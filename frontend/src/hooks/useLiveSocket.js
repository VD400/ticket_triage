import { useEffect, useRef, useState } from "react";
import { API_BASE, toWsUrl } from "../components/dashboard/api";

// Reconnecting transport shared by the dashboard and the selected ticket.
export default function useLiveSocket(path, onMessage, onOpen) {
  const callbacks = useRef({ onMessage, onOpen });
  useEffect(() => {
    callbacks.current = { onMessage, onOpen };
  }, [onMessage, onOpen]);
  const [connection, setConnection] = useState({
    path: null,
    status: "connecting",
  });
  useEffect(() => {
    if (!path) return;
    let stopped = false;
    let socket;
    let timer;
    let attempt = 0;
    function connect() {
      if (stopped) return;
      const token = localStorage.getItem("token");
      if (!token) {
        setConnection({ path, status: "unauthorized" });
        return;
      }
      const base = API_BASE || window.location.origin;
      socket = new WebSocket(
        `${toWsUrl(base)}${path}?token=${encodeURIComponent(token)}`,
      );
      const currentSocket = socket;
      socket.onopen = () => {
        if (stopped || socket !== currentSocket) return;
        attempt = 0;
        setConnection({ path, status: "connected" });
        callbacks.current.onOpen?.();
      };
      socket.onmessage = (message) => {
        if (stopped || socket !== currentSocket) return;
        try {
          callbacks.current.onMessage?.(JSON.parse(message.data));
        } catch {
          /* Polling will recover if a malformed notification arrives. */
        }
      };
      socket.onerror = () => currentSocket.close();
      socket.onclose = (event) => {
        if (stopped || socket !== currentSocket) return;
        setConnection({
          path,
          status: event.code === 1008 ? "unauthorized" : "reconnecting",
        });
        if (event.code !== 1008)
          timer = setTimeout(connect, Math.min(1000 * 2 ** attempt++, 15000));
      };
    }
    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, [path]);
  return connection.path === path ? connection.status : "connecting";
}
