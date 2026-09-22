import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import useTicketWebSocket from "../hooks/useTicketWebSocket";
import {
  API_BASE,
  authHeaders,
} from "../components/dashboard/api";

const NODE_LABELS = {
  "Classify-ticket-node": "Classify ticket",
  "Rag-past-event-node": "Past tickets RAG",
  "Rag-policy-node": "Policy RAG",
  "SQL-node": "SQL lookup",
  "Supervisor-node": "Supervisor",
  "Human-assistance-node": "Human assistance",
  "Synthesizer-node": "Response synthesizer",
};

const NODE_DESCRIPTIONS = {
  "Classify-ticket-node":
    "Analyzing and classifying the incoming ticket",
  "Rag-past-event-node":
    "Searching historical ticket data",
  "Rag-policy-node":
    "Retrieving relevant company policies",
  "SQL-node":
    "Querying structured ticket information",
  "Supervisor-node":
    "Evaluating the next action",
  "Human-assistance-node":
    "Waiting for human clarification",
  "Synthesizer-node":
    "Generating the final response",
};

const NODE_ORDER = [
  "Classify-ticket-node",
  "Rag-past-event-node",
  "Rag-policy-node",
  "SQL-node",
  "Supervisor-node",
  "Human-assistance-node",
  "Synthesizer-node",
];

function formatNodeName(node) {
  if (!node) return "Unknown node";

  return (
    NODE_LABELS[node] ??
    node.replace(/-node$/, "").replace(/-/g, " ")
  );
}

