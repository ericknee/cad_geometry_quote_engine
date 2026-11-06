import type { SelectHTMLAttributes } from "react";

/** A native select with the app's control styling. Pass `className` for size tweaks. */
export default function Select({ className = "", ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`h-9 rounded-md border border-border-strong bg-surface px-2 text-sm text-fg disabled:opacity-50 ${className}`}
      {...rest}
    />
  );
}
