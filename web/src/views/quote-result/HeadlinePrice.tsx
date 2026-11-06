import Card from "@/components/Card";
import { formatDays, formatMoney } from "@/format";
import type { CostBreakdown } from "@/types";

function Figure({ label, value, big = false }: { label: string; value: string; big?: boolean }) {
  return (
    <div>
      <dt className="text-sm text-neutral-500">{label}</dt>
      <dd className={big ? "text-4xl font-semibold tracking-tight" : "text-2xl font-semibold"}>
        {value}
      </dd>
    </div>
  );
}

/** The three numbers the user came for. */
export default function HeadlinePrice({
  cost,
  leadTimeDays,
}: {
  cost: CostBreakdown;
  leadTimeDays: number | null;
}) {
  return (
    <Card>
      <dl className="grid gap-6 sm:grid-cols-3 sm:items-end">
        <Figure label="Price per unit" value={formatMoney(cost.total_cost_per_unit)} big />
        <Figure label="Total order" value={formatMoney(cost.total_order_cost)} />
        <Figure label="Lead time" value={formatDays(leadTimeDays)} />
      </dl>
    </Card>
  );
}
