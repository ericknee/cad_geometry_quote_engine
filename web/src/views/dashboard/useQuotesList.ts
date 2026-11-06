"use client";

import { useCallback, useEffect, useState } from "react";
import { listQuotes } from "@/api/quotes";
import { IN_PROGRESS_STATUSES, type QuoteList, type QuoteStatus } from "@/types";

const REFRESH_MS = 3000;

interface Params {
  status?: QuoteStatus;
  excludeArchived: boolean;
  sort: "newest" | "oldest";
  limit: number;
  skip: number;
}

interface Loaded {
  key: string;
  data: QuoteList | null;
  error: unknown;
}

/**
 * Loads one page of quotes. Refetches every few seconds while a visible row is still queued or
 * processing, so its status and price fill in. `reload` refetches now (after a status change).
 */
export function useQuotesList({ status, excludeArchived, sort, limit, skip }: Params) {
  const key = [status ?? "", excludeArchived, sort, limit, skip].join("|");
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      try {
        const data = await listQuotes({ status, excludeArchived, sort, limit, skip });
        if (cancelled) return;
        setLoaded({ key, data, error: null });
        if (data.items.some((q) => IN_PROGRESS_STATUSES.includes(q.status))) {
          timer = setTimeout(load, REFRESH_MS);
        }
      } catch (error) {
        if (cancelled) return;
        // Keep the rows we already have for this view; just report the error.
        setLoaded((prev) => ({ key, data: prev?.key === key ? prev.data : null, error }));
      }
    }
    load();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key, reloads, status, excludeArchived, sort, limit, skip]);

  // A result for a previous set of filters is not shown.
  const current = loaded?.key === key ? loaded : null;
  const reload = useCallback(() => setReloads((n) => n + 1), []);
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: current === null,
    reload,
  };
}
