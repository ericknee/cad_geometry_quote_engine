"use client";

import Button from "@/components/Button";
import TextInput from "@/components/TextInput";
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

  return (
    <div>
      <label htmlFor="quantity" className="mb-1 block text-sm font-medium">
        Quantity
      </label>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="icon"
          aria-label="Decrease quantity"
          disabled={disabled || (current !== null && current <= MIN_QUANTITY)}
          onClick={() => step(-1)}
        >
          -
        </Button>
        <TextInput
          id="quantity"
          inputMode="numeric"
          value={value}
          disabled={disabled}
          invalid={invalid}
          onChange={(e) => onChange(e.target.value)}
          className="w-28 text-center"
        />
        <Button
          variant="secondary"
          size="icon"
          aria-label="Increase quantity"
          disabled={disabled || (current !== null && current >= MAX_QUANTITY)}
          onClick={() => step(1)}
        >
          +
        </Button>
      </div>
      {invalid && (
        <p role="alert" className="mt-1 text-sm text-danger">
          Enter a whole number from {MIN_QUANTITY} to {MAX_QUANTITY.toLocaleString("en-US")}.
        </p>
      )}
    </div>
  );
}
