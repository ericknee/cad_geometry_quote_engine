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
  const { material, machine, setup, discount } = cost;
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
                ["Minimum charge", formatMoney(material.minimum_charge)],
                ["Minimum applied", material.minimum_applied ? "Yes" : "No"],
              ]}
            />
          </Group>
          <Group title="Machine time (per unit, before discount)">
            <DataList
              rows={[
                ["Roughing", min(machine.roughing_minutes)],
                ["Finishing", min(machine.finishing_minutes)],
                ["Holes", min(machine.hole_minutes)],
                ["Handling", min(machine.handling_minutes)],
                ["Complexity factor used", formatNumber(machine.complexity_score)],
                ["Cycle time", min(machine.cycle_minutes)],
              ]}
            />
          </Group>
          <Group title="Setup and discount">
            <DataList
              rows={[
                ["Setups", setup.setups],
                ["Setup hours", formatNumber(setup.setup_hours)],
                ["Discount rate", `${Math.round(discount.rate * 100)}%`],
              ]}
            />
          </Group>
          {leadTime && (
            <Group title="Lead time (uses undiscounted machine time)">
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
