import { createContext, useContext } from "react";
export const DashboardContext = createContext(null);
export function useDashboard() {
  const value = useContext(DashboardContext);
  if (!value)
    throw new Error("Dashboard data is unavailable outside the dashboard.");
  return value;
}

export function notifyTicketUpdate() {
  window.dispatchEvent(new Event("tickets-updated"));
  // Storage events reach other same-origin tabs, including the dashboard open
  // while a customer submits a complaint in another tab.
  localStorage.setItem("tickets-updated", `${Date.now()}-${Math.random()}`);
}
