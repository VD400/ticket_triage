import { useState } from "react";
import { ChevronRightIcon } from "./icons";
import { toTitleCase, timeAgo, PRIORITY_STYLES } from "./ticketBuckets";

const TABS = [
  { key: "awaitingReview", label: "Awaiting review" },
  { key: "needsAttention", label: "Needs attention" },
  { key: "unprocessed", label: "Unprocessed" },
  { key: "resolved", label: "Resolved" },
];

const EMPTY_COPY = {
  awaitingReview: "No drafts waiting on you. The agent will drop new ones here once it finishes a ticket.",
  needsAttention: "Nothing flagged for a human right now.",
  unprocessed: "The queue is empty — every ticket has been picked up.",
  resolved: "No resolved tickets yet.",
};

function TicketRow({ ticket, onOpen }) {
  return (
    <button
      type="button"
      onClick={() => onOpen?.(ticket)}
      className="flex w-full items-center gap-4 rounded-lg px-3 py-3 text-left transition-colors hover:bg-white/5"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[#E7E9EE]">{ticket.subject}</p>
        <p className="mt-0.5 truncate text-xs text-[#5B6472]">
          {ticket.customerName}{ticket.category ? ` · ${toTitleCase(ticket.category)}` : ""}
        </p>
      </div>
      {ticket.priority && (
        <span className={`hidden shrink-0 rounded-md px-2 py-1 text-xs font-medium sm:inline-block ${PRIORITY_STYLES[ticket.priority]}`}>
          {toTitleCase(ticket.priority)}
        </span>
      )}
      <span className="hidden shrink-0 text-xs text-[#5B6472] sm:inline">{timeAgo(ticket.createdAt)}</span>
      <ChevronRightIcon className="h-4 w-4 shrink-0 text-[#5B6472]" />
    </button>
  );
}

export default function AttentionQueue({ ticketsByBucket = {}, onOpenTicket }) {
  const [activeTab, setActiveTab] = useState(TABS[0].key);
  const tickets = ticketsByBucket[activeTab] ?? [];

  return (
    <div className="rounded-xl border border-[#262C38] bg-[#161A22]">
      <div className="flex items-center gap-1 overflow-x-auto border-b border-[#262C38] px-3 pt-2">
        {TABS.map((tab) => {
          const count = ticketsByBucket[tab.key]?.length ?? 0;
          const isActive = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={[
                "whitespace-nowrap border-b-2 px-3 pb-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "border-[#818CF8] text-[#E7E9EE]"
                  : "border-transparent text-[#8A93A6] hover:text-[#E7E9EE]",
              ].join(" ")}
            >
              {tab.label}
              {count > 0 && <span className="ml-1.5 text-xs text-[#5B6472]">{count}</span>}
            </button>
          );
        })}
      </div>

      <div className="p-2">
        {tickets.length === 0 ? (
          <p className="px-3 py-8 text-center text-sm text-[#5B6472]">{EMPTY_COPY[activeTab]}</p>
        ) : (
          <div className="divide-y divide-[#262C38]">
            {tickets.map((ticket) => (
              <TicketRow key={ticket.id} ticket={ticket} onOpen={onOpenTicket} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}