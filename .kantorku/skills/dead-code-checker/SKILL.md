---
name: dead-code-checker
description: Detect dead code and unwired code immediately after any code deletion/refactor. Use every time classes, ids, selectors, handlers, or backend symbols are removed or renamed. Run the bundled Python checker to list all file+line usages, then classify each token as `is dead code` or `is not dead code` with verdict `wire|delete|legacy|more-advance`.
---

# Dead Code Checker

## Workflow
1. Run checker after deleting code:
   `python .codex/skills/dead-code-checker/scripts/dead_code_checker.py --root . --from-git-diff`
2. If needed, run explicit tokens:
   `python .codex/skills/dead-code-checker/scripts/dead_code_checker.py --root . --token class:foo --token id:bar --token symbol:Baz`
3. Read output per token:
- `path`
- `line`
- `role`
- `status`: `is dead code` / `is not dead code`
- `verdict`: `wired`, `unwired-to-html`, `legacy-html-only`, `backend-unwired-to-html`
4. Apply decision:
- `wire`: keep and reconnect references.
- `delete`: remove leftover references.
- `legacy`: keep temporarily with clear reason.
- `more-advance`: redesign/refactor deeper before deletion.

## Policy
- Frontend (`class`/`id`) without HTML connection is `is dead code`.
- Backend symbols without frontend connection are treated as `backend-unwired-to-html` (aggressive policy).
- Use this skill as mandatory gate before finalizing removal PR/commit.

## Output Contract
- Always report all matched files and line numbers.
- Always print final status per token.
- Always provide a recommendation: `wire|delete|legacy|more-advance`.

## References
- See `references/verdict-policy.md` for interpretation details.
