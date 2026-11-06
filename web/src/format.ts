/** Display formatting for money, numbers with units, and dates. */
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function formatMoney(value: number | null | undefined): string {
  return value == null ? "-" : usd.format(value);
}

export function formatNumber(value: number, digits = 2): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export const MM_PER_INCH = 25.4;

/** A length converted from mm; `withUnit: false` gives just the number, e.g. for "a × b × c mm". */
export function formatLength(mm: number, unit: "mm" | "in", withUnit = true): string {
  const text = unit === "mm" ? formatNumber(mm) : formatNumber(mm / MM_PER_INCH, 3);
  return withUnit ? `${text} ${unit}` : text;
}

export function formatDays(days: number | null | undefined): string {
  if (days == null) return "-";
  return `${days} business ${days === 1 ? "day" : "days"}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" });
}
