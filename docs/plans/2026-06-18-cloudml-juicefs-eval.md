---
plan_scope: cloudml-juicefs-eval
status: Draft; details pending
created: 2026-06-18
last_reviewed: 2026-06-18
implementation_allowed: false
source:
  - user request to make formal eval runs less local-only
  - user decision to use CloudML and JuiceFS
  - user constraint that CloudML training jobs should be treated as no-network runtime
  - user decision that Docker images are validated locally, pushed to an internal registry, then consumed by CloudML
related_context:
  - ARCHITECTURE.md
  - STATUS.md
  - docs/human/evaluation.md
  - evals/household_world/README.md
---

# CloudML + JuiceFS Eval Execution Plan

## Purpose

Move formal Roboclaws eval execution from mostly local runs to a reproducible
CloudML-backed path, with JuiceFS as the shared artifact store.

The goal is not to replace local debugging. Local runs remain the fastest way to
iterate on simulator issues, UI/report review, and one-off failures. CloudML
should own formal eval evidence: clean checkout, fixed commit, fixed image,
fixed suite/sample set, fixed mount paths, and archived output that can be
compared across commits, provider profiles, and model versions.

Hard runtime constraint: treat CloudML tasks as having no network after
submission. Anything the job needs must already be in the image or on JuiceFS
before the task starts. Do not plan on `uv sync`, GitHub/GitLab clone, model
download, apt install, pip install, or remote asset fetch inside the running
CloudML container unless a separate platform proof shows that specific prefetch
path is available.

## Architecture Layer

This plan touches these existing layers:

- Eval harness / eval suite: keep `just agent::eval ...` as the authoritative
  eval contract.
- Harness recipes: add or document the CloudML launch mechanics around the eval
  contract.
- Runtime artifacts: store eval bundles, product run artifacts, job YAML, and
  logs under a stable JuiceFS layout.
- Backend runtime / environment primitive: CloudML is the execution environment
  for formal eval runs, not a new Roboclaws product backend.

Non-decision: this plan does not introduce a new public product surface, MCP
tool, capability profile, or eval schema.

## Target Shape

```text
Local / executor staging
  -> builds and verifies a Docker image with uv + Roboclaws runtime dependencies
  -> pushes the verified image to the internal Docker registry
  -> uploads asset bundles, optional uv cache/wheelhouse, and run manifest to JuiceFS

CloudML custom_train job
  -> starts from the verified internal-registry Docker image
  -> uses CloudML codeConfig to fetch Roboclaws by Git URL + commit hash
  -> mounts JuiceFS at fixed paths
  -> reads assets/environment metadata from JuiceFS or the image
  -> runs one or more `just agent::eval ...` commands
  -> copies eval outputs and job metadata into JuiceFS
```

Roboclaws eval semantics stay repo-native:

```bash
just agent::eval suite=<suite> budget=<budget> stamp=<stamp>
```

CloudML owns where and how the command runs. JuiceFS owns durable input and
output. The Docker image owns the Python/UV dependency environment. CloudML
does not re-validate or mutate that environment; it consumes the already
verified image.

## Split Of Responsibility

This plan is split into two tracks:

- **Now-verifiable Roboclaws work:** prove the offline Docker runtime, eval
  command, artifact writing, internal-registry image reference, and CloudML
  dry-run shape without waiting for new executor features.
- **Executor-resolved work:** JuiceFS path conventions, upload/download/sync
  command forms, remote listings, staged input manifests, and operator-friendly
  retrieval. These should be answered by the executor JuiceFS upgrade instead
  of hard-coded in this plan.

## Now-Verifiable Track

These checks can be done now with local Docker, the current repo, the internal
Docker Registry, and the existing CloudML executor target.

Terminology:

- `Roboclaws code`: the Roboclaws repository source code fetched by CloudML
  from Git using `code_url` plus `code_commit`.
- `asset bundle`: runtime data such as MolmoSpaces fixtures, map bundles,
  detector weights, benchmark corpora, model caches, or other non-source files.
- `eval artifacts`: outputs such as `eval_results.json`, `eval_report.html`,
  traces, run logs, and product run directories.

