import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import StatCard from "../components/dashboard/StatCard";
import AttentionQueue from "../components/dashboard/AttentionQueue";
import {
  ClockIcon,
  InboxIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
} from "../components/dashboard/icons";
import { fetchCurrentUser, fetchTickets } from "../components/dashboard/api";
import { bucketTickets } from "../components/dashboard/ticketBuckets";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

const EMPTY_BUCKETS = {
  unprocessed: [],
  awaitingReview: [],
  needsAttention: [],
  resolved: [],
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [user, setUser] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setError("");
        const [currentTickets, currentUser] = await Promise.all([
          fetchTickets(),
          fetchCurrentUser(),
        ]);

        if (cancelled) return;
        setTickets(currentTickets);
        setUser(currentUser);
      } catch (err) {
        if (cancelled) return;
        setError(err.message || "Failed to load dashboard data.");
      }
    }

    load();
    const interval = setInterval(load, 10000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const buckets = tickets.length ? bucketTickets(tickets) : EMPTY_BUCKETS;
  const firstName = user?.username?.split(" ")[0] || "there";

  return (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-[#E7E9EE] sm:text-3xl">
          {getGreeting()}, {firstName}
        </h2>

        <p className="mt-1 text-sm text-[#8A93A6]">
          Here's where things stand across your queue today.
        </p>
      </div>

      {error && (
        <div className="mb-5 rounded-xl border border-[#F2665A]/20 bg-[#F2665A]/5 px-4 py-3 text-sm text-[#F2665A]">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={InboxIcon}
          label="Awaiting your review"
          value={buckets.awaitingReview.length}
          helperText="Drafted by the agent, ready to check"
          accent="amber"
        />

        <StatCard
          icon={AlertTriangleIcon}
          label="Needs attention"
          value={buckets.needsAttention.length}
          helperText="Flagged for a human to step in"
          accent="coral"
        />

        <StatCard
          icon={ClockIcon}
          label="Not yet processed"
          value={buckets.unprocessed.length}
          helperText="Still in the queue or being classified"
          accent="slate"
        />

        <StatCard
          icon={CheckCircleIcon}
          label="Resolved"
          value={buckets.resolved.length}
          helperText="Closed and sent to the customer"
          accent="teal"
        />
      </div>

      <div className="mt-8">
        <h3 className="mb-3 text-base font-semibold text-[#E7E9EE]">
          Your queue
        </h3>

        <AttentionQueue
          ticketsByBucket={buckets}
          onOpenTicket={(ticket) => {
            navigate(`/dashboard/liveTrace?ticketId=${ticket.id}`);
          }}
        />
      </div>
    </>
  );
}
