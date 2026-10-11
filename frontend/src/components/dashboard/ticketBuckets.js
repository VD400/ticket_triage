export function bucketTickets(tickets) {
  return {
    unprocessed: tickets.filter((t) => ["queued", "processing"].includes(t.status)),
    awaitingReview: tickets.filter((t) => t.status === "awaiting_approval"),
    needsAttention: tickets.filter((t) => ["needs_manual_review", "awaiting_clarification"].includes(t.status)),
    resolved: tickets.filter((t) => t.status === "resolved"),
  };
}

export function toTitleCase(value = "") {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function timeAgo(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export const PRIORITY_STYLES = {
  low: "bg-white/5 text-[#9AA3B5]",
  medium: "bg-[#818CF8]/15 text-[#818CF8]",
  high: "bg-[#F5B843]/15 text-[#F5B843]",
  urgent: "bg-[#F2665A]/15 text-[#F2665A]",
};

export const STATUS_STYLES = {
  queued: { label: "Queued", pill: "bg-white/5 text-[#9AA3B5]" },
  processing: { label: "Processing", pill: "bg-[#818CF8]/15 text-[#818CF8]" },
  awaiting_approval: { label: "Awaiting review", pill: "bg-[#F5B843]/15 text-[#F5B843]" },
  needs_manual_review: { label: "Needs manual review", pill: "bg-[#F2665A]/15 text-[#F2665A]" },
  awaiting_clarification: { label: "Awaiting clarification", pill: "bg-[#F2665A]/15 text-[#F2665A]" },
  resolved: { label: "Resolved", pill: "bg-[#34D399]/15 text-[#34D399]" },
  failed: { label: "Failed", pill: "bg-[#F2665A]/15 text-[#F2665A]" },
};