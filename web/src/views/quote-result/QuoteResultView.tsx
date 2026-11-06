"use client";

import { useState } from "react";
import { ApiError } from "@/api/http";
import { describeError } from "@/api/errors";
import { usePollQuote } from "@/hooks/usePollQuote";
import { IN_PROGRESS_STATUSES, type QuoteDetail } from "@/types";
import CalculationDetails from "./CalculationDetails";
import ComplexityPanel from "./ComplexityPanel";
import CostBreakdown from "./CostBreakdown";
import GeometryPanel from "./GeometryPanel";
import HeadlinePrice from "./HeadlinePrice";
import QuoteHeader from "./QuoteHeader";
import { FailedPanel, LoadingPanel, MessagePanel } from "./ResultStates";
import StatusActions from "./StatusActions";

export default function QuoteResultView({ id }: { id: string }) {
  const { quote: polled, error } = usePollQuote(id);
  // A status change replaces the polled quote (polling has stopped by then).
  const [changed, setChanged] = useState<QuoteDetail | null>(null);
  const quote = changed?.id === id ? changed : polled;

  if (error) {
    return error instanceof ApiError && error.code === "QUOTE_NOT_FOUND" ? (
      <MessagePanel title="Quote not found" message="This quote doesn't exist or was removed." />
    ) : (
      <MessagePanel title="Couldn't load this quote" message={describeError(error)} />
    );
  }
  if (!quote) return <LoadingPanel message="Loading quote..." />;

  const inProgress = IN_PROGRESS_STATUSES.includes(quote.status);

  return (
    <main className="space-y-6">
      <QuoteHeader quote={quote} />

      {inProgress && <LoadingPanel message="Analyzing your part. This usually takes a few seconds." />}
      {quote.status === "failed" && <FailedPanel error={quote.error} />}

      {quote.cost_breakdown && (
        <>
          <HeadlinePrice cost={quote.cost_breakdown} leadTimeDays={quote.lead_time_days} />
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="lg:col-span-2">
              <CostBreakdown cost={quote.cost_breakdown} />
            </div>
            {quote.geometry && <GeometryPanel geometry={quote.geometry} />}
            {quote.geometry && <ComplexityPanel features={quote.geometry.features} />}
          </div>
          <CalculationDetails cost={quote.cost_breakdown} leadTime={quote.lead_time} />
        </>
      )}

      <StatusActions quote={quote} onChange={setChanged} />
    </main>
  );
}
