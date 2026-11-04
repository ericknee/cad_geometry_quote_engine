import { Suspense } from "react";

import QuoteResultView from "@/views/quote-result/QuoteResultView";

async function QuoteResult({ params }: Pick<PageProps<"/quotes/[id]">, "params">) {
  const { id } = await params;
  return <QuoteResultView id={id} />;
}

// params is runtime data, so it is awaited under Suspense (required by cacheComponents).
export default function Page({ params }: PageProps<"/quotes/[id]">) {
  return (
    <Suspense fallback={<p className="p-8">Loading…</p>}>
      <QuoteResult params={params} />
    </Suspense>
  );
}
