/** Client-side mirrors of the API's limits. The server still enforces them (settings.max_upload_mb). */
export const MAX_UPLOAD_MB = 50;
export const MIN_QUANTITY = 1;
export const MAX_QUANTITY = 10_000;
export const ACCEPTED_EXTENSIONS = [".step", ".stp"] as const;

export function hasAcceptedExtension(name: string): boolean {
  const lower = name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

/** Returns an error message, or null when the file is acceptable. */
export function checkFile(file: File): string | null {
  if (!hasAcceptedExtension(file.name)) return "Only .step or .stp files are supported.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `The file is larger than ${MAX_UPLOAD_MB} MB.`;
  return null;
}
