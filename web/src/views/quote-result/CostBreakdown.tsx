import Card from "@/components/Card";
import { formatMoney } from "@/format";
import type { CostBreakdown as Cost } from "@/types";
import CostBar from "./CostBar";

function Row({
  label,
  note,
  unit,
  order,
  strong = false,
}: {
  label: string;
  note?: string;
  unit: string;
  order: string;
  strong?: boolean;
}) {
  return (
    <tr className={strong ? "border-t border-border-strong font-semibold" : ""}>
      <th scope="row" className="py-2 pr-3 text-left font-normal">
        <span className={strong ? "font-semibold" : ""}>{label}</span>
        {note && <span className="block text-xs text-fg-muted">{note}</span>}
      </th>
      <td className="py-2 pl-3 text-right tabular-nums">{unit}</td>
      <td className="py-2 pl-3 text-right tabular-nums">{order}</td>
    </tr>
  );
}

export default function CostBreakdown({ cost }: { cost: Cost }) {
  const { material, machine, setup } = cost;

  return (
    <Card title="Cost breakdown">
      <CostBar cost={cost} />
      <div className="mt-5 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-fg-muted">
              <th className="pb-2 text-left font-normal" />
              <th className="pb-2 pl-3 text-right font-normal">Per unit</th>
              <th className="pb-2 pl-3 text-right font-normal">
                Order ({cost.quantity.toLocaleString("en-US")})
              </th>
            </tr>
          </thead>
          <tbody>
            <Row
              label="Material"
              note={
                material.minimum_applied
                  ? `${formatMoney(material.minimum_charge)} order minimum applied (computed ${formatMoney(material.computed_cost_order)})`
                  : undefined
              }
              unit={formatMoney(material.cost_unit)}
              order={formatMoney(material.cost_order)}
            />
            <Row
              label="Machine time"
              unit={formatMoney(machine.cost_unit)}
              order={formatMoney(machine.cost_order)}
            />
            <Row
              label="Setup"
              note="One-time programming and fixturing, shared across the order"
              unit={formatMoney(setup.cost_unit)}
              order={formatMoney(setup.cost_order)}
            />
            <Row
              label="Total"
              unit={formatMoney(cost.total_cost_per_unit)}
              order={formatMoney(cost.total_order_cost)}
              strong
            />
          </tbody>
        </table>
      </div>
    </Card>
  );
}
