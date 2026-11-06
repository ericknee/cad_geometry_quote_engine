"use client";

import { useRef, useState } from "react";
import { formatNumber } from "@/format";
import { ACCEPTED_EXTENSIONS } from "./limits";

interface Props {
  file: File | null;
  error: string | null;
  disabled: boolean;
  onSelect: (file: File) => void;
}

/** Click-or-drop area for one STEP file. Validation lives in the parent. */
export default function FileDropzone({ file, error, disabled, onSelect }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function pick(files: FileList | null) {
    const chosen = files?.[0];
    if (chosen) onSelect(chosen);
  }

  const border = error
    ? "border-red-400 bg-red-50"
    : dragging
      ? "border-blue-500 bg-blue-50"
      : "border-neutral-300 bg-white hover:border-neutral-400";

  return (
    <div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) pick(e.dataTransfer.files);
        }}
        className={`flex w-full flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${border}`}
      >
        {file ? (
          <>
            <span className="font-medium">{file.name}</span>
            <span className="mt-1 text-sm text-neutral-500">
              {formatNumber(file.size / 1024 / 1024)} MB. Click or drop to replace.
            </span>
          </>
        ) : (
          <>
            <span className="font-medium">Drop your STEP file here, or click to browse</span>
            <span className="mt-1 text-sm text-neutral-500">
              {ACCEPTED_EXTENSIONS.join(" or ")} files only
            </span>
          </>
        )}
      </button>
      <input
        ref={input}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        className="hidden"
        onChange={(e) => {
          pick(e.target.files);
          e.target.value = ""; // allow re-picking the same file after an error
        }}
      />
      {error && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  );
}
