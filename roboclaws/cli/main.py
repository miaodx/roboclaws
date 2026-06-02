"""Roboclaws public CLI entrypoint."""

from __future__ import annotations

import sys

from roboclaws.cli.task_run import die, task_run_main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) >= 2 and args[0] == "task" and args[1] == "run":
        return task_run_main(args[2:])
    die("expected subcommand: task run")


if __name__ == "__main__":
    raise SystemExit(main())
