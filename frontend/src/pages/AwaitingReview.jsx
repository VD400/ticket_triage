import { useState } from "react";
import { ChevronRightIcon, InboxIcon, CheckCircleIcon } from "../components/dashboard/icons";
import { MOCK_TICKETS, MOCK_DRAFTS } from "../components/dashboard/mockTickets";
import { bucketTickets, toTitleCase, timeAgo, PRIORITY_STYLES } from "../components/dashboard/ticketBuckets";
import { API_BASE, authHeaders, extractErrorMessage } from "../components/dashboard/api";

async function submitReview(ticketId, draftId, payload) {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/drafts/${draftId}/review`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(extractErrorMessage(data, "Something went wrong reviewing this draft."));
  return data;
}

function renderAnalysis(analysis) {
  if (!analysis) return "No analysis was recorded for this draft.";
  if (typeof analysis === "string") return analysis;
  return JSON.stringify(analysis, null, 2);
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
      {ticket.priority && (
        <span className={`shrink-0 rounded-md px-2 py-1 text-xs font-medium ${PRIORITY_STYLES[ticket.priority]}`}>
          {toTitleCase(ticket.priority)}
        </span>
      )}
    </button>
  );
}

export default function AwaitingReview() {
  const [tickets, setTickets] = useState(() => bucketTickets(MOCK_TICKETS).awaitingReview);
  const [drafts, setDrafts] = useState(() => MOCK_DRAFTS);
  const [selectedId, setSelectedId] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState("");

  const selectedTicket = tickets.find((t) => t.id === selectedId) ?? null;
  const selectedDraft = selectedTicket ? drafts[selectedTicket.id] : null;

  function selectTicket(ticket) {
    setSelectedId(ticket.id);
    setIsEditing(false);
    setActionError("");
    setEditedText(drafts[ticket.id]?.draftText ?? "");
  }

  function closeDetail() {
    setSelectedId(null);
    setIsEditing(false);
    setActionError("");
  }

  function removeResolvedTicket(ticketId) {
    setTickets((prev) => prev.filter((t) => t.id !== ticketId));
    closeDetail();
  }

  async function handleApprove() {
    if (!selectedTicket || !selectedDraft) return;
    setIsSubmitting(true);
    setActionError("");
    try {
      await submitReview(selectedTicket.id, selectedDraft.id, { action: "approve" });
      removeResolvedTicket(selectedTicket.id);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSaveEdit() {
    if (!selectedTicket || !selectedDraft) return;
    setIsSubmitting(true);
    setActionError("");
    try {
      await submitReview(selectedTicket.id, selectedDraft.id, { action: "edit", edited_text: editedText });
      removeResolvedTicket(selectedTicket.id);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReject() {
    if (!selectedTicket || !selectedDraft) return;
    setIsSubmitting(true);
    setActionError("");
    try {
      await submitReview(selectedTicket.id, selectedDraft.id, { action: "reject" });
      removeResolvedTicket(selectedTicket.id);
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
          Awaiting your review
        </h2>
        <p className="mt-1 text-sm text-[#8A93A6]">
          The agent has drafted a response for each of these — check it, edit it if needed, or send it as-is.
        </p>
      </div>

      <div className="flex gap-5">
        <div className={`w-full shrink-0 md:block md:w-80 ${selectedId ? "hidden" : "block"}`}>
          {tickets.length === 0 ? (
            <div className="rounded-xl border border-[#262C38] bg-[#161A22] px-4 py-12 text-center">
              <InboxIcon className="mx-auto h-6 w-6 text-[#5B6472]" />
              <p className="mt-3 text-sm text-[#8A93A6]">Nothing waiting on your review right now.</p>
            </div>
          ) : (
            <div className="space-y-1 rounded-xl border border-[#262C38] bg-[#161A22] p-2">
              {tickets.map((ticket) => (
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
          {!selectedTicket || !selectedDraft ? (
            <div className="hidden h-full items-center justify-center rounded-xl border border-[#262C38] bg-[#161A22] px-4 py-16 text-center md:flex">
              <p className="text-sm text-[#5B6472]">Select a ticket to review its draft.</p>
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

                <div>
                  <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">Internal analysis</p>
                  <pre className="whitespace-pre-wrap rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 font-mono text-xs leading-relaxed text-[#8A93A6]">
                    {renderAnalysis(selectedDraft.analysis)}
                  </pre>
                </div>

                <div>
                  <p className="mb-1.5 text-xs font-medium text-[#8A93A6]">Draft to the customer</p>
                  {isEditing ? (
                    <textarea
                      rows={8}
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      className="w-full resize-none rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 text-sm leading-relaxed text-[#E7E9EE] focus:border-[#818CF8] focus:outline-none focus:ring-1 focus:ring-[#818CF8]"
                    />
                  ) : (
                    <p className="whitespace-pre-wrap rounded-lg border border-[#262C38] bg-[#0E1116] px-3.5 py-3 text-sm leading-relaxed text-[#E7E9EE]">
                      {selectedDraft.draftText}
                    </p>
                  )}
                </div>

                {actionError && (
                  <p className="rounded-md border border-[#F2665A]/30 bg-[#F2665A]/10 px-3.5 py-2.5 text-sm text-[#F2665A]">
                    {actionError}
                  </p>
                )}

                <div className="flex flex-wrap gap-2 border-t border-[#262C38] pt-5">
                  {isEditing ? (
                    <>
                      <button
                        type="button"
                        onClick={handleSaveEdit}
                        disabled={isSubmitting}
                        className="inline-flex items-center gap-2 rounded-md bg-[#818CF8] px-4 py-2 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#93A0FA] disabled:opacity-60"
                      >
                        {isSubmitting ? "Sending…" : "Save & send"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setIsEditing(false);
                          setEditedText(selectedDraft.draftText);
                        }}
                        disabled={isSubmitting}
                        className="rounded-md border border-[#262C38] bg-transparent px-4 py-2 text-sm font-semibold text-[#8A93A6] transition-colors hover:bg-white/5 hover:text-[#E7E9EE] disabled:opacity-60"
                      >
                        Cancel
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={handleApprove}
                        disabled={isSubmitting}
                        className="inline-flex items-center gap-2 rounded-md bg-[#34D399] px-4 py-2 text-sm font-semibold text-[#0E1116] transition-colors hover:bg-[#4ADE9E] disabled:opacity-60"
                      >
                        <CheckCircleIcon className="h-4 w-4" />
                        {isSubmitting ? "Sending…" : "Approve & send"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsEditing(true)}
                        disabled={isSubmitting}
                        className="rounded-md border border-[#262C38] bg-transparent px-4 py-2 text-sm font-semibold text-[#E7E9EE] transition-colors hover:bg-white/5 disabled:opacity-60"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={handleReject}
                        disabled={isSubmitting}
                        className="rounded-md border border-[#F2665A]/30 bg-transparent px-4 py-2 text-sm font-semibold text-[#F2665A] transition-colors hover:bg-[#F2665A]/10 disabled:opacity-60"
                      >
                        Reject
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}