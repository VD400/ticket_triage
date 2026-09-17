import { CheckCircleIcon, ChevronRightIcon } from "../components/dashboard/icons";
import { MOCK_TICKETS, MOCK_RESOLUTIONS } from "../components/dashboard/mockTickets";
import { bucketTickets, toTitleCase, timeAgo } from "../components/dashboard/ticketBuckets";
import { useState } from "react";

function TicketListItem({ ticket, resolution, isSelected, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        "flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left transition-colors",
        isSelected ? "bg-[#818CF8]/12" : "hover:bg-white/5",
      ].join(" ")}
    >
      <span className="mt-0.5 shrink-0 text-[#34D399]">
        <CheckCircleIcon className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[#E7E9EE]">{ticket.subject}</p>
        <p className="mt-0.5 truncate text-xs text-[#5B6472]">
          {ticket.customerName} · Resolved {resolution ? timeAgo(resolution.createdAt) : timeAgo(ticket.createdAt)}
        </p>
      </div>
    </button>
  );
}

export default function Resolved() {
  const tickets = bucketTickets(MOCK_TICKETS).resolved;
  const [selectedId, setSelectedId] = useState(null);

  const selectedTicket = tickets.find((t) => t.id === selectedId) ?? null;
  const selectedResolution = selectedTicket ? MOCK_RESOLUTIONS[selectedTicket.id] : null;

  return (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-[#E7E9EE] sm:text-3xl">
          Resolved
        </h2>
        <p className="mt-1 text-sm text-[#8A93A6]">
          Closed tickets and what was sent to each customer.
        </p>
      </div>

      <div className="flex gap-5">
        <div className={`w-full shrink-0 md:block md:w-80 ${selectedId ? "hidden" : "block"}`}>
          {tickets.length === 0 ? (
            <div className="rounded-xl border border-[#262C38] bg-[#161A22] px-4 py-12 text-center">
              <CheckCircleIcon className="mx-auto h-6 w-6 text-[#5B6472]" />
              <p className="mt-3 text-sm text-[#8A93A6]">Nothing resolved yet.</p>
            </div>
          ) : (
            <div className="space-y-1 rounded-xl border border-[#262C38] bg-[#161A22] p-2">
              {tickets.map((ticket) => (
                <TicketListItem
                  key={ticket.id}
                  ticket={ticket}
                  resolution={MOCK_RESOLUTIONS[ticket.id]}
                  isSelected={ticket.id === selectedId}
                  onSelect={() => setSelectedId(ticket.id)}
                />
              ))}
            </div>
          )}
        </div>

        <div className={`min-w-0 flex-1 ${selectedId ? "block" : "hidden md:block"}`}>
          {!selectedTicket ? (
            <div className="hidden h-full items-center justify-center rounded-xl border border-[#262C38] bg-[#161A22] px-4 py-16 text-center md:flex">
              <p className="text-sm text-[#5B6472]">Select a resolved ticket to see how it was handled.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-[#262C38] bg-[#161A22]">
              <div className="flex items-start gap-3 border-b border-[#262C38] px-5 py-4">
                <button
                  type="button"
                  onClick={() => setSelectedId(null)}
                  className="rounded-md p-1 text-[#8A93A6] hover:bg-white/5 hover:text-[#E7E9EE] md:hidden"
                  aria-label="Back to list"
                >
                  <ChevronRightIcon className="h-5 w-5 rotate-180" />
                </button>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-base font-semibold text-[#E7E9EE]">{selectedTicket.subject}</h3>
                  <p className="mt-0.5 text-xs text-[#5B6472]">
                    {selectedTicket.customerName}
                    {selectedTicket.category ? ` · ${toTitleCase(selectedTicket.category)}` : ""}
                    {selectedTicket.priority ? ` · ${toTitleCase(selectedTicket.priority)}` : ""}
                  </p>
                </div>
                <span className="shrink-0 rounded-md bg-[#34D399]/15 px-2 py-1 text-xs font-medium text-[#34D399]">
                  Resolved
                </span>
              </div>

              <div className="space-y-5 px-5 py-5">
                <div>
                  <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">Original complaint</p>
                  <p className="text-sm leading-relaxed text-[#8A93A6]">{selectedTicket.description}</p>
                </div>

                <div>
                  <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">What was sent to the customer</p>
                  {selectedResolution ? (
                    <p className="whitespace-pre-wrap rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 text-sm leading-relaxed text-[#E7E9EE]">
                      {selectedResolution.resolutionText}
                    </p>
                  ) : (
                    <p className="rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 text-sm text-[#5B6472]">
                      No resolution text on record for this ticket.
                    </p>
                  )}
                </div>

                {selectedResolution && (
                  <p className="text-xs text-[#5B6472]">
                    Resolved {timeAgo(selectedResolution.createdAt)} by agent #{selectedResolution.resolvedBy}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}