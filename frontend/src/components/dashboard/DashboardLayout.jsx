import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { fetchCurrentUser, fetchTickets } from "./api";
import { bucketTickets } from "./ticketBuckets";

const PAGE_TITLES = {
  "/dashboard": "Overview",
  "/dashboard/unprocessed": "Unprocessed queue",
  "/dashboard/awaiting-review": "Awaiting your review",
  "/dashboard/needs-attention": "Needs attention",
  "/dashboard/resolved": "Resolved",
  "/dashboard/liveTrace": "Live agent trace",
  "/dashboard/team": "Team",
  "/dashboard/settings": "Settings",
};

const EMPTY_BUCKETS = {
  unprocessed: [],
  awaitingReview: [],
  needsAttention: [],
  resolved: [],
};

export default function DashboardLayout({ onLogout = () => {} }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [tickets, setTickets] = useState([]);
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] ?? "Overview";

  useEffect(() => {
    let cancelled = false;

    async function loadDashboardContext() {
      try {
        const [currentUser, currentTickets] = await Promise.all([
          fetchCurrentUser(),
          fetchTickets(),
        ]);

        if (cancelled) return;
        setUser(currentUser);
        setTickets(currentTickets);
      } catch (error) {
        if (cancelled) return;
        console.error("Failed to load dashboard context:", error);
      }
    }

    loadDashboardContext();
    const interval = setInterval(loadDashboardContext, 10000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const buckets = tickets.length ? bucketTickets(tickets) : EMPTY_BUCKETS;
  const currentUser = user
    ? { name: user.username, role: user.role }
    : { name: "", role: "viewer" };

  return (
    <div className="flex h-screen bg-[#0E1116] text-[#E7E9EE]">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        role={currentUser.role}
        counts={{
          unprocessed: buckets.unprocessed.length,
          awaitingReview: buckets.awaitingReview.length,
          needsAttention: buckets.needsAttention.length,
        }}
        onSignOut={onLogout}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onMenuClick={() => setSidebarOpen(true)}
          pageTitle={pageTitle}
          user={currentUser}
        />

        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
