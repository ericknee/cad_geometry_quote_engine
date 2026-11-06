import StatusBadge from "@/components/StatusBadge";
import { formatDate } from "@/format";
import type { QuoteDetail } from "@/types";

export default function QuoteHeader({ quote }: { quote: QuoteDetail }) {
  return (
    <header>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="break-all text-2xl font-semibold">{quote.file_name}</h1>
        <StatusBadge status={quote.status} />
      </div>
      <p className="mt-1 text-sm text-fg-muted">
        Quantity {quote.quantity.toLocaleString("en-US")} · {quote.material} ·{" "}
        {formatDate(quote.created_at)}
      </p>
    </header>
  );
}
