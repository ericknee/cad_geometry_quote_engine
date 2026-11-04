/** Every URL pattern in the app. Build concrete paths with the helpers below. */
export const routes = {
  newQuote: "/",
  dashboard: "/quotes",
  quote: (id: string) => `/quotes/${id}`,
} as const;
