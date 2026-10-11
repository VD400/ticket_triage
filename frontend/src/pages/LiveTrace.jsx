import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import useTicketWebSocket from "../hooks/useTicketWebSocket";
import { useDashboard } from "../components/dashboard/useDashboard";
import {
  fetchTicketDrafts,
  fetchTicketResolution,
} from "../components/dashboard/api";
import {
  STATUS_STYLES,
  timeAgo,
  toTitleCase,
} from "../components/dashboard/ticketBuckets";

const LABELS = {
  queued: "Complaint received",
  processing_started: "Agent picked up the ticket",
  classified: "Category and priority assigned",
  tool_called: "Searching for context",
  tool_result: "Context retrieved",
  supervisor_decision: "Next step decided",
  clarification_requested: "Waiting for clarification",
  clarification_answered: "Clarification received — work resumed",
  draft_created: "Response drafted",
  awaiting_approval: "Ready for human review",
  draft_approved: "Draft approved",
  draft_edited: "Draft edited and approved",
  draft_rejected: "Draft rejected — manual review needed",
  resolved: "Ticket resolved",
  failed: "Processing stopped — attention needed",
};
const TOOLS = {
  past_tickets_rag: "Similar past tickets",
  policies_rag: "Company policies",
  sql: "Account records",
};
const ACTIONS = {
  POLICY_RAG: "Check company policies",
  SQL: "Check account records",
  HUMAN_CLARIFICATION: "Ask for clarification",
  SYNTHESIS: "Write a response",
};
function summary(event) {
  const p = event.payload || {};
  if (event.event_type === "classified")
    return [p.category, p.priority]
      .filter(Boolean)
      .map(toTitleCase)
      .join(" · ");
  if (["tool_called", "tool_result"].includes(event.event_type))
    return TOOLS[p.tool_used] || toTitleCase(p.tool_used || "");
  if (event.event_type === "supervisor_decision")
    return ACTIONS[p.next_action] || toTitleCase(p.next_action || "");
  if (event.event_type === "clarification_requested")
    return p.question || p.clarification_question;
  if (event.event_type === "clarification_answered") return p.answer;
  return p.reason || p.message;
}
function EventItem({ event, newest }) {
  return (
    <li className="relative pl-8 pb-8 last:pb-0">
      <span
        className={`absolute left-0 top-1.5 h-2.5 w-2.5 rounded-full ring-4 ring-[#12161E] ${newest ? "bg-[#818CF8]" : "bg-[#384152]"}`}
      />
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="text-sm font-medium text-[#E7E9EE]">
          {LABELS[event.event_type] || toTitleCase(event.event_type)}
        </p>
        <time
          dateTime={event.created_at}
          title={new Date(event.created_at).toLocaleString()}
          className="text-xs tabular-nums text-[#8A93A6]"
        >
          {new Date(event.created_at).toLocaleString([], {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </time>
      </div>
      {summary(event) && (
        <p className="mt-2 text-sm leading-relaxed text-[#8A93A6]">
          {summary(event)}
        </p>
      )}
      {event.payload && Object.keys(event.payload).length > 0 && (
        <details className="mt-3 text-xs text-[#8A93A6]">
          <summary className="w-fit cursor-pointer rounded py-1 text-[#818CF8] focus-visible:outline-2 focus-visible:outline-[#818CF8]">
            Event details
          </summary>
          <div className="mt-3 space-y-4 rounded-lg border border-[#262C38] bg-[#0E1116] p-4">
            {Object.entries(event.payload).map(([key, value]) => (
              <div key={key}>
                <p className="mb-1 font-medium">{toTitleCase(key)}</p>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-[#CBD1DD]">
                  {typeof value === "string"
                    ? value
                    : JSON.stringify(value, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </details>
      )}
    </li>
  );
}
function TicketOutput({ ticketId, revision, status }) {
  const [data, setData] = useState({
    ticketId: null,
    drafts: [],
    resolution: null,
    error: "",
  });
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchTicketDrafts(ticketId),
      status === "resolved"
        ? fetchTicketResolution(ticketId)
        : Promise.resolve(null),
    ])
      .then(([drafts, resolution]) => {
        if (!cancelled) setData({ ticketId, drafts, resolution, error: "" });
      })
      .catch((err) => {
        if (!cancelled)
          setData({
            ticketId,
            drafts: [],
            resolution: null,
            error: err.message,
          });
      });
    return () => {
      cancelled = true;
    };
  }, [ticketId, revision, status]);
  if (data.ticketId !== ticketId) return null;
  return (
    <>
      {data.error && (
        <p role="alert" className="mt-4 text-sm text-[#F2665A]">
          {data.error}
        </p>
      )}
      {(data.drafts.length > 0 || data.resolution) && (
        <details className="mt-6 border-t border-[#262C38] pt-5">
          <summary className="cursor-pointer text-sm text-[#818CF8]">
            Drafts & resolution
          </summary>
          <div className="mt-5 space-y-6 text-sm leading-relaxed">
            {data.resolution && (
              <div>
                <p className="mb-2 font-medium text-[#34D399]">
                  Final resolution
                </p>
                <p className="whitespace-pre-wrap text-[#CBD1DD]">
                  {data.resolution.resolutionText}
                </p>
              </div>
            )}
            {data.drafts.map((draft) => (
              <div key={draft.id}>
                <p className="mb-2 font-medium">
                  Draft #{draft.id} · {toTitleCase(draft.status)}
                </p>
                <p className="whitespace-pre-wrap text-[#CBD1DD]">
                  {draft.draftText}
                </p>
                {draft.analysis && (
                  <details className="mt-3">
                    <summary className="cursor-pointer text-[#8A93A6]">
                      Agent analysis
                    </summary>
                    <pre className="mt-3 overflow-auto whitespace-pre-wrap break-words font-sans text-[#8A93A6]">
                      {typeof draft.analysis === "string"
                        ? draft.analysis
                        : JSON.stringify(draft.analysis, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        </details>
      )}
    </>
  );
}
export default function LiveTrace() {
  const { tickets, loading: ticketsLoading } = useDashboard();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const requestedId = params.get("ticketId");
  const selectedId = requestedId ? Number(requestedId) : tickets[0]?.id;
  const ticket = tickets.find((row) => row.id === selectedId);
  const { events, loading, error, connectionStatus } = useTicketWebSocket(
    ticket?.id,
  );
  const latest = events.at(-1);
  const status = ticket?.status;
  const style = STATUS_STYLES[status] || STATUS_STYLES.queued;
  const visible = tickets.filter(
    (row) =>
      (filter === "all" ||
        (filter === "resolved"
          ? row.status === "resolved"
          : row.status !== "resolved")) &&
      `${row.id} ${row.subject} ${row.customerName}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const steps = ["Received", "Agent working", "Human review", "Resolved"];
  const stage =
    status === "resolved"
      ? 3
      : [
            "awaiting_approval",
            "awaiting_clarification",
            "needs_manual_review",
            "failed",
          ].includes(status)
        ? 2
        : status === "processing"
          ? 1
          : 0;
  const idleActivity = {
    queued: "Waiting for the worker to pick up this ticket",
    awaiting_approval: "Response ready — review it before sending",
    awaiting_clarification: "The agent needs an answer before it can continue",
    needs_manual_review: "A human needs to review and resolve this ticket",
    failed: "The agent stopped — open needs attention to resolve it",
    resolved: "Resolution saved — the complete history is available below",
  };
  const activity = status === "processing" && latest
    ? summary(latest) || LABELS[latest.event_type]
    : idleActivity[status] || style.label;
  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Live trace
        </h2>
        <p className="mt-2 text-sm text-[#8A93A6]">
          Follow the agent’s work, or revisit any ticket’s history.
        </p>
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside
          className="rounded-xl border border-[#262C38] bg-[#12161E] p-4"
          aria-label="Ticket history selector"
        >
          <label
            htmlFor="trace-search"
            className="mb-3 block text-xs font-medium uppercase tracking-wider text-[#8A93A6]"
          >
            Tickets · {tickets.length}
          </label>
          <input
            id="trace-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search subject, customer or ID"
            className="w-full rounded-lg border border-[#262C38] bg-[#0E1116] px-3 py-2.5 text-sm outline-none placeholder:text-[#5B6472] focus:border-[#818CF8]"
          />
          <div className="mt-3 flex gap-1" aria-label="Filter tickets">
            {[
              ["all", "All"],
              ["active", "Active"],
              ["resolved", "Resolved"],
            ].map(([key, label]) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                aria-pressed={filter === key}
                className={`flex-1 rounded-md py-2 text-xs ${filter === key ? "bg-[#818CF8]/12 text-[#ADB5FC]" : "text-[#8A93A6] hover:bg-white/5"}`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-4 max-h-64 space-y-1 overflow-y-auto lg:max-h-[65vh]">
            {ticketsLoading ? (
              <p className="p-3 text-sm text-[#8A93A6]">Loading tickets…</p>
            ) : visible.length === 0 ? (
              <p className="p-3 text-sm text-[#8A93A6]">No matching tickets.</p>
            ) : (
              visible.map((row) => (
                <button
                  key={row.id}
                  onClick={() => setParams({ ticketId: row.id })}
                  aria-pressed={row.id === selectedId}
                  className={`w-full rounded-lg px-3 py-4 text-left ${row.id === selectedId ? "bg-[#818CF8]/10 ring-1 ring-inset ring-[#818CF8]/25" : "hover:bg-white/5"}`}
                >
                  <p className="text-xs text-[#8A93A6]">
                    #{row.id} ·{" "}
                    {STATUS_STYLES[row.status]?.label ||
                      toTitleCase(row.status)}
                  </p>
                  <p className="mt-2 truncate text-sm font-medium">
                    {row.subject}
                  </p>
                  <p className="mt-1 truncate text-xs text-[#8A93A6]">
                    {row.customerName}
                  </p>
                </button>
              ))
            )}
          </div>
        </aside>
        {!ticket ? (
          <div className="rounded-xl border border-[#262C38] bg-[#12161E] px-6 py-16 text-center text-sm text-[#8A93A6]">
            {ticketsLoading
              ? "Loading ticket…"
              : requestedId
                ? "This ticket is unavailable in your queue. Choose another ticket to view its history."
                : "Your tickets will appear here after a complaint is submitted."}
          </div>
        ) : (
          <section
            key={ticket.id}
            className="min-w-0 rounded-xl border border-[#262C38] bg-[#12161E] p-6 sm:p-8"
            aria-label="Selected ticket trace"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-[#8A93A6]">
                Ticket #{ticket.id} · {ticket.customerName}
              </p>
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium ${style.pill}`}
              >
                {style.label}
              </span>
            </div>
            <h3 className="mt-4 break-words text-xl font-medium leading-relaxed">
              {ticket.subject}
            </h3>
            <details className="mt-3 text-sm text-[#8A93A6]">
              <summary className="w-fit cursor-pointer">
                Original complaint
              </summary>
              <p className="mt-3 whitespace-pre-wrap leading-relaxed">
                {ticket.description}
              </p>
            </details>
            <ol
              className="my-8 grid grid-cols-4 gap-3"
              aria-label="Ticket progress"
            >
              {steps.map((label, index) => (
                <li
                  key={label}
                  aria-current={index === stage ? "step" : undefined}
                  className={`border-t-2 pt-3 text-xs leading-relaxed ${index <= stage ? "border-[#818CF8] text-[#ADB5FC]" : "border-[#262C38] text-[#5B6472]"}`}
                >
                  {label}
                </li>
              ))}
            </ol>
            <div className="flex items-center gap-3 rounded-lg bg-[#0E1116] px-4 py-4">
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${status === "processing" ? "animate-pulse bg-[#818CF8]" : status === "resolved" ? "bg-[#34D399]" : "bg-[#F5B843]"}`}
              />
              <div className="min-w-0">
                <p className="text-sm text-[#CBD1DD]">{activity}</p>
                <p className="mt-1 text-xs text-[#8A93A6]">
                  {latest
                    ? `Last activity ${timeAgo(latest.created_at)}`
                    : "Waiting for the worker to pick up this ticket"}
                </p>
              </div>
            </div>
            {stage === 2 && (
              <Link
                to={
                  status === "awaiting_approval"
                    ? "/dashboard/awaiting-review"
                    : "/dashboard/needs-attention"
                }
                className="mt-4 inline-block text-sm text-[#818CF8] hover:underline"
              >
                {status === "awaiting_approval"
                  ? "Review the response"
                  : "Open needs attention"}{" "}
                →
              </Link>
            )}
            <div className="mt-10 flex flex-wrap items-center justify-between gap-2 border-b border-[#262C38] pb-4">
              <h4 className="text-sm font-medium">
                Activity history{" "}
                <span className="ml-2 text-[#8A93A6]">{events.length}</span>
              </h4>
              <p className="flex items-center gap-2 text-xs text-[#8A93A6]">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${connectionStatus === "connected" ? "bg-[#34D399]" : "bg-[#F5B843]"}`}
                />
                {connectionStatus === "connected"
                  ? "Live · latest first"
                  : connectionStatus === "unauthorized"
                    ? "Live connection unavailable"
                    : "Reconnecting · refreshing automatically"}
              </p>
            </div>
            {error && (
              <p role="alert" className="mt-5 text-sm text-[#F2665A]">
                {error}
              </p>
            )}
            {loading ? (
              <p className="py-8 text-sm text-[#8A93A6]">Loading history…</p>
            ) : events.length === 0 ? (
              <p className="py-8 text-sm text-[#8A93A6]">
                No activity recorded yet.
              </p>
            ) : (
              <ol
                className="relative mt-8 before:absolute before:bottom-3 before:left-[4px] before:top-2 before:w-px before:bg-[#262C38]"
                aria-label="Activity history"
              >
                {[...events].reverse().map((event, index) => (
                  <EventItem
                    key={event.id}
                    event={event}
                    newest={index === 0}
                  />
                ))}
              </ol>
            )}
            <TicketOutput
              ticketId={ticket.id}
              revision={latest?.id}
              status={status}
            />
          </section>
        )}
      </div>
    </div>
  );
}
