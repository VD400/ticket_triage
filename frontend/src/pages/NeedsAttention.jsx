import { useState } from "react";
import { ChevronRightIcon, AlertTriangleIcon } from "../components/dashboard/icons";
import { MOCK_TICKETS } from "../components/dashboard/mockTickets";
import { bucketTickets, toTitleCase, timeAgo } from "../components/dashboard/ticketBuckets";
import { API_BASE, authHeaders, extractErrorMessage } from "../components/dashboard/api";

const TABS = [
  { key: "awaiting_clarification", label: "Needs clarification" },
  { key: "needs_manual_review", label: "Needs manual review" },
];

async function submitClarification(ticketId, answer) {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/clarify`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ answer }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(extractErrorMessage(data, "Something went wrong submitting your answer."));
  return data;
}

async function submitManualResolution(ticketId, resolutionText) {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/resolve-manually`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ resolution_text: resolutionText }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(extractErrorMessage(data, "Something went wrong resolving this ticket."));
  return data;
}

function TicketListItem({ ticket, isSelected, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        "flex w-full items-start gap-3 rounded-lg px-3 py-3 text-left transition-colors",
        isSelected ? "bg-[#818CF8]/12" : "hover:bg-white/5",
      ].join(" ")}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-[#E7E9EE]">{ticket.subject}</p>
        <p className="mt-0.5 truncate text-xs text-[#5B6472]">
          {ticket.customerName} · {timeAgo(ticket.createdAt)}
        </p>
      </div>
    </button>
  );
}

