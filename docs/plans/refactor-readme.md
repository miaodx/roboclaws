---
refactor_scope: readme
status: DONE
accepted_severities:
  - P0
  - P1
last_verified: "2026-05-14"
---

# Refactor Scope: README

## Status

DONE

## Target

`README.md` as the public first-read surface for Roboclaws.

## Accepted Severities

- P0: Remove any credential-looking or secret material from the README.
- P1: Make the first-read story clear: what Roboclaws does, how to run demos
  through the public `just task::run` grammar, and where CI-published live demos
  are visible.

## Accepted P0/P1 Checklist

- [x] Remove credential-looking material from `README.md`.
- [x] Replace the current mixed orientation with a compact "what it does" section.
- [x] Make runnable demos discoverable from one `just` command table.
- [x] Add direct CI/Pages demo links, including MolmoSpaces live cleanup results.
- [x] Remove duplicate or lower-level run instructions that belong in deeper docs.
- [x] Merge the old "What It Does" and "Live CI Reports" sections into one
  demo matrix.
- [x] Add a dedicated MolmoSpaces live cleanup Pages entry point.
- [x] Remove planner-proof harness commands from the README first-read path.
- [x] Add top-of-report local rerun commands for CI-published report pages.

## Parked P2 / Future Ideas

- Add screenshots for the MolmoSpaces live report tiles after the public Pages
  links are stable.
- Add a generated README command table from the `just` router if the command
  surface changes frequently.
- Backfill already-published Pages artifacts; existing public Pages reports will
  only show rerun panels after the next successful deploy regenerates them.

## Evidence Ladder

- L0 static: inspect the README for leaked-secret patterns, stale branch-only
  wording, and Markdown link shape.
- L1 docs smoke: run focused grep checks for the required sections and links.
- L2 report contract: run focused report renderer tests and one generated-report
  smoke so the README-linked CI artifacts expose local rerun commands.

## Stop Condition

Stop when the README has no credential-looking line, presents the public demo
surface through `just`, links the CI/Pages artifacts including MolmoSpaces live
cleanup, generated report pages expose local rerun commands, and the L0-L2
checks pass.

## Execution Log

- 2026-05-14: Created scope gate for README organization refactor.
- 2026-05-14: Rewrote README around demo purpose, public `just` commands,
  CI/Pages links, and deeper-doc routing.
- 2026-05-14: Verified required README sections, local Markdown links, and
  credential-looking pattern cleanup.
- 2026-05-14: Folded demo purpose, local command, and live CI link into one
  README matrix; added `/molmo/live/` as the dedicated MolmoSpaces live page;
  left planner-proof commands in deeper MolmoSpaces docs instead of the README.
- 2026-05-14: Verified with targeted ruff check/format, Molmo live Pages unit
  tests, README link check, required-section grep, secret-pattern grep, and
  `git diff --check`.
- 2026-05-14: Added reusable report rerun panels to game, autonomous replay,
  Molmo cleanup, and Molmo live index outputs. Verified targeted report tests
  and a mock report generation smoke under `/tmp`.
