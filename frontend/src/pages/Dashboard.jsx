import { useMemo } from "react";
import StatCard from "../components/dashboard/StatCard";
import AttentionQueue from "../components/dashboard/AttentionQueue";
import { ClockIcon, InboxIcon, AlertTriangleIcon, CheckCircleIcon } from "../components/dashboard/icons";
import { MOCK_TICKETS } from "../components/dashboard/mockTickets";
import { bucketTickets } from "../components/dashboard/ticketBuckets";

const MOCK_USER = { name: "Devika Menon" };

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function Dashboard() {
  const buckets = useMemo(() => bucketTickets(MOCK_TICKETS), []);
  const firstName = MOCK_USER.name.split(" ")[0];

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
        <h3 className="mb-3 text-base font-semibold text-[#E7E9EE]">Your queue</h3>
        <AttentionQueue
          ticketsByBucket={buckets}
          onOpenTicket={(ticket) => {
            console.log("open ticket", ticket.id);
          }}
        />
      </div>
    </>
  );
}