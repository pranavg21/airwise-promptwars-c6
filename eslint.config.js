import js from "@eslint/js";
import globals from "globals";

/**
 * Browser modules must stay small and shallow: these limits fail the build rather than warn.
 * Tests and this config run under Node.
 */
export default [
  { ignores: ["node_modules/", "htmlcov/", ".venv/"] },
  js.configs.recommended,
  {
    files: ["static/js/**/*.js"],
    languageOptions: { ecmaVersion: 2024, sourceType: "module", globals: globals.browser },
    rules: {
      complexity: ["error", 10],
      "max-depth": ["error", 3],
      "max-params": ["error", 4],
      "max-lines": ["error", { max: 200, skipBlankLines: true, skipComments: true }],
      "max-lines-per-function": ["error", { max: 40, skipBlankLines: true, skipComments: true }],
      "max-nested-callbacks": ["error", 3],
      eqeqeq: "error",
      "no-implicit-globals": "error",
      "no-var": "error",
      "prefer-const": "error",
    },
  },
  {
    files: ["tests/js/**/*.js", "eslint.config.js"],
    languageOptions: { ecmaVersion: 2024, sourceType: "module", globals: globals.node },
  },
];
