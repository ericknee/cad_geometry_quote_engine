import { Suspense } from "react";

import DashboardView from "@/views/dashboard/DashboardView";

// DashboardView reads the URL's query string (the filters), which must happen under Suspense.
export default function Page() {
  return (
    <Suspense fallback={<p className="text-fg-muted">Loading…</p>}>
      <DashboardView />
    </Suspense>
  );
}
