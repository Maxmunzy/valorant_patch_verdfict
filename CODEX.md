# CODEX Change Log

This file summarizes the non-README changes made in this pass so another agent can continue safely.

## Scope

- `README.md` and `README_KR.md` were restored to the user's preferred state and are not part of the intended code changes.
- The changes below cover backend safety, frontend reliability, and local verification support.

## Backend changes

- Reworked `main.py` startup flow.
  - Added runtime file checks for required artifacts.
  - Made `/health` report readiness and missing files more safely.
  - Removed the old direct-run port-kill behavior.
  - Kept reload support but return clearer failure states.
- Updated `predict_service.py`.
  - Runtime files are now resolved relative to the project root.
  - Model/data/cache loading now fails with clearer missing-file errors.

## Frontend changes

- Updated `frontend/app/layout.tsx`.
  - Removed remote Google font fetching to avoid build failures in restricted environments.
  - Kept the same overall shell but with local-safe styling.
- Cleaned up key user-facing copy and presentation in:
  - `frontend/app/page.tsx`
  - `frontend/components/AgentCard.tsx`
  - `frontend/components/TldrHero.tsx`
  - `frontend/components/TrustBlock.tsx`
  - `frontend/components/Disclaimer.tsx`
  - `frontend/lib/constants.ts`
  - `frontend/lib/headline.ts`
- Added `typecheck` script to `frontend/package.json`.
- Replaced the default template content in `frontend/README.md` with project-specific instructions.
- Improved readability for user-facing typography:
  - Agent names in multiple views were moved away from condensed display styling.
  - The main percentage readout in `frontend/components/AgentDetailClient.tsx` now uses numeric styling for better legibility.

## Test and DX changes

- Added `pytest.ini` to disable pytest cacheprovider, which was producing local permission warnings for `.pytest_cache`.

## Validation performed

- `pytest tests/test_api_smoke.py -q`
  - Passed.
- `npm.cmd run typecheck` in `frontend`
  - Passed.
- `npm.cmd run build` in `frontend`
  - Next.js compilation completed, but the final build process hit Windows sandbox `spawn EPERM` after compilation.
  - This looks environment-related rather than a TypeScript or source compile error.

## Files intended for commit

- `main.py`
- `predict_service.py`
- `frontend/README.md`
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/components/AgentCard.tsx`
- `frontend/components/Disclaimer.tsx`
- `frontend/components/TldrHero.tsx`
- `frontend/components/TrustBlock.tsx`
- `frontend/lib/constants.ts`
- `frontend/lib/headline.ts`
- `frontend/package.json`
- `frontend/components/AgentDetailClient.tsx`
- `pytest.ini`
- `CODEX.md`