### 1. Offline Docker Eval Proof

Goal: prove a Docker image can run deterministic Roboclaws evals with no runtime
network.

Local proof command shape:

```bash
docker run --rm --network none \
  -v "$PWD:/workspace/roboclaws:ro" \
  -v /tmp/roboclaws-eval-output:/workspace/output \
  -e ROBOCLAWS_DEVTOOLS_PYTHON=/opt/roboclaws/.venv/bin/python \
  <image-url-or-local-tag> \
  bash -lc '
    cd /workspace/roboclaws &&
    "$ROBOCLAWS_DEVTOOLS_PYTHON" -c "import roboclaws, numpy, PIL, jinja2" &&
    just agent::eval suite=smoke_regression budget=smoke output_dir=/workspace/output
  '
```

Pass condition:

- `smoke_regression` completes without network.
- `eval_results.json` and `eval_report.html` are written under the mounted
  output directory.
- Failure is loud when the image lacks Python, `.venv`, native libraries, or
  required assets.
- Local proof can bind-mount the current checkout for simplicity. CloudML source
  fetch is covered by the dry-run/submission path, not by this Docker proof.

### 2. Docker Image Baseline

Initial image expectations:

- Python 3.12.
- `uv` installed.
- Roboclaws `dev` dependency set installed from `pyproject.toml` / `uv.lock`.
- Either `.venv/bin/python` exists at the repo root after source unpack, or
  `ROBOCLAWS_DEVTOOLS_PYTHON` points at the image-baked interpreter. Keeping a
  repo-local `.venv` gives the closest behavior to current local recipes.
- Native libraries needed by deterministic MuJoCo/MolmoSpaces smoke evals.
- `just`, `git`, `bash`, and basic diagnostics.
- No provider secrets baked into the image.

Recommended build strategy:

1. Build a dedicated eval image instead of reusing `Dockerfile.coding-agents`.
   The coding-agent image is for Codex/Claude CLIs, not the Roboclaws Python
   eval runtime.
2. Version the image by environment inputs: Dockerfile, base image, `uv.lock`,
   native libraries, and runtime scripts. Do not rebuild the image for every
   Roboclaws code commit unless that commit changes environment inputs.
3. During image build, run `uv sync --extra dev` while network is available,
   or build a portable `/opt/roboclaws/.venv` and set
   `ROBOCLAWS_DEVTOOLS_PYTHON=/opt/roboclaws/.venv/bin/python`.
4. At runtime, never run `uv sync` unless the job is explicitly an environment
   proof with network enabled.
5. Tag and push only after the offline proof passes.

Recommended tag convention:

```text
<cloudml-accessible-internal-registry>/roboclaws/eval:<short-sha>-<yyyymmdd>
```

Record the immutable image digest after push:

```bash
docker image inspect <cloudml-accessible-internal-registry>/roboclaws/eval:<tag> \
  --format '{{index .RepoDigests 0}}'
```

CloudML should use the pushed registry URL, preferably with a digest-pinned
reference when the platform accepts it. Use the internal registry namespace
that CloudML can pull from; if CloudML enforces a `micr.cloud.mioffice.cn/`
prefix, mirror or tag the verified image there.

Formal jobs should use an image digest, not just a mutable tag. If CloudML does
not accept digest-pinned image references, record the resolved digest in the
run manifest next to the submitted tag.

### 3. Deterministic Eval Matrix

Start with deterministic eval suites only:

```bash
just agent::eval suite=smoke_regression budget=smoke
just agent::eval suite=open_ended_goals budget=smoke
just agent::eval suite=map_build_consumer budget=smoke
just agent::eval suite=scene_sampler_stress budget=smoke
```

Do not include live provider execution in the first slice. Live routes require
extra proof for provider keys, runtime capacity, model outages, and in the
Codex/Claude cases the pinned coding-agent Docker runtime.

Promotion gates:

- Image promotion gate: import check plus `smoke_regression` passes in the
  local no-network Docker proof.
- First formal eval gate: the four deterministic suites above pass locally in
  no-network Docker before the first CloudML submission is treated as formal
  evidence.

