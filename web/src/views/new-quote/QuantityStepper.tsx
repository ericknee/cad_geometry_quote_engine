"use client";

import { MAX_QUANTITY, MIN_QUANTITY } from "./limits";

interface Props {
  /** Raw text, so the user can clear the box while typing. The parent validates it. */
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}

/** Parses the text; null when it is not a whole number in range. */
export function parseQuantity(text: string): number | null {
  if (!/^\d+$/.test(text.trim())) return null;
  const n = Number(text);
  return n >= MIN_QUANTITY && n <= MAX_QUANTITY ? n : null;
}

export default function QuantityStepper({ value, disabled, onChange }: Props) {
  const current = parseQuantity(value);
  const invalid = current === null;

  function step(delta: number) {
    const next = Math.min(MAX_QUANTITY, Math.max(MIN_QUANTITY, (current ?? MIN_QUANTITY) + delta));
    onChange(String(next));
  }

  const button =
    "h-10 w-10 rounded-md border border-neutral-300 bg-white text-lg hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50";

  return (
    <div>
      <label htmlFor="quantity" className="mb-1 block text-sm font-medium">
        Quantity
      </label>
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label="Decrease quantity"
          className={button}
          disabled={disabled || (current !== null && current <= MIN_QUANTITY)}
          onClick={() => step(-1)}
        >
          -
        </button>
        <input
          id="quantity"
          inputMode="numeric"
          value={value}
          disabled={disabled}
          aria-invalid={invalid}
          onChange={(e) => onChange(e.target.value)}
          className={`h-10 w-28 rounded-md border px-3 text-center disabled:opacity-60 ${
            invalid ? "border-red-400" : "border-neutral-300"
          }`}
        />
        <button
          type="button"
          aria-label="Increase quantity"
          className={button}
          disabled={disabled || (current !== null && current >= MAX_QUANTITY)}
          onClick={() => step(1)}
        >
          +
        </button>
      </div>
      {invalid && (
        <p role="alert" className="mt-1 text-sm text-red-700">
          Enter a whole number from {MIN_QUANTITY} to {MAX_QUANTITY.toLocaleString("en-US")}.
        </p>
      )}
    </div>
  );
}
