# Verdict Policy

## Frontend (class/id)
- `is dead code` + `unwired-to-html`:
  - token appears in css/js/backend but no html declaration/reference.
  - default action: `delete` unless explicitly rewired.
- `is not dead code` + `wired`:
  - token has html + css/js linkage.
  - default action: `keep`.
- `is not dead code` + `legacy-html-only`:
  - token exists only in html without css/js linkage.
  - default action: `legacy` (verify with product owner).

## Backend (symbol)
- `is dead code` + `backend-unwired-to-html`:
  - symbol only appears in backend files, not wired to frontend/html/css/js.
  - default action: `wire`, `delete`, or `more-advance` based on architecture intent.

## Recommended Sequence
1. Run checker.
2. Group by verdict.
3. Remove dead leftovers first.
4. Re-run checker to ensure no remaining unwired references.
