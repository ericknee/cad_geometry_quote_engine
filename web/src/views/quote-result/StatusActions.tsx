"use client";

import { useState } from "react";
import { ApiError } from "@/api/http";
import { describeError } from "@/api/errors";
import { getQuote, updateQuoteStatus } from "@/api/quotes";
import Button from "@/components/Button";
import { MOVE_LABELS, REVIEWER_MOVES } from "@/statusMoves";
import type { QuoteDetail, QuoteStatus } from "@/types";

/** Buttons for the status changes a reviewer may make. Renders nothing when there are none. */
export default function StatusActions({
  quote,
  onChange,
}: {
  quote: QuoteDetail;
  onChange: (quote: QuoteDetail) => void;
}) {
  const [pending, setPending] = useState<QuoteStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const moves = REVIEWER_MOVES[quote.status];

  if (moves.length === 0) return null;

  async function move(status: QuoteStatus) {
    if (status === "archived" && !window.confirm("Archive this quote? This cannot be undone.")) {
      return;
    }
    setPending(status);
    setError(null);
    try {
      onChange(await updateQuoteStatus(quote.id, status));
    } catch (e) {
      setError(describeError(e));
      // Someone else changed it first: show the current state so the buttons match.
      if (e instanceof ApiError && e.code === "STATUS_CONFLICT") {
        onChange(await getQuote(quote.id).catch(() => quote));
      }
    } finally {
      setPending(null);
    }
  }

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        {moves.map((status) => (
          <Button
            key={status}
            variant={status === "archived" ? "secondary" : "primary"}
            disabled={pending !== null}
            onClick={() => move(status)}
          >
            {pending === status ? "Saving..." : MOVE_LABELS[status]}
          </Button>
        ))}
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