function formatEventName(eventType) {
  if (!eventType) return "Unknown event";

  return eventType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTime(timestamp) {
  if (!timestamp) return "--:--:--";

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return String(timestamp);
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDate(timestamp) {
  if (!timestamp) return "";

  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleDateString([], {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatPayload(payload) {
  if (!payload) return null;

  if (typeof payload === "string") {
    return payload;
  }

  try {
    return JSON.stringify(payload, null, 2);
  } catch {
    return String(payload);
  }
}

function getEventNode(event) {
  if (!event) return null;

  const payload = event.payload ?? {};

  return (
    payload.node ??
    payload.node_name ??
    payload.active_node ??
    payload.tool_node ??
    null
  );
}

function getEventDescription(event) {
  if (!event) return "";

  const payload = event.payload ?? {};

  return (
    payload.message ??
    payload.description ??
    payload.reason ??
    payload.content ??
    ""
  );
}

function getEventTimestamp(event) {
  return (
    event?.timestamp ??
    event?.created_at ??
    event?.time ??
    event?.occurred_at ??
    null
  );
}

function StatusBadge({ status }) {
  const config = {
    connecting: {
      label: "Connecting",
      className: "bg-[#F5B843]/10 text-[#F5B843]",
      dot: "bg-[#F5B843]",
    },

    connected: {
      label: "Live",
      className: "bg-[#34D399]/10 text-[#34D399]",
      dot: "bg-[#34D399]",
    },

    closed: {
      label: "History loaded",
      className: "bg-white/5 text-[#8A93A6]",
      dot: "bg-[#8A93A6]",
    },

    error: {
      label: "Connection error",
      className: "bg-[#F2665A]/10 text-[#F2665A]",
      dot: "bg-[#F2665A]",
    },
  };

  const current =
    config[status] ?? config.connecting;

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium ${current.className}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${current.dot}`}
      />

      {current.label}
    </span>
  );
}

function NodeIcon({
  node,
  activeNode,
  completedNodes,
}) {
  const isActive = node === activeNode;
  const isCompleted = completedNodes.includes(node);

  if (isCompleted) {
    return (
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[#34D399]/30 bg-[#34D399]/10 text-[#34D399]">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className="h-4 w-4"
        >
          <path d="m5 12 4 4L19 6" />
        </svg>
      </div>
    );
  }

  if (isActive) {
    return (
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[#818CF8]/50 bg-[#818CF8]/15">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#818CF8]" />
      </div>
    );
  }

  return (
    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-[#262C38] bg-[#0E1116]">
      <span className="h-2 w-2 rounded-full bg-[#5B6472]" />
    </div>
  );
}

function EventItem({ event, index }) {
  const eventNode = getEventNode(event);
  const description = getEventDescription(event);
  const payload = formatPayload(event?.payload);

  return (
    <div className="relative flex gap-3">
      <div className="flex w-7 shrink-0 flex-col items-center">
        <div className="flex h-7 w-7 items-center justify-center rounded-full border border-[#262C38] bg-[#161A22] text-[10px] font-semibold text-[#8A93A6]">
          {index + 1}
        </div>

        <div className="mt-2 h-full min-h-5 w-px bg-[#262C38]" />
      </div>

      <div className="min-w-0 flex-1 pb-5">
        <div className="rounded-lg border border-[#262C38] bg-[#161A22] px-4 py-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-medium text-[#E7E9EE]">
                {formatEventName(event?.event_type)}
              </p>

              {eventNode && (
                <p className="mt-1 text-xs text-[#818CF8]">
                  {formatNodeName(eventNode)}
                </p>
              )}
            </div>

            <span className="shrink-0 text-[11px] tabular-nums text-[#5B6472]">
              {formatTime(getEventTimestamp(event))}
            </span>
          </div>

          {description && (
            <p className="mt-3 text-sm leading-relaxed text-[#8A93A6]">
              {typeof description === "string"
                ? description
                : JSON.stringify(description)}
            </p>
          )}

          {payload && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-[#5B6472] transition-colors hover:text-[#8A93A6]">
                View payload
              </summary>

              <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-md border border-[#262C38] bg-[#0E1116] p-3 font-mono text-[11px] leading-relaxed text-[#8A93A6]">
                {payload}
              </pre>
            </details>
          )}
        </div>
      </div>
    </div>
  );
}

function EmptyTimeline() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#262C38] bg-[#161A22] px-6 py-14 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-[#5B6472]">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          className="h-5 w-5"
        >
          <path d="M3 12h4l3-8 4 16 3-8h4" />
        </svg>
      </div>

      <p className="mt-4 text-sm font-medium text-[#E7E9EE]">
        No execution events
      </p>

      <p className="mt-1 max-w-sm text-xs leading-relaxed text-[#5B6472]">
        This ticket does not have any recorded agent events.
      </p>
    </div>
  );
}

export default function LiveTrace() {
  const [searchParams, setSearchParams] =
    useSearchParams();

  const urlTicketId = searchParams.get("ticketId");

  const [tickets, setTickets] = useState([]);
  const [selectedTicketId, setSelectedTicketId] =
    useState(urlTicketId);

  const [loadingTickets, setLoadingTickets] =
    useState(true);

  const [ticketError, setTicketError] =
    useState("");

  const [search, setSearch] = useState("");

  /*
   * Load every resolved ticket.
   */
  async function loadCompletedTickets() {
    try {
      setTicketError("");

      const res = await fetch(
        `${API_BASE}/tickets/completed`,
        {
          headers: authHeaders(),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data?.detail ||
            "Failed to load completed tickets"
        );
      }

      const completed = Array.isArray(data)
        ? data
        : [];

      completed.sort(
        (a, b) =>
          new Date(b.created_at).getTime() -
          new Date(a.created_at).getTime()
      );

      setTickets(completed);

      /*
       * If the URL already contains a ticket ID and that ticket
       * exists, keep it selected.
       *
       * Otherwise automatically select the newest completed ticket.
       */
      const urlMatch = completed.find(
        (ticket) =>
          String(ticket.id) === String(urlTicketId)
      );

      if (urlMatch) {
        setSelectedTicketId(String(urlMatch.id));
        return;
      }

      if (completed.length > 0) {
        const newest = completed[0];

        setSelectedTicketId(String(newest.id));

        setSearchParams(
          {
            ticketId: String(newest.id),
          },
          {
            replace: true,
          }
        );
      } else {
        setSelectedTicketId(null);
      }
    } catch (error) {
      console.error(
        "Failed to load completed tickets:",
        error
      );

      setTicketError(
        error.message ||
          "Failed to load completed tickets."
      );
    } finally {
      setLoadingTickets(false);
    }
  }

  useEffect(() => {
    loadCompletedTickets();

    /*
     * Automatically refresh the completed-ticket list.
     * This means a newly resolved ticket will appear
     * without requiring a full page refresh.
     */
    const interval = setInterval(
      loadCompletedTickets,
      10000
    );

    return () => clearInterval(interval);
  }, [urlTicketId]);

  /*
   * Select the ticket from the left-hand list.
   */
  function selectTicket(ticketId) {
    const id = String(ticketId);

    setSelectedTicketId(id);

    setSearchParams(
      {
        ticketId: id,
      },
      {
        replace: true,
      }
    );
  }

  const selectedTicket = useMemo(
    () =>
      tickets.find(
        (ticket) =>
          String(ticket.id) ===
          String(selectedTicketId)
      ) ?? null,
    [tickets, selectedTicketId]
  );

  const filteredTickets = useMemo(() => {
    const query = search
      .trim()
      .toLowerCase();

    if (!query) return tickets;

    return tickets.filter((ticket) => {
      return (
        String(ticket.id)
          .toLowerCase()
          .includes(query) ||
        ticket.subject
          ?.toLowerCase()
          .includes(query) ||
        ticket.description
          ?.toLowerCase()
          .includes(query)
      );
    });
  }, [tickets, search]);

  /*
   * This is the actual live/history connection.
   *
   * For a completed ticket, the websocket first returns
   * the complete DB history, then remains available for
   * any further events.
   */
  const {
    events,
    activeNode,
    completedNodes,
    connectionStatus,
  } = useTicketWebSocket(selectedTicketId);

  const completedCount =
    completedNodes.length;

  const knownNodes = useMemo(() => {
    const nodes = [...NODE_ORDER];

    events.forEach((event) => {
      const node = getEventNode(event);

      if (node && !nodes.includes(node)) {
        nodes.push(node);
      }
    });

    if (
      activeNode &&
      !nodes.includes(activeNode)
    ) {
      nodes.push(activeNode);
    }

    completedNodes.forEach((node) => {
      if (
        node &&
        !nodes.includes(node)
      ) {
        nodes.push(node);
      }
    });

    return nodes;
  }, [
    events,
    activeNode,
    completedNodes,
  ]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wider text-[#5B6472]">
              Execution
            </span>

            <span className="text-xs text-[#5B6472]">
              /
            </span>

            <span className="text-xs font-medium text-[#8A93A6]">
              Completed tickets
            </span>
          </div>

          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#E7E9EE] sm:text-3xl">
            Live agent trace
          </h2>

          <p className="mt-1 text-sm text-[#8A93A6]">
            Select a completed ticket to inspect its
            complete agent execution history.
          </p>
        </div>

        <button
          onClick={() => {
            setLoadingTickets(true);
            loadCompletedTickets();
          }}
          disabled={loadingTickets}
          className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#262C38] bg-[#161A22] px-4 py-2 text-sm font-medium text-[#C7CBD4] transition hover:border-[#3A4250] hover:bg-[#1B2029] disabled:cursor-not-allowed disabled:opacity-50"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className={`h-4 w-4 ${
              loadingTickets
                ? "animate-spin"
                : ""
            }`}
          >
            <path d="M20 11a8.1 8.1 0 0 0-14.9-4M4 5v4h4M4 13a8.1 8.1 0 0 0 14.9 4M20 19v-4h-4" />
          </svg>

          Refresh
        </button>
      </div>

      {ticketError && (
        <div className="rounded-xl border border-[#F2665A]/20 bg-[#F2665A]/5 px-5 py-4">
          <p className="text-sm font-medium text-[#F2665A]">
            Could not load tickets
          </p>

          <p className="mt-1 text-sm text-[#8A93A6]">
            {ticketError}
          </p>
        </div>
      )}

      {/* Main split view */}
      <div className="grid min-h-[650px] grid-cols-1 overflow-hidden rounded-xl border border-[#262C38] bg-[#0E1116] xl:grid-cols-[340px_minmax(0,1fr)]">
        {/* Ticket list */}
        <aside className="border-b border-[#262C38] bg-[#12161D] xl:border-b-0 xl:border-r">
          <div className="border-b border-[#262C38] p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-[#E7E9EE]">
                  Completed tickets
                </p>

                <p className="mt-1 text-xs text-[#5B6472]">
                  {tickets.length}{" "}
                  {tickets.length === 1
                    ? "ticket"
                    : "tickets"}
                </p>
              </div>

              <span className="rounded-full bg-[#34D399]/10 px-2.5 py-1 text-xs font-medium text-[#34D399]">
                Resolved
              </span>
            </div>

            {/* Search */}
            <div className="relative mt-4">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#5B6472]"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-4-4" />
              </svg>

              <input
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search tickets..."
                className="w-full rounded-lg border border-[#262C38] bg-[#0E1116] py-2.5 pl-9 pr-3 text-xs text-[#E7E9EE] outline-none placeholder:text-[#4F5867] focus:border-[#818CF8]/50"
              />
            </div>
          </div>

          {/* Tickets */}
          <div className="max-h-[650px] overflow-y-auto">
            {loadingTickets &&
            tickets.length === 0 ? (
              <div className="space-y-2 p-3">
                {[1, 2, 3, 4].map(
                  (item) => (
                    <div
                      key={item}
                      className="animate-pulse rounded-lg border border-[#262C38] bg-[#161A22] p-4"
                    >
                      <div className="h-3 w-16 rounded bg-[#262C38]" />
                      <div className="mt-3 h-3 w-4/5 rounded bg-[#262C38]" />
                      <div className="mt-2 h-2 w-2/3 rounded bg-[#262C38]" />
                    </div>
                  )
                )}
              </div>
            ) : filteredTickets.length === 0 ? (
              <div className="px-5 py-12 text-center">
                <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-[#5B6472]">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    className="h-5 w-5"
                  >
                    <path d="M4 6h16v12H4z" />
                    <path d="M8 10h8M8 14h5" />
                  </svg>
                </div>

                <p className="mt-4 text-sm font-medium text-[#E7E9EE]">
                  No completed tickets
                </p>

                <p className="mt-1 text-xs leading-relaxed text-[#5B6472]">
                  Resolved tickets will appear here
                  automatically.
                </p>
              </div>
            ) : (
              filteredTickets.map(
                (ticket) => {
                  const selected =
                    String(ticket.id) ===
                    String(selectedTicketId);

                  return (
                    <button
                      key={ticket.id}
                      onClick={() =>
                        selectTicket(
                          ticket.id
                        )
                      }
                      className={`w-full border-b border-[#262C38] px-4 py-4 text-left transition ${
                        selected
                          ? "bg-[#1A1F2E]"
                          : "hover:bg-[#161A22]"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <span
                          className={`text-[11px] font-semibold ${
                            selected
                              ? "text-[#A5AEFF]"
                              : "text-[#5B6472]"
                          }`}
                        >
                          TICKET #{ticket.id}
                        </span>

                        <span className="shrink-0 text-[10px] text-[#5B6472]">
                          {formatDate(
                            ticket.created_at
                          )}
                        </span>
                      </div>

                      <p className="mt-2 line-clamp-2 text-sm font-medium leading-snug text-[#E7E9EE]">
                        {ticket.subject}
                      </p>

                      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-[#687282]">
                        {ticket.description}
                      </p>

                      <div className="mt-3 flex items-center gap-2">
                        <span className="rounded-md bg-[#34D399]/10 px-2 py-1 text-[10px] font-medium text-[#34D399]">
                          Resolved
                        </span>

                        {ticket.category && (
                          <span className="truncate rounded-md bg-white/5 px-2 py-1 text-[10px] text-[#687282]">
                            {String(
                              ticket.category
                            ).replace(
                              /_/g,
                              " "
                            )}
                          </span>
                        )}
                      </div>
                    </button>
                  );
                }
              )
            )}
          </div>
        </aside>

        {/* Trace */}
        <main className="min-w-0 bg-[#0E1116]">
          {!selectedTicket ? (
            <div className="flex h-full min-h-[650px] items-center justify-center px-6">
              <div className="max-w-md text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5 text-[#5B6472]">
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    className="h-6 w-6"
                  >
                    <path d="M3 12h4l3-8 4 16 3-8h4" />
                  </svg>
                </div>

                <h3 className="mt-5 text-base font-semibold text-[#E7E9EE]">
                  Select a completed ticket
                </h3>

                <p className="mt-2 text-sm leading-relaxed text-[#5B6472]">
                  Choose a ticket from the list to
                  inspect its complete execution
                  history.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-5 sm:p-6">
              {/* Selected ticket header */}
              <div className="border-b border-[#262C38] pb-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium uppercase tracking-wider text-[#5B6472]">
                        Ticket #{selectedTicket.id}
                      </span>

                      <span className="text-xs text-[#5B6472]">
                        /
                      </span>

                      <span className="text-xs text-[#34D399]">
                        Resolved
                      </span>
                    </div>

                    <h3 className="mt-2 text-xl font-semibold text-[#E7E9EE]">
                      {selectedTicket.subject}
                    </h3>

                    <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#8A93A6]">
                      {selectedTicket.description}
                    </p>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {selectedTicket.category && (
                        <span className="rounded-md bg-white/5 px-2.5 py-1 text-[11px] text-[#8A93A6]">
                          Category:{" "}
                          {String(
                            selectedTicket.category
                          ).replace(
                            /_/g,
                            " "
                          )}
                        </span>
                      )}

                      {selectedTicket.priority && (
                        <span className="rounded-md bg-white/5 px-2.5 py-1 text-[11px] text-[#8A93A6]">
                          Priority:{" "}
                          {String(
                            selectedTicket.priority
                          )}
                        </span>
                      )}
                    </div>
                  </div>

                  <StatusBadge
                    status={connectionStatus}
                  />
                </div>
              </div>

              {/* Summary */}
              <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-lg border border-[#262C38] bg-[#161A22] px-4 py-3">
                  <p className="text-[11px] text-[#5B6472]">
                    Events
                  </p>

                  <p className="mt-1 text-lg font-semibold tabular-nums text-[#E7E9EE]">
                    {events.length}
                  </p>
                </div>

                <div className="rounded-lg border border-[#262C38] bg-[#161A22] px-4 py-3">
                  <p className="text-[11px] text-[#5B6472]">
                    Completed nodes
                  </p>

                  <p className="mt-1 text-lg font-semibold tabular-nums text-[#E7E9EE]">
                    {completedCount}
                  </p>
                </div>

                <div className="rounded-lg border border-[#262C38] bg-[#161A22] px-4 py-3">
                  <p className="text-[11px] text-[#5B6472]">
                    Created
                  </p>

                  <p className="mt-1 text-sm font-semibold text-[#E7E9EE]">
                    {formatDate(
                      selectedTicket.created_at
                    )}
                  </p>
                </div>
              </div>

              {/* Trace */}
              <div className="mt-6 grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_270px]">
                {/* Event timeline */}
                <section className="min-w-0">
                  <div className="mb-3 flex items-center justify-between">
                    <h4 className="text-base font-semibold text-[#E7E9EE]">
                      Complete event history
                    </h4>

                    <span className="text-xs text-[#5B6472]">
                      {events.length}{" "}
                      {events.length === 1
                        ? "event"
                        : "events"}
                    </span>
                  </div>

                  {events.length === 0 ? (
                    <EmptyTimeline />
                  ) : (
                    <div className="rounded-xl border border-[#262C38] bg-[#0E1116] p-4 sm:p-5">
                      {events.map(
                        (event, index) => (
                          <EventItem
                            key={`${
                              event?.id ??
                              event?.event_type ??
                              "event"
                            }-${index}`}
                            event={event}
                            index={index}
                          />
                        )
                      )}
                    </div>
                  )}
                </section>

                {/* Workflow */}
                <section>
                  <div className="mb-3 flex items-center justify-between">
                    <h4 className="text-base font-semibold text-[#E7E9EE]">
                      Agent workflow
                    </h4>

                    <span className="text-xs text-[#5B6472]">
                      {completedCount}/
                      {knownNodes.length}
                    </span>
                  </div>

                  <div className="rounded-xl border border-[#262C38] bg-[#161A22] p-4">
                    <div className="space-y-1">
                      {knownNodes.map(
                        (node, index) => {
                          const isLast =
                            index ===
                            knownNodes.length -
                              1;

                          return (
                            <div
                              key={node}
                            >
                              <div className="flex items-center gap-3 rounded-lg px-2 py-3">
                                <NodeIcon
                                  node={node}
                                  activeNode={
                                    activeNode
                                  }
                                  completedNodes={
                                    completedNodes
                                  }
                                />

                                <div className="min-w-0 flex-1">
                                  <p className="text-sm font-medium text-[#E7E9EE]">
                                    {formatNodeName(
                                      node
                                    )}
                                  </p>

                                  <p className="mt-0.5 text-[11px] leading-relaxed text-[#5B6472]">
                                    {NODE_DESCRIPTIONS[
                                      node
                                    ] ??
                                      "Agent workflow node"}
                                  </p>
                                </div>
                              </div>

                              {!isLast && (
                                <div className="ml-[25px] h-3 w-px bg-[#262C38]" />
                              )}
                            </div>
                          );
                        }
                      )}
                    </div>

                    {activeNode && (
                      <div className="mt-4 border-t border-[#262C38] pt-4">
                        <p className="text-[10px] font-medium uppercase tracking-wider text-[#5B6472]">
                          Currently running
                        </p>

                        <p className="mt-1 text-sm font-medium text-[#A5AEFF]">
                          {formatNodeName(
                            activeNode
                          )}
                        </p>
                      </div>
                    )}

                    {!activeNode &&
                      completedCount > 0 && (
                        <div className="mt-4 border-t border-[#262C38] pt-4">
                          <p className="text-xs text-[#34D399]">
                            Agent execution
                            complete.
                          </p>
                        </div>
                      )}
                  </div>
                </section>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}