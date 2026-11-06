import type { InputHTMLAttributes } from "react";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

/** A text input with the app's control styling; `invalid` turns the outline red. */
export default function TextInput({ invalid = false, className = "", ...rest }: Props) {
  return (
    <input
      aria-invalid={invalid}
      className={`h-10 rounded-md border bg-surface px-3 text-fg disabled:opacity-60 ${
        invalid ? "border-danger" : "border-border-strong"
      } ${className}`}
      {...rest}
    />
  );
}
