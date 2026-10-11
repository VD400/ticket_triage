// Small, single-style icon set (24px grid, stroke-based) so the dashboard
// doesn't depend on an icon package. Every icon takes a `className` for
// sizing/color, e.g. <ClockIcon className="h-5 w-5" />.

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export function GridIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function ClockIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </svg>
  );
}

export function InboxIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <path d="M3 12h4.5l1.6 3h5.8l1.6-3H21" />
      <path d="M5.2 5.2h13.6a2 2 0 0 1 1.98 1.72L21.5 13v6a2 2 0 0 1-2 2H4.5a2 2 0 0 1-2-2v-6l0.72-6.08A2 2 0 0 1 5.2 5.2Z" />
    </svg>
  );
}

export function AlertTriangleIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <path d="M10.6 4.1 2.9 18a1.8 1.8 0 0 0 1.55 2.7h15.1A1.8 1.8 0 0 0 21.1 18L13.4 4.1a1.8 1.8 0 0 0-2.8 0Z" />
      <path d="M12 9.5v4.2" />
      <path d="M12 17.2h.01" />
    </svg>
  );
}

export function CheckCircleIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.2 12.3 2.5 2.5 5-5.2" />
    </svg>
  );
}

export function ActivityIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <path d="M3 12h3.5l2-6.5 4 13 2-6.5H21" />
    </svg>
  );
}

export function UsersIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.8 19.5a6.2 6.2 0 0 1 12.4 0" />
      <path d="M16.2 5.3a3.2 3.2 0 0 1 0 6.2" />
      <path d="M18.4 13.6a6.2 6.2 0 0 1 3.8 5.9" />
    </svg>
  );
}

export function SettingsIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 13.5a1.7 1.7 0 0 0 .34 1.87l.06.06a2.06 2.06 0 1 1-2.92 2.92l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V19.6a2.06 2.06 0 1 1-4.12 0v-.09a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2.06 2.06 0 1 1-2.92-2.92l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H4.4a2.06 2.06 0 1 1 0-4.12h.09A1.7 1.7 0 0 0 6.05 6.9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2.06 2.06 0 1 1 2.92-2.92l.06.06a1.7 1.7 0 0 0 1.87.34H10.6a1.7 1.7 0 0 0 1.03-1.56V4.4a2.06 2.06 0 1 1 4.12 0v.09a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06a2.06 2.06 0 1 1 2.92 2.92l-.06.06a1.7 1.7 0 0 0-.34 1.87v.1a1.7 1.7 0 0 0 1.56 1.03h.09a2.06 2.06 0 1 1 0 4.12h-.09a1.7 1.7 0 0 0-1.56 1.03Z" />
    </svg>
  );
}

export function LogOutIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <path d="M9 4.5H5.8A1.8 1.8 0 0 0 4 6.3v11.4A1.8 1.8 0 0 0 5.8 19.5H9" />
      <path d="M16 15.5 21 12l-5-3.5" />
      <path d="M21 12h-11" />
    </svg>
  );
}

export function MenuIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <path d="M3.5 6.5h17" />
      <path d="M3.5 12h17" />
      <path d="M3.5 17.5h17" />
    </svg>
  );
}

export function XIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <path d="M6 6l12 12" />
      <path d="M18 6 6 18" />
    </svg>
  );
}

export function SearchIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20.5 20.5-4-4" />
    </svg>
  );
}

export function BellIcon({ className = "h-5 w-5" }) {
  return (
    <svg {...base} className={className}>
      <path d="M6 9.5a6 6 0 0 1 12 0c0 4.2 1.2 5.8 2 6.5H4c.8-.7 2-2.3 2-6.5Z" />
      <path d="M10 19a2.1 2.1 0 0 0 4 0" />
    </svg>
  );
}

export function ChevronRightIcon({ className = "h-4 w-4" }) {
  return (
    <svg {...base} className={className}>
      <path d="m9 6 6 6-6 6" />
    </svg>
  );
}