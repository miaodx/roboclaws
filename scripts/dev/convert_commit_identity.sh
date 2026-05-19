#!/usr/bin/env bash
# Rewrite a source commit history to an exported ref with deterministic identity.
#
# This script intentionally does not push, fetch, edit remotes, edit Git config,
# or move the currently checked-out branch. It writes new commit objects and then
# updates only the requested output ref.

set -euo pipefail

source_ref="origin/main"
output_ref=""
target_name="miaodongxu"
target_email="miaodongxu@xiaomi.com"

usage() {
  cat <<'EOF'
Usage:
  scripts/dev/convert_commit_identity.sh --output-ref <ref> [options]

Options:
  --source <ref>       Source commit ref to convert (default: origin/main)
  --output-ref <ref>   Full destination ref, e.g. refs/heads/mi-export (required)
  --name <name>        Author and committer name (default: miaodongxu)
  --email <email>      Author and committer email (default: miaodongxu@xiaomi.com)
  -h, --help           Show this help

The script rewrites commits reachable from --source into --output-ref, preserving
tree contents, parent topology, author date, committer date, and commit message.
It does not push, fetch, configure remotes, or move the checked-out branch.
EOF
}

die() {
  echo "error: $*" >&2
  exit 2
}

shell_quote() {
  printf "%q" "$1"
}

require_value() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" ]]; then
    die "${option} requires a value"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)
      require_value "$1" "${2:-}"
      source_ref="$2"
      shift 2
      ;;
    --output-ref)
      require_value "$1" "${2:-}"
      output_ref="$2"
      shift 2
      ;;
    --name)
      require_value "$1" "${2:-}"
      target_name="$2"
      shift 2
      ;;
    --email)
      require_value "$1" "${2:-}"
      target_email="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

if [[ -z "$output_ref" ]]; then
  die "--output-ref is required"
fi
if [[ "$output_ref" != refs/* ]]; then
  die "--output-ref must be a full ref under refs/"
fi
if ! git check-ref-format "$output_ref" >/dev/null 2>&1; then
  die "invalid --output-ref: ${output_ref}"
fi
if [[ "$target_name" == *$'\n'* || "$target_email" == *$'\n'* ]]; then
  die "--name and --email must not contain newlines"
fi
if ! command -v perl >/dev/null 2>&1; then
  die "perl is required to preserve commit messages exactly"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a Git worktree"
source_sha="$(git -C "$repo_root" rev-parse --verify "${source_ref}^{commit}" 2>/dev/null)" \
  || die "source does not resolve to a commit: ${source_ref}"

current_branch_ref="$(git -C "$repo_root" symbolic-ref -q HEAD || true)"
if [[ -n "$current_branch_ref" && "$output_ref" == "$current_branch_ref" ]]; then
  die "--output-ref points at the currently checked-out branch: ${output_ref}"
fi

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/roboclaws-convert-identity.XXXXXX")"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

clone_dir="$tmp_dir/source"
messages_dir="$tmp_dir/messages"
commit_list="$tmp_dir/commits.txt"
mkdir -p "$messages_dir"

git clone --quiet --shared --no-checkout --no-tags "$repo_root" "$clone_dir"
git -C "$clone_dir" cat-file -e "${source_sha}^{commit}"
git -C "$clone_dir" rev-list --reverse --topo-order "$source_sha" > "$commit_list"

declare -A converted_by_original=()
converted_tip=""

while IFS= read -r original_commit; do
  tree_sha="$(git -C "$clone_dir" show -s --format=%T "$original_commit")"
  author_date="$(git -C "$clone_dir" show -s --format=%ad --date=raw "$original_commit")"
  committer_date="$(git -C "$clone_dir" show -s --format=%cd --date=raw "$original_commit")"

  message_file="$messages_dir/$original_commit"
  git -C "$clone_dir" cat-file commit "$original_commit" \
    | perl -0ne 's/\A.*?\n\n//s; print' > "$message_file"

  parent_args=()
  parents_line="$(git -C "$clone_dir" show -s --format=%P "$original_commit")"
  if [[ -n "$parents_line" ]]; then
    read -r -a original_parents <<< "$parents_line"
    for original_parent in "${original_parents[@]}"; do
      converted_parent="${converted_by_original[$original_parent]:-}"
      if [[ -z "$converted_parent" ]]; then
        die "internal parent-order error while converting ${original_commit}"
      fi
      parent_args+=("-p" "$converted_parent")
    done
  fi

  converted_commit="$(
    GIT_AUTHOR_NAME="$target_name" \
      GIT_AUTHOR_EMAIL="$target_email" \
      GIT_AUTHOR_DATE="$author_date" \
      GIT_COMMITTER_NAME="$target_name" \
      GIT_COMMITTER_EMAIL="$target_email" \
      GIT_COMMITTER_DATE="$committer_date" \
      git -C "$repo_root" \
        -c commit.gpgSign=false \
        commit-tree "$tree_sha" "${parent_args[@]}" -F "$message_file"
  )"
  converted_by_original["$original_commit"]="$converted_commit"
  converted_tip="$converted_commit"
done < "$commit_list"

if [[ -z "$converted_tip" ]]; then
  die "no commits found for source: ${source_ref}"
fi

git -C "$repo_root" update-ref "$output_ref" "$converted_tip"

quoted_source_sha="$(shell_quote "$source_sha")"
quoted_output_ref="$(shell_quote "$output_ref")"

printf "source ref: %s\n" "$source_ref"
printf "output ref: %s\n" "$output_ref"
printf "original tip SHA: %s\n" "$source_sha"
printf "converted tip SHA: %s\n" "$converted_tip"
printf "\n"
printf "Verification commands:\n"
printf "  git diff --quiet %s %s\n" "$quoted_source_sha" "$quoted_output_ref"
printf "  git log --format='%%H %%an <%%ae> | %%cn <%%ce>' -n 5 %s\n" "$quoted_output_ref"