export default function NeedsAttention() {
  const allNeedsAttention = bucketTickets(MOCK_TICKETS).needsAttention;
  const [tickets, setTickets] = useState(allNeedsAttention);
  const [activeTab, setActiveTab] = useState(TABS[0].key);
  const [selectedId, setSelectedId] = useState(null);
  const [answerText, setAnswerText] = useState("");
  const [resolutionText, setResolutionText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState("");
  const [submittedIds, setSubmittedIds] = useState(() => new Set());

  const visibleTickets = tickets.filter((t) => t.status === activeTab);
  const selectedTicket = visibleTickets.find((t) => t.id === selectedId) ?? null;
  const isSubmitted = selectedTicket ? submittedIds.has(selectedTicket.id) : false;

  function selectTicket(ticket) {
    setSelectedId(ticket.id);
    setAnswerText("");
    setResolutionText("");
    setActionError("");
  }

  function closeDetail() {
    setSelectedId(null);
    setActionError("");
  }

  function switchTab(tabKey) {
    setActiveTab(tabKey);
    setSelectedId(null);
    setActionError("");
  }

  async function handleSubmitAnswer() {
    if (!selectedTicket || !answerText.trim()) return;
    setIsSubmitting(true);
    setActionError("");
    try {
      await submitClarification(selectedTicket.id, answerText);
      setSubmittedIds((prev) => new Set(prev).add(selectedTicket.id));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmitResolution() {
    if (!selectedTicket || !resolutionText.trim()) return;
    setIsSubmitting(true);
    setActionError("");
    try {
      await submitManualResolution(selectedTicket.id, resolutionText);
      setTickets((prev) => prev.filter((t) => t.id !== selectedTicket.id));
      closeDetail();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-[#E7E9EE] sm:text-3xl">
          Needs attention
        </h2>
        <p className="mt-1 text-sm text-[#8A93A6]">
          These need a human in the loop — either to answer a question the agent got stuck on, or to write the resolution yourself.
        </p>
      </div>

      <div className="mb-5 flex items-center gap-1 border-b border-[#262C38]">
        {TABS.map((tab) => {
          const count = tickets.filter((t) => t.status === tab.key).length;
          const isActive = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => switchTab(tab.key)}
              className={[
                "border-b-2 px-3 pb-2.5 text-sm font-medium transition-colors",
                isActive ? "border-[#F2665A] text-[#E7E9EE]" : "border-transparent text-[#8A93A6] hover:text-[#E7E9EE]",
              ].join(" ")}
            >
              {tab.label}
              {count > 0 && <span className="ml-1.5 text-xs text-[#5B6472]">{count}</span>}
            </button>
          );
        })}
      </div>

      <div className="flex gap-5">
        <div className={`w-full shrink-0 md:block md:w-80 ${selectedId ? "hidden" : "block"}`}>
          {visibleTickets.length === 0 ? (
            <div className="rounded-xl border border-[#262C38] bg-[#161A22] px-4 py-12 text-center">
              <AlertTriangleIcon className="mx-auto h-6 w-6 text-[#5B6472]" />
              <p className="mt-3 text-sm text-[#8A93A6]">Nothing flagged here right now.</p>
            </div>
          ) : (
            <div className="space-y-1 rounded-xl border border-[#262C38] bg-[#161A22] p-2">
              {visibleTickets.map((ticket) => (
                <TicketListItem
                  key={ticket.id}
                  ticket={ticket}
                  isSelected={ticket.id === selectedId}
                  onSelect={() => selectTicket(ticket)}
                />
              ))}
            </div>
          )}
        </div>

        <div className={`min-w-0 flex-1 ${selectedId ? "block" : "hidden md:block"}`}>
          {!selectedTicket ? (
            <div className="hidden h-full items-center justify-center rounded-xl border border-[#262C38] bg-[#161A22] px-4 py-16 text-center md:flex">
              <p className="text-sm text-[#5B6472]">Select a ticket to see what it needs.</p>
            </div>
          ) : (
            <div className="rounded-xl border border-[#262C38] bg-[#161A22]">
              <div className="flex items-start gap-3 border-b border-[#262C38] px-5 py-4">
                <button
                  type="button"
                  onClick={closeDetail}
                  className="rounded-md p-1 text-[#8A93A6] hover:bg-white/5 hover:text-[#E7E9EE] md:hidden"
                  aria-label="Back to list"
                >
                  <ChevronRightIcon className="h-5 w-5 rotate-180" />
                </button>
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-base font-semibold text-[#E7E9EE]">{selectedTicket.subject}</h3>
                  <p className="mt-0.5 text-xs text-[#5B6472]">
                    {selectedTicket.customerName}
                    {selectedTicket.category ? ` · ${toTitleCase(selectedTicket.category)}` : ""} · {timeAgo(selectedTicket.createdAt)}
                  </p>
                </div>
              </div>

              <div className="space-y-5 px-5 py-5">
                <div>
                  <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">Original complaint</p>
                  <p className="text-sm leading-relaxed text-[#8A93A6]">{selectedTicket.description}</p>
                </div>

                {selectedTicket.status === "awaiting_clarification" ? (
                  isSubmitted ? (
                    <p className="rounded-md border border-[#34D399]/30 bg-[#34D399]/10 px-3.5 py-2.5 text-sm text-[#34D399]">
                      Answer submitted — the agent will resume shortly and this ticket will move on its own.
                    </p>
                  ) : (
                    <>
                      <div>
                        <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">The agent is stuck on</p>
                        <p className="rounded-lg border border-[#F5B843]/30 bg-[#F5B843]/10 px-3.5 py-3 text-sm leading-relaxed text-[#F5B843]">
                          {selectedTicket.clarificationQuestion}
                        </p>
                      </div>
                      <div>
                        <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">Your answer</p>
                        <textarea
                          rows={4}
                          value={answerText}
                          onChange={(e) => setAnswerText(e.target.value)}
                          placeholder="Type what the agent needs to know"
                          className="w-full resize-none rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 text-sm leading-relaxed text-[#E7E9EE] placeholder:text-[#5B6472] focus:border-[#818CF8] focus:outline-none focus:ring-1 focus:ring-[#818CF8]"
                        />
                      </div>
                      {actionError && (
                        <p className="rounded-md border border-[#F2665A]/30 bg-[#F2665A]/10 px-3.5 py-2.5 text-sm text-[#F2665A]">
                          {actionError}
                        </p>
                      )}
                      <div className="border-t border-[#262C38] pt-5">
                        <button
                          type="button"
                          onClick={handleSubmitAnswer}
                          disabled={isSubmitting || !answerText.trim()}
                          className="rounded-md bg-[#818CF8] px-4 py-2 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#93A0FA] disabled:opacity-60"
                        >
                          {isSubmitting ? "Submitting…" : "Submit answer"}
                        </button>
                      </div>
                    </>
                  )
                ) : (
                  <>
                    {selectedTicket.rejectedDraftText && (
                      <div>
                        <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">Draft that was rejected</p>
                        <p className="whitespace-pre-wrap rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 text-sm leading-relaxed text-[#5B6472]">
                          {selectedTicket.rejectedDraftText}
                        </p>
                      </div>
                    )}
                    <div>
                      <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">Your resolution</p>
                      <textarea
                        rows={6}
                        value={resolutionText}
                        onChange={(e) => setResolutionText(e.target.value)}
                        placeholder="Write the full resolution to send to the customer"
                        className="w-full resize-none rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 text-sm leading-relaxed text-[#E7E9EE] placeholder:text-[#5B6472] focus:border-[#818CF8] focus:outline-none focus:ring-1 focus:ring-[#818CF8]"
                      />
                    </div>
                    {actionError && (
                      <p className="rounded-md border border-[#F2665A]/30 bg-[#F2665A]/10 px-3.5 py-2.5 text-sm text-[#F2665A]">
                        {actionError}
                      </p>
                    )}
                    <div className="border-t border-[#262C38] pt-5">
                      <button
                        type="button"
                        onClick={handleSubmitResolution}
                        disabled={isSubmitting || !resolutionText.trim()}
                        className="rounded-md bg-[#34D399] px-4 py-2 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#4ADE9E] disabled:opacity-60"
                      >
                        {isSubmitting ? "Resolving…" : "Resolve ticket"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}