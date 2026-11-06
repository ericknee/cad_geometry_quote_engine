import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // Colors come from the theme tokens in src/app/globals.css (bg-surface, text-fg-muted, ...).
    // Raw palette classes like bg-red-500 or text-white bypass the theme, so they are rejected.
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-syntax": [
        "error",
        ...["Literal", "TemplateElement"].map((node) => ({
          selector: `${node}[${node === "Literal" ? "value" : "value.raw"}=/\\b(?:bg|text|border|divide|ring|fill|stroke|from|via|to|outline|decoration|accent|caret|shadow)-(?:white|black|slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)(?:-\\d+)?\\b/]`,
          message: "Use a theme color token from globals.css (e.g. bg-surface, text-fg-muted) instead of a raw palette color.",
        })),
      ],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