### 4. CloudML Dry-Run YAML

The existing executor target can already generate a CloudML dry-run YAML. Use
this only to validate job shape before submission:

```bash
./execute.py nvs cloudml custom_train submit \
  --job_name roboclaws-eval-<short-sha>-smoke \
  --description "Roboclaws deterministic eval smoke for <code_commit>" \
  --access_type PRIVATE \
  --image_url <cloudml-accessible-internal-registry>/roboclaws/eval:<verified-tag-or-digest> \
  --image_command '<entrypoint command>' \
  --code_url <https://.../roboclaws.git> \
  --code_branch <branch> \
  --code_commit <commit-sha> \
  --juicefs_mount_configs '<juicefs-json-array>' \
  --queue_id <queue-id> \
  --priority 5 \
  --resource_priority GUARANTEED \
  --resource_name <resource-name> \
  --resource_number 1 \
  --node_number 1 \
  --dry_run true \
  --json
```

The dry-run should answer whether the image, queue, resource, Git source config,
JuiceFS mount, and entrypoint shape are valid. It should not be treated as
proof that assets are staged correctly or that the image works. The
image-working proof is the local Docker `--network none` run.

## Executor-Resolved Track

Executor already supports TOS local operations. JuiceFS support is pending, but
this plan treats JuiceFS as a peer local-operable storage target: local agents
should be able to upload, download, list, and sync files before and after
CloudML execution.

Expected future executor shape, names pending actual target implementation:

```text
local files -> executor JuiceFS upload/sync -> JuiceFS fixed prefix
CloudML job -> mounted JuiceFS prefix -> output artifacts
JuiceFS fixed prefix -> executor JuiceFS download/sync -> local review
```

Until a JuiceFS target exists, commands in this plan should stay templates, not
verified CLI syntax.

Executor should eventually own or standardize:

- JuiceFS URI/path syntax.
- Upload/sync/list/download command forms.
- Fixed input/output prefix conventions.
- Remote manifest conventions for staged asset bundles, caches, image, and
  eval command matrix.
- Retrieval commands for local report review.
- Any platform-specific convenience around CloudML job submission.

The rest of this section records design intent, not final executor CLI syntax.

## Inputs To Be Supplied By Executor Or Operator

Fill these before submitting a real CloudML job:

| Field | Required | Notes |
| --- | --- | --- |
| `code_url` | yes | Git URL CloudML can fetch. |
| `code_branch` | yes | Branch used for traceability. |
| `code_commit` | yes | Commit hash used by CloudML `codeConfig`; local uncommitted files are not formal eval input. |
| `image_url` | yes | CloudML-accessible internal-registry image URL or digest for the locally verified eval image. |
| `queue_id` | yes | CloudML queue id. |
| `resource_name` | yes | CloudML resource name from queue resources. |
| `resource_priority` | yes | Usually `GUARANTEED` for formal eval, unless cost/capacity says otherwise. |
| `priority` | yes | CloudML supports common values such as `2`, `5`, `8`. |
| `juicefs volume` | yes | JuiceFS volume name from CloudML storage console. |
| `juicefs cluster` | yes | JuiceFS cluster name. |
| `juicefs input subPath` | yes | Absolute subpath for staged assets, caches, and manifests. |
| `juicefs output subPath` | yes | Absolute subpath for eval artifacts and logs. |
| `juicefs mountPath` | yes | Absolute container path; must not be `/` or `/ml-engine/code`. |
| `suite matrix` | yes | Which suites/budgets to run in the job. |
| `stamp convention` | yes | Recommended: `<date>-<short-sha>-<suite-or-matrix>`. |

Implementation preference: use CloudML `codeConfig` as the source-code path.
That keeps source identity as Git URL + commit hash. JuiceFS is for assets,
caches, manifests, and outputs.

## JuiceFS Layout

Recommended initial layout:

