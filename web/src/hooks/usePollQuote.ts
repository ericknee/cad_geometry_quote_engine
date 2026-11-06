"use client";

import { useEffect, useState } from "react";
import { ApiError } from "@/api/http";
import { getQuote } from "@/api/quotes";
import { IN_PROGRESS_STATUSES, type QuoteDetail } from "@/types";

const POLL_MS = 1000;

interface Polled {
  id: string;
  quote: QuoteDetail | null;
  error: ApiError | null;
}

/**
 * Fetches a quote every second while it is queued or processing, then stops.
 * Pass null to do nothing. A network failure or 5xx is retried; a 4xx (e.g. 404) stops with `error`.
 */
export function usePollQuote(id: string | null) {
  const [polled, setPolled] = useState<Polled | null>(null);

  useEffect(() => {
    if (!id) return;
    const quoteId = id;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function tick() {
      try {
        const quote = await getQuote(quoteId);
        if (cancelled) return;
        setPolled({ id: quoteId, quote, error: null });
        if (IN_PROGRESS_STATUSES.includes(quote.status)) timer = setTimeout(tick, POLL_MS);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && error.status < 500) {
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
