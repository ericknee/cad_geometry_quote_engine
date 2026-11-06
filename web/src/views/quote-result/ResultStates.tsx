import Link from "next/link";
import { buttonClasses } from "@/components/Button";
import Card from "@/components/Card";
import { routes } from "@/routes";
import type { ErrorDetail } from "@/types";

export function LoadingPanel({ message }: { message: string }) {
  return (
    <Card>
      <div className="flex items-center gap-3 py-6" role="status">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-primary" />
        <p>{message}</p>
      </div>
    </Card>
  );
}

export function FailedPanel({ error }: { error: ErrorDetail | null }) {
  return (
    <Card>
      <div className="py-4" role="alert">
        <h2 className="font-semibold text-danger">We couldn&apos;t quote this file</h2>
        <p className="mt-1 text-fg-muted">{error?.message ?? "The analysis failed."}</p>
        <Link href={routes.newQuote} className={`${buttonClasses("primary")} mt-4`}>
          Upload another file
        </Link>
      </div>
    </Card>
  );
}

export function MessagePanel({ title, message }: { title: string; message: string }) {
  return (
    <Card>
      <div className="py-4" role="alert">
        <h2 className="font-semibold">{title}</h2>
        <p className="mt-1 text-fg-muted">{message}</p>
        <Link href={routes.newQuote} className="mt-4 inline-block text-sm text-primary underline">
          Start a new quote
        </Link>
      </div>
    </Card>
  );
}
