import { NavLink } from "react-router-dom";
import {
  GridIcon,
  ClockIcon,
  InboxIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  ActivityIcon,
  UsersIcon,
  SettingsIcon,
  LogOutIcon,
  XIcon,
} from "./icons";

// Each workspace item maps 1:1 to a ticket bucket the agent cares about.
// `badgeKey` looks up a live count from the `counts` prop; `tone` picks
// the badge color when the count needs to stand out (e.g. flagged tickets).
const WORKSPACE_ITEMS = [
  { key: "overview", label: "Overview", to: "/dashboard", icon: GridIcon, end: true },
  { key: "unprocessed", label: "Unprocessed queue", to: "/dashboard/unprocessed", icon: ClockIcon, badgeKey: "unprocessed", tone: "slate" },
  { key: "awaitingReview", label: "Awaiting your review", to: "/dashboard/awaiting-review", icon: InboxIcon, badgeKey: "awaitingReview", tone: "amber" },
  { key: "needsAttention", label: "Needs attention", to: "/dashboard/needs-attention", icon: AlertTriangleIcon, badgeKey: "needsAttention", tone: "coral" },
  { key: "resolved", label: "Resolved", to: "/dashboard/resolved", icon: CheckCircleIcon },
  { key: "liveTrace", label: "Live agent trace", to: "/dashboard/live", icon: ActivityIcon },
];

const ACCOUNT_ITEMS = [
  { key: "team", label: "Team", to: "/dashboard/team", icon: UsersIcon, roles: ["admin"] },
  { key: "settings", label: "Settings", to: "/dashboard/settings", icon: SettingsIcon },
];

const BADGE_TONES = {
  slate: "bg-white/5 text-[#9AA3B5]",
  amber: "bg-[#F5B843]/15 text-[#F5B843]",
  coral: "bg-[#F2665A]/15 text-[#F2665A]",
};

function NavBadge({ tone = "slate", children }) {
  return (
    <span className={`ml-auto rounded-md px-1.5 py-0.5 text-xs font-medium tabular-nums ${BADGE_TONES[tone]}`}>
      {children}
    </span>
  );
}

function NavItem({ item, count, onNavigate }) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      className={({ isActive }) =>
        [
          "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-[#818CF8]/12 text-[#E7E9EE] border-l-2 border-[#818CF8] -ml-0.5 pl-[11px]"
            : "text-[#8A93A6] hover:bg-white/5 hover:text-[#E7E9EE] border-l-2 border-transparent -ml-0.5 pl-[11px]",
        ].join(" ")
      }
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      <span className="truncate">{item.label}</span>
      {typeof count === "number" && count > 0 && <NavBadge tone={item.tone}>{count}</NavBadge>}
    </NavLink>
  );
}

/**
 * Sidebar
 *
 * Props:
 * - isOpen: whether the mobile drawer is open (ignored on md+ where the
 *   sidebar is always visible as a static column)
 * - onClose: called when the drawer should close (backdrop click, nav click)
 * - role: "admin" | "agent" | "viewer" — hides role-gated items
 * - counts: { unprocessed, awaitingReview, needsAttention } — live badge counts
 * - onSignOut: called when "Sign out" is pressed
 */
export default function Sidebar({ isOpen = false, onClose = () => {}, role = "agent", counts = {}, onSignOut = () => {} }) {
  const accountItems = ACCOUNT_ITEMS.filter((item) => !item.roles || item.roles.includes(role));

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={[
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-[#262C38] bg-[#161A22] transition-transform duration-200 ease-out",
          "md:static md:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full",
        ].join(" ")}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[#818CF8]/15 text-sm font-semibold text-[#818CF8]">
              T
            </span>
            <span className="text-[15px] font-semibold text-[#E7E9EE]">Triage</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-[#8A93A6] hover:bg-white/5 hover:text-[#E7E9EE] md:hidden"
            aria-label="Close menu"
          >
            <XIcon className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3.5 pb-4">
          <p className="px-3 pb-2 pt-2 text-xs font-medium text-[#5B6472]">Workspace</p>
          <div className="space-y-0.5">
            {WORKSPACE_ITEMS.map((item) => (
              <NavItem key={item.key} item={item} count={counts[item.badgeKey]} onNavigate={onClose} />
            ))}
          </div>

          <p className="px-3 pb-2 pt-6 text-xs font-medium text-[#5B6472]">Account</p>
          <div className="space-y-0.5">
            {accountItems.map((item) => (
              <NavItem key={item.key} item={item} onNavigate={onClose} />
            ))}
          </div>
        </nav>

        <div className="border-t border-[#262C38] p-3.5">
          <button
            type="button"
            onClick={onSignOut}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-[#8A93A6] transition-colors hover:bg-white/5 hover:text-[#E7E9EE]"
          >
            <LogOutIcon className="h-[18px] w-[18px]" />
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}