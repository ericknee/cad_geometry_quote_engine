import type { QuoteStatus } from "@/types";

// One color per status, shared by the result page and the dashboard.
const STYLES: Record<QuoteStatus, string> = {
  queued: "bg-surface-muted text-fg-muted",
  processing: "bg-info-soft text-info",
  failed: "bg-danger-soft text-danger",
  quoted: "bg-success-soft text-success",
  reviewed: "bg-accent-soft text-primary-hover",
  archived: "bg-border/50 text-fg-muted",
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
