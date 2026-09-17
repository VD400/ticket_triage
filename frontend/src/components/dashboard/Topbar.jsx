import { MenuIcon, SearchIcon, BellIcon } from "./icons";

const ROLE_STYLES = {
  admin: "bg-[#818CF8]/15 text-[#818CF8]",
  agent: "bg-[#34D399]/15 text-[#34D399]",
  viewer: "bg-white/5 text-[#9AA3B5]",
};

const ROLE_LABELS = {
  admin: "Admin",
  agent: "Agent",
  viewer: "Viewer",
};

function getInitials(name = "") {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/**
 * Topbar
 *
 * Props:
 * - onMenuClick: opens the mobile sidebar drawer
 * - pageTitle: current section name, shown next to the menu button
 * - user: { name, role } — role is "admin" | "agent" | "viewer"
 */
export default function Topbar({ onMenuClick = () => {}, pageTitle = "Overview", user = { name: "", role: "agent" } }) {
  const roleClass = ROLE_STYLES[user.role] ?? ROLE_STYLES.viewer;
  const roleLabel = ROLE_LABELS[user.role] ?? "Viewer";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-[#262C38] bg-[#0E1116]/95 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-md p-1.5 text-[#8A93A6] hover:bg-white/5 hover:text-[#E7E9EE] md:hidden"
        aria-label="Open menu"
      >
        <MenuIcon className="h-5 w-5" />
      </button>

      <h1 className="text-[15px] font-semibold text-[#E7E9EE]">{pageTitle}</h1>

      <div className="ml-auto flex items-center gap-2 sm:gap-4">
        <label className="relative hidden sm:block">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#5B6472]" />
          <input
            type="text"
            placeholder="Search tickets"
            className="w-56 rounded-md border border-[#262C38] bg-[#161A22] py-2 pl-9 pr-3 text-sm text-[#E7E9EE] placeholder:text-[#5B6472] focus:border-[#818CF8] focus:outline-none focus:ring-1 focus:ring-[#818CF8]"
          />
        </label>

        <button
          type="button"
          className="relative rounded-md p-2 text-[#8A93A6] hover:bg-white/5 hover:text-[#E7E9EE]"
          aria-label="Notifications"
        >
          <BellIcon className="h-5 w-5" />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-[#F2665A]" />
        </button>

        <div className="h-6 w-px bg-[#262C38]" />

        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#1C212B] text-xs font-semibold text-[#E7E9EE]">
            {getInitials(user.name)}
          </span>
          <div className="hidden leading-tight sm:block">
            <p className="text-sm font-medium text-[#E7E9EE]">{user.name}</p>
            <span className={`inline-block rounded-md px-1.5 py-0.5 text-[11px] font-medium ${roleClass}`}>
              {roleLabel}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}