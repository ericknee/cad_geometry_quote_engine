"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { describeError } from "@/api/errors";
import { createQuote } from "@/api/quotes";
import { routes } from "@/routes";
import FileDropzone from "./FileDropzone";
import { checkFile } from "./limits";
import QuantityStepper, { parseQuantity } from "./QuantityStepper";

export default function NewQuoteView() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [quantity, setQuantity] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const parsedQuantity = parseQuantity(quantity);
  const canSubmit = file !== null && fileError === null && parsedQuantity !== null && !submitting;

  function selectFile(chosen: File) {
    const problem = checkFile(chosen);
    setFileError(problem);
    setFile(problem ? null : chosen);
    setSubmitError(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || parsedQuantity === null) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      // The API answers 202 right away; the result page polls until the quote is ready.
      const quote = await createQuote(file, parsedQuantity);
      router.push(routes.quote(quote.id));
    } catch (error) {
      setSubmitError(describeError(error));
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold">New quote</h1>
      <p className="mt-1 text-neutral-600">
        Upload a STEP file and a quantity to get an instant CNC quote in 6061 aluminum.
      </p>

      <form onSubmit={submit} className="mt-6 space-y-6">
        <FileDropzone file={file} error={fileError} disabled={submitting} onSelect={selectFile} />
        <QuantityStepper value={quantity} disabled={submitting} onChange={setQuantity} />

        {submitError && (
          <p role="alert" className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">
            {submitError}
          </p>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full rounded-md bg-neutral-900 px-4 py-3 font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {submitting ? "Uploading..." : "Generate quote"}
        </button>
      </form>
    </main>
  );
}
