import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger";
export type ButtonSize = "sm" | "md" | "lg" | "icon";

const BASE =
  "inline-flex items-center justify-center whitespace-nowrap rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-primary text-primary-fg hover:bg-primary-hover",
  secondary: "border border-border-strong bg-surface text-fg hover:bg-surface-muted",
  danger: "border border-danger-border bg-surface text-danger hover:bg-danger-soft",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "px-3 py-1 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "w-full px-4 py-3",
  icon: "h-10 w-10 text-lg", // square +/- buttons
};

/** Class string for anything that should look like a button, e.g. a <Link>. */
export function buttonClasses(variant: ButtonVariant = "primary", size: ButtonSize = "md") {
  return `${BASE} ${VARIANTS[variant]} ${SIZES[size]}`;
}

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

export default function Button({
  variant = "primary",
  size = "md",
  type = "button",
  className = "",
  ...rest
}: Props) {
  return <button type={type} className={`${buttonClasses(variant, size)} ${className}`} {...rest} />;
}
