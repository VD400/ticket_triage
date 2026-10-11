import { useState } from "react";
import { retryTicket } from "./api";
import { useDashboard } from "./useDashboard";

export default function RecoveryButton({ ticket }) {
  const { user, refresh } = useDashboard();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [requestedFor, setRequestedFor] = useState(null);
  if (!ticket.recovery_available || !["admin", "agent"].includes(user?.role))
    return null;
  const submitted = requestedFor === ticket.updatedAt;
  async function recover() {
    setPending(true);
    setError("");
    try {
      await retryTicket(ticket.id);
      setRequestedFor(ticket.updatedAt);
      await refresh();
    } catch (err) {
      setError(err.message || "Could not recover this ticket.");
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={recover}
        disabled={pending || submitted}
        className="rounded-md border border-[#818CF8]/40 bg-[#818CF8]/10 px-4 py-2 text-sm font-medium text-[#ADB5FC] hover:bg-[#818CF8]/20 disabled:opacity-50"
      >
        {pending
          ? "Queueing recovery…"
          : submitted
            ? "Recovery queued"
            : "Retry processing"}
      </button>
      <p className="mt-2 text-xs leading-relaxed text-[#8A93A6]">
        Checks saved progress and returns this ticket to the worker. Keep the
        worker running.
      </p>
      {error && (
        <p role="alert" className="mt-3 text-sm text-[#F2665A]">
          {error}
        </p>
      )}
    </div>
  );
}
