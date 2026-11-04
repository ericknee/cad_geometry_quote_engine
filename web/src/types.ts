/**
 * The one place to import types from. API types will be re-exported here once they are
 * generated from the backend's OpenAPI schema (see CLAUDE.md); client-only types live here too.
 */
export type QuoteStatus = "new" | "quoted" | "reviewed" | "archived";
