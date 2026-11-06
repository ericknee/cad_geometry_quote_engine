import { formatMoney } from "@/format";
import type { CostBreakdown } from "@/types";

// Segment colors, shared with the legend below the bar.
const SEGMENTS = [
  { key: "material", label: "Material", color: "bg-chart-material" },
  { key: "machine", label: "Machine time", color: "bg-chart-machine" },
  { key: "setup", label: "Setup", color: "bg-chart-setup" },
] as const;

/** One stacked bar of the per-unit cost. */
export default function CostBar({ cost }: { cost: CostBreakdown }) {
  const values = {
    material: cost.material.cost_unit,
    machine: cost.machine.cost_unit,
    setup: cost.setup.cost_unit,
  };
  const total = values.material + values.machine + values.setup;

  return (
    <div>
      <div
        className="flex h-4 overflow-hidden rounded-full bg-surface-muted"
        role="img"
        aria-label="Share of per-unit cost: material, machine time and setup"
      >
        {SEGMENTS.map(({ key, color }) => (
          <div
            key={key}
            className={color}
            style={{ width: `${total > 0 ? (values[key] / total) * 100 : 0}%` }}
          />
        ))}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-fg-muted">
        {SEGMENTS.map(({ key, label, color }) => (
          <li key={key} className="flex items-center gap-1.5">
            <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
            {label} {total > 0 ? Math.round((values[key] / total) * 100) : 0}% (
            {formatMoney(values[key])})
          </li>
        ))}
      </ul>
    </div>
  );
}
