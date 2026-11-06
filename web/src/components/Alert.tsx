import type { ReactNode } from "react";

export type AlertVariant = "error" | "warning";

const VARIANTS: Record<AlertVariant, string> = {
  error: "bg-danger-soft text-danger",
  warning: "bg-warning-soft text-warning",
};

/** A tinted message box. Errors are announced to screen readers (role="alert"). */
export default function Alert({
  variant = "error",
  className = "",
  children,
}: {
  variant?: AlertVariant;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      role={variant === "error" ? "alert" : undefined}
      className={`rounded-md px-4 py-3 text-sm ${VARIANTS[variant]} ${className}`}
    >
      {children}
    </div>
  );
}
