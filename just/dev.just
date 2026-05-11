# Dev workflow — git hooks, pytest split, repo-wide self-check.
#
# Test split invariant:
#   - test-fast        : what the pre-commit hook runs (no Docker, no real provider).
#   - test-unit        : fast isolated public-API behavior tests.
#   - test-contract    : public schema/tool/report/recipe compatibility tests.
#   - test-regression  : known-bug and artifact-regression coverage.
#   - test-integration : what the post-merge hook runs in background
#                        (Docker-gated tests + anything touching a real
#                        model provider).
# Integration tests should never fire on every `git commit`. They live behind
# `@pytest.mark.integration`.

set working-directory := '..'

standalone_pytest := "./scripts/run_pytest_standalone.sh"

# Default: list module recipes (avoids accidentally rewiring git hooks).
default:
    @just --list dev

install-hooks:
    @git config core.hooksPath .githooks
    @echo "==> git hooks installed (core.hooksPath = .githooks)"
    @echo "    pre-commit : ruff + fast pytest"
    @echo "    post-merge : integration tests, backgrounded, log in .git/integration-last.log"
    @echo "    bypass     : git commit --no-verify   or   SKIP_TESTS=1 git commit"

uninstall-hooks:
    -@git config --unset core.hooksPath
    @echo "==> git hooks uninstalled (core.hooksPath reset)"

test kind="all":
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{kind}}" in
      fast)
        {{standalone_pytest}} -m "not integration" -q --durations=5
        ;;

      unit)
        {{standalone_pytest}} -m unit -q --durations=5
        ;;

      contract)
        {{standalone_pytest}} -m contract -q --durations=5
        ;;

      regression)
        {{standalone_pytest}} -m regression -q --durations=5
        ;;

      integration)
        {{standalone_pytest}} -m integration -q --durations=10
        ;;

      all)
        OPENCLAW_DEFAULT_IMAGE="$(awk -F= '$1=="OPENCLAW_IMAGE_DEFAULT"{print $2}' scripts/openclaw-defaults.env | tr -d '\"')"
        if [[ -z "${OPENCLAW_DEFAULT_IMAGE}" ]]; then
          echo "error: missing OPENCLAW_IMAGE_DEFAULT in scripts/openclaw-defaults.env" >&2
          exit 1
        fi
        OPENCLAW_IMG="${OPENCLAW_IMG:-${OPENCLAW_IMAGE:-$OPENCLAW_DEFAULT_IMAGE}}"
        if ! command -v docker >/dev/null 2>&1; then
          echo "warning: docker not on PATH — live OpenClaw tests will skip"
        elif ! docker image inspect "$OPENCLAW_IMG" >/dev/null 2>&1; then
          echo "==> pulling $OPENCLAW_IMG (one-time, ~700MB)"
          docker pull "$OPENCLAW_IMG" >/dev/null \
            || echo "warning: docker pull failed — live OpenClaw tests will skip"
        else
          echo "==> $OPENCLAW_IMG already cached"
        fi
        {{standalone_pytest}} -m "not integration" -q --durations=5
        {{standalone_pytest}} -m integration -q --durations=10
        ;;

      *)
        echo "error: unknown test kind '{{kind}}' (expected fast|unit|contract|regression|integration|all)" >&2
        exit 1
        ;;
    esac
