"use client";

import { useState } from "react";
import { ApiError } from "@/api/http";
import { describeError } from "@/api/errors";
import { updateQuoteStatus } from "@/api/quotes";
import StatusBadge from "@/components/StatusBadge";
import { MOVE_LABELS, REVIEWER_MOVES } from "@/statusMoves";
import type { QuoteStatus, QuoteSummary } from "@/types";

/** A badge, or a dropdown of the status changes allowed for this row. */
export default function RowStatusControl({
  quote,
  onChanged,
}: {
  quote: QuoteSummary;
  onChanged: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const moves = REVIEWER_MOVES[quote.status];

  if (moves.length === 0) return <StatusBadge status={quote.status} />;

  async function change(status: QuoteStatus) {
    if (status === "archived" && !window.confirm("Archive this quote? This cannot be undone.")) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await updateQuoteStatus(quote.id, status);
      onChanged();
    } catch (e) {
      setError(describeError(e));
      // Someone else changed it first: reload so this row shows its real status.
      if (e instanceof ApiError && e.code === "STATUS_CONFLICT") onChanged();
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <select
        aria-label={`Status of ${quote.file_name}`}
        value={quote.status}
        disabled={pending}
        onChange={(e) => change(e.target.value as QuoteStatus)}
        className="h-8 rounded-md border border-neutral-300 bg-white px-1.5 text-sm capitalize disabled:opacity-50"
      >
        <option value={quote.status}>{quote.status}</option>
        {moves.map((status) => (
          <option key={status} value={status}>
            {MOVE_LABELS[status] ?? status}
          </option>
        ))}
      </select>
      {error && (
        <p role="alert" className="mt-1 max-w-48 text-xs text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
