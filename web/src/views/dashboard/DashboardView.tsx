"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { describeError } from "@/api/errors";
import Alert from "@/components/Alert";
import Button, { buttonClasses } from "@/components/Button";
import Card from "@/components/Card";
import { routes } from "@/routes";
import {
  DEFAULT_FILTERS,
  filtersToQuery,
  PAGE_SIZE,
  parseFilters,
  toListParams,
  type Filters,
} from "./filters";
import Pagination from "./Pagination";
import QuotesFilters from "./QuotesFilters";
import QuotesTable, { TableSkeleton } from "./QuotesTable";
import { useQuotesList } from "./useQuotesList";

export default function DashboardView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const filters = parseFilters(searchParams);
  const { data, error, loading, reload } = useQuotesList(toListParams(filters));

  function go(next: Filters, replace = false) {
    const query = filtersToQuery(next);
    const url = query ? `${routes.dashboard}?${query}` : routes.dashboard;
    if (replace) router.replace(url, { scroll: false });
    else router.push(url, { scroll: false });
  }

  // Changing a filter goes back to page 1; changing the page keeps the filters.
  const changeFilters = (change: Partial<Filters>) => go({ ...filters, ...change, page: 1 });

  // The last row on a page was archived or the URL had a page past the end: step back.
  useEffect(() => {
    if (data && data.items.length === 0 && data.total > 0 && filters.page > 1) {
      const lastPage = Math.ceil(data.total / PAGE_SIZE);
      router.replace(
        `${routes.dashboard}?${filtersToQuery({ ...filters, page: lastPage })}`,
        { scroll: false },
      );
    }
  }, [data, filters, router]);

  const isDefault = filtersToQuery(filters) === filtersToQuery(DEFAULT_FILTERS);

  return (
    <main className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Quotes</h1>
        <Link href={routes.newQuote} className={buttonClasses("primary")}>
          New quote
        </Link>
      </div>

      <QuotesFilters filters={filters} onChange={changeFilters} />

      {error !== null && (
        <Alert className="flex flex-wrap items-center justify-between gap-3">
          <span>{describeError(error)}</span>
          <Button variant="danger" size="sm" onClick={reload}>
            Retry
          </Button>
        </Alert>
      )}

      {loading && error === null && <TableSkeleton />}

      {data && data.items.length > 0 && (
        <>
          <QuotesTable quotes={data.items} onChanged={reload} />
          <Pagination
            total={data.total}
            limit={data.limit}
            skip={data.skip}
            onPage={(page) => go({ ...filters, page })}
          />
        </>
      )}

      {data && data.total === 0 && (
        <Card>
          <div className="py-6 text-center">
            <p className="font-medium">
              {isDefault ? "No quotes yet" : "No quotes match these filters"}
            </p>
            <p className="mt-1 text-sm text-fg-muted">
              {isDefault
                ? "Upload a STEP file to create your first quote."
                : "Try a different status or show archived quotes."}
            </p>
            <Link href={routes.newQuote} className="mt-4 inline-block text-sm text-primary underline">
              New quote
            </Link>
          </div>
        </Card>
      )}
    </main>
  );
}
