"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { describeError } from "@/api/errors";
import { createQuote } from "@/api/quotes";
import { usePollQuote } from "@/hooks/usePollQuote";
import { routes } from "@/routes";
import { IN_PROGRESS_STATUSES } from "@/types";
import FileDropzone from "./FileDropzone";
import { checkFile } from "./limits";
import QuantityStepper, { parseQuantity } from "./QuantityStepper";

export default function NewQuoteView() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  // Set once the upload is accepted; the worker is then analyzing, and we poll for the result.
  const [quoteId, setQuoteId] = useState<string | null>(null);
  const { quote, error: pollError } = usePollQuote(quoteId);

  const failed = quote?.status === "failed";
  const analyzing = quoteId !== null && !failed && !pollError;
  const busy = uploading || analyzing;

  let errorMessage: string | null = uploadError;
  if (!errorMessage && failed) {
    errorMessage = quote.error?.message ?? "We couldn't analyze that file.";
  }
  if (!errorMessage && pollError) errorMessage = describeError(pollError);

  const parsedQuantity = parseQuantity(quantity);
  const canSubmit = file !== null && fileError === null && parsedQuantity !== null && !busy;

  // Redirect only once the quote is ready (any status past queued/processing/failed).
  useEffect(() => {
    if (quote && quote.status !== "failed" && !IN_PROGRESS_STATUSES.includes(quote.status)) {
      router.push(routes.quote(quote.id));
    }
  }, [quote, router]);

  // Editing the form clears the previous attempt and its error.
  function resetAttempt() {
    setQuoteId(null);
    setUploadError(null);
  }

  function selectFile(chosen: File) {
    const problem = checkFile(chosen);
    setFileError(problem);
    setFile(problem ? null : chosen);
    resetAttempt();
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || parsedQuantity === null) return;
    resetAttempt();
    setUploading(true);
    try {
      const created = await createQuote(file, parsedQuantity);
      setQuoteId(created.id);
    } catch (error) {
      setUploadError(describeError(error));
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold">New quote</h1>
      <p className="mt-1 text-neutral-600">
        Upload a STEP file and a quantity to get an instant CNC quote in 6061 aluminum.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-6">
        <FileDropzone file={file} error={fileError} disabled={busy} onSelect={selectFile} />
        <QuantityStepper
          value={quantity}
          disabled={busy}
          onChange={(value) => {
            setQuantity(value);
            resetAttempt();
          }}
        />

        {errorMessage && (
          <p role="alert" className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">
            {errorMessage}
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full rounded-md bg-neutral-900 px-4 py-3 font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {uploading ? "Uploading..." : analyzing ? "Analyzing your part..." : "Generate quote"}
        </button>
      </form>
    </main>
  );
}
