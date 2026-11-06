import type { QuoteStatus } from "@/types";

// One color per status, shared by the result page and the dashboard.
const STYLES: Record<QuoteStatus, string> = {
  queued: "bg-neutral-100 text-neutral-700",
  processing: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  quoted: "bg-emerald-100 text-emerald-800",
  reviewed: "bg-violet-100 text-violet-800",
  archived: "bg-neutral-200 text-neutral-500",
};

export default function StatusBadge({ status }: { status: QuoteStatus }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[status]}`}
    >
      {status}
    </span>
  );
}
