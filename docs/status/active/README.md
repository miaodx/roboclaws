# Active Standalone Work

Use this directory for parallel terminal or agent work that needs lightweight
coordination but should not change the repo-level dashboard in `STATUS.md`.

One standalone task owns one file:

```text
docs/status/active/<task-slug>.md
```

Keep each file short and delete or archive it when the task is done. Do not use
these files as substitutes for GSD phase plans, `docs/plans/`, issues, or
verification artifacts.

## Template

```md
# <Task Name>

Owner/session: <terminal or agent>
Started: YYYY-MM-DD HH:MM
State: active | blocked | done

## Scope

One short paragraph.

## Source Of Truth

- Plan/phase/issue: <link>

## Next Action

One concrete step.

## Touched Areas

- <path or module>

## Notes

Only details needed by another terminal to avoid conflicts.
```
