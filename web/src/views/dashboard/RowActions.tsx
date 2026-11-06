"use client";

import Link from "next/link";
import { useState } from "react";
import { ApiError } from "@/api/http";
import { describeError } from "@/api/errors";
import { updateQuoteStatus } from "@/api/quotes";
import Button, { buttonClasses } from "@/components/Button";
import { routes } from "@/routes";
import { MOVE_LABELS, REVIEWER_MOVES } from "@/statusMoves";
import type { QuoteStatus, QuoteSummary } from "@/types";

/** View button, plus a button for each status change allowed for this row. */
export default function RowActions({
  quote,
  onChanged,
}: {
  quote: QuoteSummary;
  onChanged: () => void;
}) {
  const [pending, setPending] = useState<QuoteStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function change(status: QuoteStatus) {
    if (status === "archived" && !window.confirm("Archive this quote? This cannot be undone.")) {
      return;
    }
    setPending(status);
    setError(null);
    try {
      await updateQuoteStatus(quote.id, status);
      onChanged();
    } catch (e) {
      setError(describeError(e));
      // Someone else changed it first: reload so this row shows its real status.
      if (e instanceof ApiError && e.code === "STATUS_CONFLICT") onChanged();
    } finally {
      setPending(null);
    }
  }

  return (
    <div>
      <div className="flex gap-2">
        <Link href={routes.quote(quote.id)} className={buttonClasses("secondary", "sm")}>
          View
        </Link>
        {REVIEWER_MOVES[quote.status].map((status) => (
          <Button
            key={status}
            size="sm"
            variant={status === "archived" ? "secondary" : "primary"}
            disabled={pending !== null}
            onClick={() => change(status)}
          >
            {pending === status ? "Saving..." : MOVE_LABELS[status]}
          </Button>
        ))}
      </div>
      {error && (
        <p role="alert" className="mt-1 max-w-56 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
