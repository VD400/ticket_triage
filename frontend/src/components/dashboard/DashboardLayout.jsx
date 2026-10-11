import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import DashboardProvider from "./DashboardProvider";
import { useDashboard } from "./useDashboard";

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

export default function DashboardLayout(props) {
  return <DashboardProvider><DashboardShell {...props} /></DashboardProvider>;
}

function DashboardShell({ onLogout = () => {} }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user, buckets, error, connectionStatus, refresh } = useDashboard();
  const location = useLocation();
  const pageTitle = PAGE_TITLES[location.pathname] ?? "Overview";

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
            {error && <div role="alert" className="mb-5 flex items-center justify-between gap-4 rounded-lg border border-[#F2665A]/25 bg-[#F2665A]/5 px-4 py-3 text-sm text-[#F2665A]">{error}<button onClick={refresh} className="shrink-0 underline">Retry</button></div>}
            {connectionStatus !== "connected" && <p className="mb-4 text-xs text-[#8A93A6]">Live connection {connectionStatus}. Tickets refresh automatically every 5 seconds.</p>}
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
