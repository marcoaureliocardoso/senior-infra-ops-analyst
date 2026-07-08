# Contributing

Before proposing a change:

1. Keep operational instructions evidence-based and approval-gated.
2. Use shared risk vocabulary from `references/risk-levels.md`.
3. Do not add commands that expose secrets, personal data, or broad inventories without modifiers and safety notes.
4. Run `make validate-local` before packaging.
5. Add or update templates when a skill requires a structured output.
6. Prefer official vendor documentation and standards in `references/external-sources.md`.

A change is not ready if it introduces a second diagnostic order, a local risk taxonomy, an empty template, or unvalidated helper script behavior.