```text
/mnt/roboclaws-evals/
  inputs/
    assets/
      molmospaces/
      visual-grounding/
      maps/
    caches/
      uv/
      huggingface/
      torch/
  runs/
    <yyyyMMdd>/
      <short-sha>/
        <job-name>/
          cloudml_task.yaml
          cloudml_submit.json
          command.sh
          stdout.log
          stderr.log
          output/
            evals/
              <suite-id>/
                <stamp>/
                  eval_results.json
                  eval_report.html
                  runs/
```

Keep private scorer truth out of public report bundles. If a future run needs
private grader inputs, place them under an explicitly private path and link them
only from maintainer-facing manifests.

Initial artifact policy: treat the first JuiceFS eval prefix as
maintainer-private. It may store complete eval bundles, logs, manifests, and
debug artifacts. Publishing public reports from that prefix is a later explicit
export step, not the default behavior.

## Local Asset Staging

Before submitting CloudML, local/executor staging should prepare everything the
job needs:

- Asset bundles: MolmoSpaces fixtures, map bundles, generated eval samples,
  detector weights, and any benchmark corpora needed by selected suites.
- Optional caches: uv cache, model cache, torch cache, and other large immutable
  downloads. Caches are an optimization only; the first formal deterministic
  path should work from the pinned image plus staged assets.
- Run manifest: commit SHA, branch, image URL, suite matrix, expected JuiceFS
  input/output prefixes, and exact eval commands.

This staging step is where future executor JuiceFS support should mirror the
current TOS ergonomics: upload/sync local files, verify remote listing, and
download/sync results for review.

Every staged input prefix should include a manifest:

```json
{
  "schema": "roboclaws_cloudml_eval_inputs_v1",
  "created_at": "<iso8601>",
  "git": {
    "url": "<repo-url>",
    "branch": "<branch>",
    "commit": "<sha>",
    "source_path": "cloudml.codeConfig"
  },
  "image": {
    "url": "<cloudml-accessible-internal-registry>/roboclaws/eval:<tag-or-digest>",
    "python": "<path>",
    "uv_lock_sha256": "<sha256>"
  },
  "assets": [
    {
      "name": "molmospaces",
      "path": "assets/molmospaces",
      "sha256_manifest": "assets/molmospaces.sha256"
    }
  ],
  "eval": {
    "commands": [
      "just agent::eval suite=smoke_regression budget=smoke stamp=<stamp>"
    ]
  }
}
```

The manifest is more important than the exact directory names. It is the object
that lets two eval runs answer whether they used the same code, image, assets,
and suite matrix.

## Docker Image Strategy
See **Now-Verifiable Track**. This is the first thing to prove before relying on
CloudML.

## CloudML Submit Template
See **Now-Verifiable Track** for the current dry-run command shape. After
reviewing the generated YAML, submit the same command without `--dry_run true`.

Example JuiceFS config shape:

```json
[
  {
    "volume": "<JuiceFSVolumeName>",
    "subPath": "/roboclaws/evals",
    "juiceFsCluster": "<juiceFsClusterName>",
    "mountPath": "/mnt/roboclaws-evals",
    "readOnly": false
  }
]
```

## Entrypoint Sketch

The entrypoint should fail loudly and preserve artifacts even when an eval
fails. It must not rely on network after CloudML has prepared the container.
Roboclaws code should already be present through CloudML `codeConfig`.

```bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-}"
JUICEFS_ROOT="/mnt/roboclaws-evals"
WORK_ROOT="/workspace/roboclaws-eval"
ARTIFACT_ROOT="$JUICEFS_ROOT/runs/<date>/<short-sha>/<job-name>"
STAMP="<date>-<short-sha>-smoke"

mkdir -p "$ARTIFACT_ROOT" "$WORK_ROOT"
if [ -z "$REPO_DIR" ]; then
  for candidate in /ml-engine/code/roboclaws /ml-engine/code/roboclaws.git; do
    if [ -d "$candidate/.git" ]; then
      REPO_DIR="$candidate"
      break
    fi
  done
fi

test -n "$REPO_DIR"
cd "$REPO_DIR"

if [ -z "${ROBOCLAWS_DEVTOOLS_PYTHON:-}" ]; then
  if [ -x "$REPO_DIR/.venv/bin/python" ]; then
    export ROBOCLAWS_DEVTOOLS_PYTHON="$REPO_DIR/.venv/bin/python"
  else
    export ROBOCLAWS_DEVTOOLS_PYTHON="/opt/roboclaws/.venv/bin/python"
  fi
fi
test -x "$ROBOCLAWS_DEVTOOLS_PYTHON"
"$ROBOCLAWS_DEVTOOLS_PYTHON" -c "import roboclaws, numpy, PIL, jinja2"
if git rev-parse HEAD >/dev/null 2>&1; then
  git rev-parse HEAD > "$ARTIFACT_ROOT/code_commit.txt"
else
  printf '%s\n' "<commit-sha>" > "$ARTIFACT_ROOT/code_commit.txt"
fi

set +e
just agent::eval suite=smoke_regression budget=smoke stamp="$STAMP-smoke-regression"
SMOKE_STATUS=$?
just agent::eval suite=open_ended_goals budget=smoke stamp="$STAMP-open-ended-goals"
OPEN_STATUS=$?
just agent::eval suite=map_build_consumer budget=smoke stamp="$STAMP-map-build-consumer"
MAP_STATUS=$?
just agent::eval suite=scene_sampler_stress budget=smoke stamp="$STAMP-scene-sampler-stress"
SCENE_STATUS=$?
set -e

mkdir -p "$ARTIFACT_ROOT/output"
cp -a output/evals "$ARTIFACT_ROOT/output/"

cat > "$ARTIFACT_ROOT/exit_status.json" <<EOF
{
  "smoke_regression": $SMOKE_STATUS,
  "open_ended_goals": $OPEN_STATUS,
  "map_build_consumer": $MAP_STATUS,
  "scene_sampler_stress": $SCENE_STATUS
}
EOF

test "$SMOKE_STATUS" -eq 0
test "$OPEN_STATUS" -eq 0
test "$MAP_STATUS" -eq 0
test "$SCENE_STATUS" -eq 0
```

Before implementation, verify the CloudML checkout path and replace the
discovery snippet with a fixed path once the platform behavior is known.

## Monitoring Commands

Query a job:

```bash
./execute.py nvs cloudml custom_train query \
  --job_ids <job-id> \
  --json
```

Describe a job:

```bash
./execute.py nvs cloudml custom_train describe \
  --job_id <job-id> \
  --json
```

Fetch logs:

```bash
./execute.py nvs cloudml custom_train log \
  --job_id <job-id> \
  --lines 2000
```

Stopping jobs is a state-changing operation. Only run stop commands after
explicit human confirmation.

## Reproducibility Contract

A formal CloudML eval result is comparable only if it records:

- Git URL, branch, and commit SHA.
- Docker image URL.
- CloudML queue/resource metadata.
- JuiceFS artifact root.
- JuiceFS input manifest and staged asset bundle hashes.
- Exact `just agent::eval ...` commands.
- Eval suite id, budget, stamp, and sample/trial identity.
- Provider profile and `live_execution` setting, if any.
- Exit status and CloudML job id.

Uncommitted local files are not part of a formal CloudML eval. If a test needs
local changes, push them to a branch and pass the resulting commit SHA.

## Live Eval Follow-up

After deterministic suites work:

1. Add `live_execution=run` for `open_ended_goals` with one provider profile
   that does not require the coding-agent Docker runtime.
2. Record provider/runtime failures separately from behavior failures, matching
   the current eval runner contract.
3. Prove whether CloudML can support the pinned Codex/Claude Docker runtime
   before enabling Codex CLI or Claude Code live evals.
