// Accent tokens shared by every stat card. Keeping the class strings
// static (rather than building them from an arbitrary hex prop) is what
// lets Tailwind's JIT compiler pick them up reliably.
const ACCENTS = {
  slate: { chip: "bg-[#6B7280]/15 text-[#9AA3B5]", edge: "border-l-[#6B7280]" },
  amber: { chip: "bg-[#F5B843]/15 text-[#F5B843]", edge: "border-l-[#F5B843]" },
  coral: { chip: "bg-[#F2665A]/15 text-[#F2665A]", edge: "border-l-[#F2665A]" },
  teal: { chip: "bg-[#34D399]/15 text-[#34D399]", edge: "border-l-[#34D399]" },
  brand: { chip: "bg-[#818CF8]/15 text-[#818CF8]", edge: "border-l-[#818CF8]" },
};

/**
 * StatCard
 *
 * Props:
 * - icon: icon component, e.g. ClockIcon
 * - label: short description, e.g. "Awaiting your review"
 * - value: number or string shown as the headline figure
 * - helperText: small supporting line under the value (optional)
 * - accent: "slate" | "amber" | "coral" | "teal" | "brand"
 */
export default function StatCard({ icon: Icon, label, value, helperText, accent = "slate" }) {
  const tone = ACCENTS[accent] ?? ACCENTS.slate;

  return (
    <div className={`rounded-xl border border-[#262C38] border-l-2 bg-[#161A22] p-5 ${tone.edge}`}>
      <div className="flex items-center justify-between">
        <span className={`flex h-9 w-9 items-center justify-center rounded-md ${tone.chip}`}>
          {Icon && <Icon className="h-[18px] w-[18px]" />}
        </span>
      </div>
      <p className="mt-4 font-mono text-3xl font-semibold tabular-nums text-[#E7E9EE]">{value}</p>
      <p className="mt-1 text-sm text-[#8A93A6]">{label}</p>
      {helperText && <p className="mt-2 text-xs text-[#5B6472]">{helperText}</p>}
    </div>
  );
}