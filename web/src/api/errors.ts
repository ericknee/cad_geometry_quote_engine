import { ApiError } from "./http";

// Backend error codes (backend/api/errors/quotes_errors.py, utils/body_limit.py) -> user-facing text.
// Codes that already carry a good server message (INVALID_FILE, INVALID_QUANTITY, FILE_TOO_LARGE,
// STATUS_CONFLICT, INVALID_STATUS_TRANSITION) fall through to that message.
const FIXED_MESSAGES: Record<string, string> = {
  QUOTE_NOT_FOUND: "We couldn't find that quote.",
};

export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return FIXED_MESSAGES[error.code] ?? error.message;
  }
  // fetch itself failed: the API is down or the network dropped.
  return "Could not reach the server. Check your connection and try again.";
}
