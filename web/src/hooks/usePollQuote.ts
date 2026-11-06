"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/api/http";
import { getQuote } from "@/api/quotes";
import { IN_PROGRESS_STATUSES, type QuoteDetail } from "@/types";

const POLL_MS = 1000;
const MAX_FAILURES = 10; // consecutive failures (~20s of retrying) before giving up

interface Polled {
  id: string;
  quote: QuoteDetail | null;
  error: unknown;
}

/**
 * Fetches a quote every second while it is queued or processing, then stops.
 * Pass null to do nothing. A network failure, 5xx, 408 or 429 is retried until it has failed
 * several times in a row; any other 4xx (e.g. 404) stops at once. Either way it stops with `error`.
 */
export function usePollQuote(id: string | null) {
  const [polled, setPolled] = useState<Polled | null>(null);

  useEffect(() => {
    if (!id) return;
    const quoteId = id;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let failures = 0;

    async function tick() {
      try {
        const quote = await getQuote(quoteId);
        if (cancelled) return;
        failures = 0;
        setPolled({ id: quoteId, quote, error: null });
        if (IN_PROGRESS_STATUSES.includes(quote.status)) timer = setTimeout(tick, POLL_MS);
      } catch (error) {
        if (cancelled) return;
        failures += 1;
        const clientError =
          error instanceof ApiError &&
          error.status < 500 &&
          error.status !== 408 &&
          error.status !== 429;
        if (clientError || failures >= MAX_FAILURES) {
          setPolled({ id: quoteId, quote: null, error });
        } else {
          timer = setTimeout(tick, POLL_MS * 2);
        }
      }
    }
    tick();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  // Ignore a result that belongs to a previous id.
  const current = polled?.id === id ? polled : null;
  return { quote: current?.quote ?? null, error: current?.error ?? null };
}
