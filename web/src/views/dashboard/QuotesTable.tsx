import Link from "next/link";
import StatusBadge from "@/components/StatusBadge";
import { formatDate, formatMoney } from "@/format";
import { routes } from "@/routes";
import type { QuoteSummary } from "@/types";
import RowActions from "./RowActions";

const HEAD = "whitespace-nowrap px-3 py-2 text-left font-medium text-fg-muted";
const CELL = "px-3 py-3";

export default function QuotesTable({
  quotes,
  onChanged,
}: {
  quotes: QuoteSummary[];
  onChanged: () => void;
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-sm">
        <thead className="border-b border-border bg-surface-muted">
          <tr>
            <th className={HEAD}>Status</th>
            <th className={HEAD}>File</th>
            <th className={`${HEAD} text-right`}>Qty</th>
            <th className={`${HEAD} text-right`}>Per unit</th>
            <th className={`${HEAD} text-right`}>Total</th>
            <th className={`${HEAD} text-right`}>Lead time</th>
            <th className={HEAD}>Created</th>
            <th className={HEAD}>Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/50">
          {quotes.map((quote) => (
            <tr key={quote.id}>
              <td className={CELL}>
                <StatusBadge status={quote.status} />
              </td>
              <td className={`${CELL} max-w-48 break-words font-medium`}>
                <Link href={routes.quote(quote.id)} className="hover:underline">
                  {quote.file_name}
                </Link>
              </td>
              <td className={`${CELL} text-right tabular-nums`}>
                {quote.quantity.toLocaleString("en-US")}
              </td>
              <td className={`${CELL} text-right tabular-nums`}>
                {formatMoney(quote.total_cost_per_unit)}
              </td>
              <td className={`${CELL} text-right tabular-nums`}>
                {formatMoney(quote.total_order_cost)}
              </td>
              <td className={`${CELL} text-right tabular-nums`}>
                {quote.lead_time_days === null ? "-" : `${quote.lead_time_days} days`}
              </td>
              <td className={`${CELL} min-w-28 text-fg-muted`}>
                {formatDate(quote.created_at)}
              </td>
              <td className={CELL}>
                <RowActions quote={quote} onChanged={onChanged} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TableSkeleton() {
  return (
    <div
      className="space-y-px overflow-hidden rounded-lg border border-border bg-surface"
      role="status"
      aria-label="Loading quotes"
    >
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="h-12 animate-pulse bg-surface-muted" />
      ))}
    </div>
  );
}
