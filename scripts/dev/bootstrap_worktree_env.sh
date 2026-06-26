#!/usr/bin/env bash
# Prepare an isolated git worktree to use the baseline checkout's uv environment.
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: scripts/dev/bootstrap_worktree_env.sh [--baseline <repo>] [--repo-root <repo>] [--force-venv-link] [--no-submodules]

Creates .venv as a symlink to the baseline checkout's .venv, updates pinned
submodules, then runs the Roboclaws worktree readiness check.

Set ROBOCLAWS_BASELINE_REPO=/path/to/main/checkout to avoid passing --baseline.
EOF
}

repo_root=""
baseline_repo="${ROBOCLAWS_BASELINE_REPO:-}"
force_venv_link=0
update_submodules=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --baseline)
      baseline_repo="${2:-}"
      shift 2
      ;;
    --repo-root)
      repo_root="${2:-}"
      shift 2
      ;;
    --force-venv-link)
      force_venv_link=1
      shift
      ;;
    --no-submodules)
      update_submodules=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$repo_root" ]]; then
  repo_root="$(git rev-parse --show-toplevel)"
fi
repo_root="$(cd "$repo_root" && pwd)"

if [[ -z "$baseline_repo" ]]; then
  baseline_repo="$repo_root"
fi
baseline_repo="$(cd "$baseline_repo" && pwd)"

baseline_python="$baseline_repo/.venv/bin/python"
baseline_pytest="$baseline_repo/.venv/bin/pytest"
if [[ ! -x "$baseline_python" || ! -x "$baseline_pytest" ]]; then
  echo "error: baseline repo does not have a ready uv env: $baseline_repo/.venv" >&2
  echo "       run 'uv sync --extra dev' there, or pass --baseline /path/to/main-checkout" >&2
  exit 1
fi

target_venv="$repo_root/.venv"
baseline_venv="$baseline_repo/.venv"
if [[ -L "$target_venv" ]]; then
  current_target="$(readlink "$target_venv")"
  if [[ "$current_target" != "$baseline_venv" && "$force_venv_link" != "1" ]]; then
    echo "error: $target_venv points to $current_target, not $baseline_venv" >&2
    echo "       rerun with --force-venv-link to replace the link" >&2
    exit 1
  fi
  if [[ "$current_target" != "$baseline_venv" ]]; then
    rm "$target_venv"
    ln -s "$baseline_venv" "$target_venv"
  fi
elif [[ -e "$target_venv" ]]; then
  if [[ "$repo_root" == "$baseline_repo" ]]; then
    :
  elif [[ "$force_venv_link" == "1" ]]; then
    rm -rf -- "$target_venv"
    ln -s "$baseline_venv" "$target_venv"
  else
    echo "error: $target_venv already exists and is not a symlink" >&2
    echo "       keep per-worktree envs, or rerun with --force-venv-link to replace it" >&2
    exit 1
  fi
else
  ln -s "$baseline_venv" "$target_venv"
fi

if [[ "$update_submodules" == "1" ]]; then
  git -C "$repo_root" submodule sync --recursive
  if [[ "$repo_root" != "$baseline_repo" && -f "$repo_root/.gitmodules" ]]; then
    while read -r key submodule_path; do
      submodule_name="${key#submodule.}"
      submodule_name="${submodule_name%.path}"
      baseline_submodule="$baseline_repo/$submodule_path"
      if [[ ! -d "$baseline_submodule" ]]; then
        continue
      fi
      expected_commit="$(
        git -C "$repo_root" ls-tree HEAD "$submodule_path" | awk '{print $3}'
      )"
      if [[ -z "$expected_commit" ]]; then
        continue
      fi
      if git -C "$baseline_submodule" cat-file -e "$expected_commit^{commit}" 2>/dev/null; then
        git -C "$repo_root" submodule init -- "$submodule_path" >/dev/null
        git -C "$repo_root" config "submodule.$submodule_name.url" "$baseline_submodule"
      fi
    done < <(git -C "$repo_root" config --file .gitmodules --get-regexp '^submodule\..*\.path$')
  fi
  if [[ "$repo_root" != "$baseline_repo" ]]; then
    git -C "$repo_root" -c protocol.file.allow=always submodule update --init --recursive
  else
    git -C "$repo_root" submodule update --init --recursive
  fi
fi

"$baseline_python" "$repo_root/scripts/dev/check_worktree_readiness.py" --repo-root "$repo_root"
