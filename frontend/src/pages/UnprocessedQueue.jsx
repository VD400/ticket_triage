import { useEffect, useState } from "react";
import { ChevronRightIcon, ClockIcon } from "../components/dashboard/icons";
import { MOCK_TICKETS } from "../components/dashboard/mockTickets";
import { bucketTickets } from "../components/dashboard/ticketBuckets";
import { toTitleCase, timeAgo, STATUS_STYLES } from "../components/dashboard/ticketBuckets";

const REFRESH_INTERVAL_MS = 8000;

function QueueRow({ ticket, isExpanded, onToggle }) {
  const statusStyle = STATUS_STYLES[ticket.status];
  const isClassified = Boolean(ticket.category);

  return (
    <div className="rounded-lg border border-[#262C38] bg-[#161A22]">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-4 px-4 py-3.5 text-left"
      >
        <span className={`shrink-0 rounded-md px-2 py-1 text-xs font-medium ${statusStyle.pill}`}>
          {statusStyle.label}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-[#E7E9EE]">{ticket.subject}</p>
          <p className="mt-0.5 truncate text-xs text-[#5B6472]">
            {ticket.customerName}
            {isClassified ? ` · ${toTitleCase(ticket.category)} · ${toTitleCase(ticket.priority)}` : " · Not yet classified"}
          </p>
        </div>
        <span className="hidden shrink-0 text-xs text-[#5B6472] sm:inline">{timeAgo(ticket.createdAt)}</span>
        <ChevronRightIcon className={`h-4 w-4 shrink-0 text-[#5B6472] transition-transform ${isExpanded ? "rotate-90" : ""}`} />
      </button>

      {isExpanded && (
        <div className="border-t border-[#262C38] px-4 py-3.5">
          <p className="text-sm leading-relaxed text-[#8A93A6]">{ticket.description}</p>
          {ticket.status === "processing" && (
            <p className="mt-3 flex items-center gap-2 text-xs text-[#818CF8]">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#818CF8]" />
              The agent is working through this ticket now
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function UnprocessedQueue() {
  const [tickets, setTickets] = useState(() => bucketTickets(MOCK_TICKETS).unprocessed);
  const [expandedIds, setExpandedIds] = useState(() => new Set());
  const [lastRefreshed, setLastRefreshed] = useState(() => new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setTickets(bucketTickets(MOCK_TICKETS).unprocessed);
      setLastRefreshed(new Date());
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  function toggleExpanded(id) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <>
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-[#E7E9EE] sm:text-3xl">
            Unprocessed queue
          </h2>
          <p className="mt-1 text-sm text-[#8A93A6]">
            Tickets still sitting in the queue or being classified — nothing here needs you yet.
          </p>
        </div>
        <p className="hidden shrink-0 text-xs text-[#5B6472] sm:block">
          Updated {timeAgo(lastRefreshed.toISOString())}
        </p>
      </div>

      {tickets.length === 0 ? (
        <div className="rounded-xl border border-[#262C38] bg-[#161A22] px-4 py-12 text-center">
          <ClockIcon className="mx-auto h-6 w-6 text-[#5B6472]" />
          <p className="mt-3 text-sm text-[#8A93A6]">The queue is empty — every ticket has been picked up.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {tickets.map((ticket) => (
            <QueueRow
              key={ticket.id}
              ticket={ticket}
              isExpanded={expandedIds.has(ticket.id)}
              onToggle={() => toggleExpanded(ticket.id)}
            />
          ))}
        </div>
      )}
    </>
  );
}