4. Only then add repeated live-agent `cleanup_capability` runs for `pass@k` and
   `pass^k`.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/2026-06-18-cloudml-juicefs-eval.md` plus discussion.

Canonical source: `docs/plans/2026-06-18-cloudml-juicefs-eval.md`.

Route: durable `$intuitive-flow`.

Goal: prove the first local validation slice for CloudML evals by building a
local offline-capable Roboclaws eval Docker image and running deterministic
eval smoke with `--network none`.

Scope:

- Add a dedicated eval Docker image definition if no suitable image already
  exists.
- Build an image with Python 3.12, `uv`, `just`, native runtime dependencies,
  and Roboclaws `dev` dependencies.
- Verify locally with a bind-mounted checkout and no runtime network.
- Record image versioning assumptions: environment image is versioned by
  Dockerfile, base image, `uv.lock`, and native dependencies, not by every
  Roboclaws commit.
- Keep CloudML dry-run command documented, but run it only if registry image
  URL, queue/resource, and JuiceFS mount config are supplied.

Non-goals:

- No executor JuiceFS target implementation.
- No real CloudML job submission unless explicitly approved after dry-run.
- No live provider evals, Codex/Claude live routes, or `live_execution=run`.
- No public report publishing from JuiceFS.
- No change to `just agent::eval` semantics.

Entity budget:

- Reuse: `just agent::eval`, current eval suites, `pyproject.toml`, `uv.lock`,
  and the CloudML executor target.
- Remove/merge: none.
- New: one eval Dockerfile and optionally one small local proof script, only if
  needed to make the proof repeatable.
- Expansion triggers: adding executor targets, submitting real CloudML jobs,
  handling provider credentials, changing eval suite semantics, or publishing
  reports.

Context:

- Must-read: this plan, `docs/human/evaluation.md`,
  `evals/household_world/README.md`, `pyproject.toml`, `uv.lock`, and
  `just/agent.just`.
- Useful: `Dockerfile.coding-agents` as a non-reuse contrast, and CloudML
  executor help.
- Avoid unless needed: historical plans and live-agent implementation details.

Acceptance:

- SUCCESS: local Docker image runs
  `just agent::eval suite=smoke_regression budget=smoke` with `--network none`
  and writes `eval_results.json` plus `eval_report.html`.
- BLOCKED_NEEDS_DECISION: real CloudML dry-run or push requires registry URL,
  queue/resource, and JuiceFS mount config.
- BLOCKED_NEEDS_LOCAL_VALIDATION: Docker unavailable or image build cannot
  complete on the local machine.
- INTERMEDIATE_ONLY: Dockerfile builds but offline eval fails; keep logs and
  failure reason.
- No regressions: existing local `.venv` workflow and `just agent::eval` remain
  unchanged.

Verification:

- Deterministic: `git diff --check`, plus focused Dockerfile/script shell
  syntax check if added.
- Integration: `docker build ...`, then
  `docker run --rm --network none ... just agent::eval suite=smoke_regression budget=smoke output_dir=/workspace/output`.
- Product-run: none; this is eval infrastructure proof, not a public robot run
  change.
- Local/live/manual: Docker build/run is required locally; CloudML dry-run is
  optional if required parameters are provided.
- Optional: run the four deterministic suites locally offline after smoke
  passes.

Execution:

- Main: supervise image definition, build, offline smoke, artifact inspection,
  and plan update with result.
- Worker: none.
- Worker goal: none.

To execute:

```text
/goal execute docs/plans/2026-06-18-cloudml-juicefs-eval.md with intuitive-flow
```

Optional tracking: none.

Approval: `LGTM`, `approve`, or `go ahead` approves; edits request revision.

## Acceptance Criteria

- Future executor JuiceFS commands can upload staged assets/caches/manifests
  and download result bundles with the same ergonomics as current TOS
  operations.
- A local Docker run with `--network none` can execute at least
  `smoke_regression` from a read-only source checkout and write eval output to a
  mounted directory.
- A dry-run CloudML YAML can be generated for a pushed Roboclaws commit.
- One CloudML deterministic smoke job runs without runtime network dependency.
- The job writes `eval_results.json` and `eval_report.html` under JuiceFS.
- The local operator can retrieve the result by commit/suite/stamp without
  inspecting local machine state.
- Missing CloudML config, missing JuiceFS mount fields, missing code commit, or
  missing staged assets fails loudly.

## Deferred Work

- A dedicated executor workflow or target for Roboclaws eval submission.
- A report index that compares two JuiceFS eval roots by suite/sample/trial.
- CloudML image promotion automation after the local offline proof passes.
- Live provider key handling and redacted metrics capture.
- Scheduled nightly or pre-release eval runs.
