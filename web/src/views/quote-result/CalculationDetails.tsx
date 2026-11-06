import Card from "@/components/Card";
import DataList from "@/components/DataList";
import { formatMoney, formatNumber } from "@/format";
import type { CostBreakdown, LeadTime } from "@/types";

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium">{title}</h3>
      {children}
    </div>
  );
}

/** Every intermediate value behind the price and lead time (PRD FR-P6). Collapsed by default. */
export default function CalculationDetails({
  cost,
  leadTime,
}: {
  cost: CostBreakdown;
  leadTime: LeadTime | null;
}) {
  const { material, machine, setup } = cost;
  const min = (n: number) => `${formatNumber(n)} min`;

  return (
    <Card>
      <details>
        <summary className="cursor-pointer font-semibold">How this was calculated</summary>
        <div className="mt-4 grid gap-6 sm:grid-cols-2">
          <Group title="Material">
            <p className="mb-2 text-xs text-fg-muted">
              Billed on the raw block we cut from (stock), not the finished part, because the
              removed material is paid for too.
            </p>
            <DataList
              rows={[
                ["Stock volume", `${formatNumber(material.stock_volume_cm3)} cm³`],
                ["Part volume", `${formatNumber(material.part_volume_cm3)} cm³`],
                ["Removed volume", `${formatNumber(material.removed_volume_cm3)} cm³`],
                ["Computed cost per unit", formatMoney(material.computed_cost_unit)],
                ["Computed cost per order", formatMoney(material.computed_cost_order)],
                ["Minimum charge (per order)", formatMoney(material.minimum_charge)],
                ["Minimum applied", material.minimum_applied ? "Yes" : "No"],
              ]}
            />
          </Group>
          <Group title="Machine time (per unit)">
            <DataList
              rows={[
                ["Roughing", min(machine.roughing_minutes)],
                ["Holes", min(machine.hole_minutes)],
                ["Edges", min(machine.edge_minutes)],
                ["Thin walls (under 3 mm)", machine.thin_wall_count],
                ["Roughing rate (MRR)", `${formatNumber(machine.mrr_cm3_per_min)} cm³/min`],
                ["Cycle time", min(machine.cycle_minutes)],
              ]}
            />
          </Group>
          <Group title="Setup (one-time, shared across the order)">
            <DataList
              rows={[
                ["Setups", setup.setups],
                ["Setup hours", formatNumber(setup.setup_hours)],
              ]}
            />
          </Group>
          {leadTime && (
            <Group title="Lead time">
              <DataList
                rows={[
                  ["Total machine hours", formatNumber(leadTime.total_machine_hours)],
                  ["Productive hours per day", formatNumber(leadTime.productive_hours_per_day)],
                  ["Machining days", leadTime.work_days],
                  ["Minimum lead time", `${leadTime.min_lead_time_days} days`],
                  ["Complexity buffer", `${leadTime.complexity_buffer_days} days`],
                  ["Lead time", `${leadTime.days} business days`],
                ]}
              />
            </Group>
          )}
        </div>
        <p className="mt-4 text-xs text-fg-muted">Pricing version {cost.pricing_version}</p>
      </details>
    </Card>
  );
}
