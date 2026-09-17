import { useMemo, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { MOCK_TICKETS } from "./mockTickets";
import { bucketTickets } from "./ticketBuckets";

const MOCK_USER = { name: "Devika Menon", role: "agent" };

const PAGE_TITLES = {
  "/dashboard": "Overview",
  "/dashboard/unprocessed": "Unprocessed queue",
  "/dashboard/awaiting-review": "Awaiting your review",
  "/dashboard/needs-attention": "Needs attention",
  "/dashboard/resolved": "Resolved",
  "/dashboard/live": "Live agent trace",
  "/dashboard/team": "Team",
  "/dashboard/settings": "Settings",
};

export default function DashboardLayout({ onLogout = () => {} }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const buckets = useMemo(() => bucketTickets(MOCK_TICKETS), []);
  const pageTitle = PAGE_TITLES[location.pathname] ?? "Overview";

  return (
    <div className="flex h-screen bg-[#0E1116] text-[#E7E9EE]">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        role={MOCK_USER.role}
        counts={{
          unprocessed: buckets.unprocessed.length,
          awaitingReview: buckets.awaitingReview.length,
          needsAttention: buckets.needsAttention.length,
        }}
        onSignOut={onLogout}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenuClick={() => setSidebarOpen(true)} pageTitle={pageTitle} user={MOCK_USER} />

        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}