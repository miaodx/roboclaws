#!/usr/bin/env bash
# openclaw-bootstrap.sh — idempotent first-run setup for a local OpenClaw Gateway
# with N named agents (agent-0, agent-1, ...), each with its own isolated
# workspace, auth profile, and bind-mounted skill.
#
# Does:
#   1. Pre-create every dir the Gateway + all N agents will need (as root).
#   2. Seed openclaw.json:
#        - gateway.http.endpoints.chatCompletions.enabled = true
#        - agents map: each agent-i entry with its own workspace + model pin
#   3. Seed each agent-i's auth-profiles.json with the provider api_key.
#   4. Chown the volume to uid 1000 (node user).
#   5. Start the Gateway — one --mount per agent so each has its own skill dir.
#   6. Wait for /readyz.
#   7. Probe /v1/chat/completions on agent-0 with a PONG turn (fail fast if
#      anything in the skill/auth/model chain is broken).
#   8. Echo the live bearer token on stdout (only thing on stdout — everything
#      else goes to stderr so `TOKEN=$(scripts/openclaw-bootstrap.sh)` works).
#
# Environment (all optional unless marked required, sensible defaults):
#   AGENTS       Number of named agents to create    (default: 2; must be 1..8)
#   AGENT_PREFIX Name prefix for agents              (default: agent-)
#   CONTAINER    Container name                      (default: openclaw-gateway)
#   IMAGE        Gateway image                       (default: ghcr.io/openclaw/openclaw:2026.4.14)
#   VOLUME       Named volume for /home/node/.openclaw (default: openclaw-gateway-config)
#   HOST_IP      Bind address on the host            (default: 127.0.0.1)
#   PORT         Gateway port                        (default: 18789)
#   PROVIDER     Upstream LLM provider               (auto-detected from env —
#                                                     nvidia | kimi)
#   MODEL        Model id each agent uses            (default per PROVIDER — see below)
#   SKILLS_DIR   Host path of the skill to mount     (default: $PWD/skills/ai2thor-navigator)
#   READY_TIMEOUT  Seconds to wait for /readyz       (default: 60)
#
# Provider-specific vars (only the one matching PROVIDER is required):
#   KIMI_API_KEY   (PROVIDER=kimi)   Moonshot/Kimi API key
#   NV_API_KEY     (PROVIDER=nvidia) NVIDIA NIM API key (NVIDIA_API_KEY also accepted)
#
# Supported providers + default model (curated to just the one verified-
# working vision model per provider):
#
#   nvidia → nvidia/nvidia/nemotron-nano-12b-v2-vl  (free; vision; multi-image)
#   kimi   → kimi/k2p5                              (free coding tier; vision;
#                                                    aliases to kimi-for-coding
#                                                    upstream which is currently
#                                                    Kimi 2.6 — see
#                                                    /app/dist/provider-catalog-BCrO6TZn.js)
#
# Auto-detection order when PROVIDER is unset: nvidia → kimi (prefers the
# verified-working provider; first provider with an API key in env wins).
#
# Why these two and not more: the demo sends FPV + overhead per turn
# (2 images) so the model must support multi-image input. NVIDIA NIM's
# nvidia/nemotron-nano-12b-v2-vl is the only NIM vision model that
# survives all end-to-end constraints (multi-image + tool use from the
# Gateway's agent framework). Kimi's coding-tier provider via the
# Gateway plugin accepts multi-image too. Other models we probed hit
# one of: 1-image cap, no tool-use support on :free, or server-side
# errors. History lives in docs/openclaw-local.md if you want to
# re-evaluate after NIM / OpenRouter update their free-tier lineup.
#
# Exit codes:
#   0  success (token on stdout)
#   1  missing provider api key or AGENTS out of range
#   2  docker pull / run / volume / pre-seed error
#   3  Gateway /readyz never returned 200 within READY_TIMEOUT seconds
#   4  /v1/chat/completions probe against agent-0 failed
#   5  personality divergence probe failed (agents returned identical strategies)
#
set -euo pipefail

AGENTS="${AGENTS:-2}"
AGENT_PREFIX="${AGENT_PREFIX:-agent-}"
CONTAINER="${CONTAINER:-openclaw-gateway}"
IMAGE="${IMAGE:-ghcr.io/openclaw/openclaw:2026.4.14}"
VOLUME="${VOLUME:-openclaw-gateway-config}"
HOST_IP="${HOST_IP:-127.0.0.1}"
PORT="${PORT:-18789}"
SKILLS_DIR="${SKILLS_DIR:-${PWD}/skills/ai2thor-navigator}"
SOULS_DIR="${SOULS_DIR:-${PWD}/skills/ai2thor-navigator/souls}"
AGENT_SOULS="${AGENT_SOULS:-}"
PERSONALITY_PROBE="${PERSONALITY_PROBE:-1}"
READY_TIMEOUT="${READY_TIMEOUT:-60}"

# Auto-detect PROVIDER when unset:
#   1) nvidia — if NV_API_KEY / NVIDIA_API_KEY is set (verified-working,
#      free NIM vision model with multi-image support)
#   2) kimi   — otherwise (free coding tier, vision; resolves to the
#      current kimi-for-coding upstream alias)
if [[ -z "${PROVIDER:-}" ]]; then
    if [[ -n "${NV_API_KEY:-}${NVIDIA_API_KEY:-}" ]]; then
        PROVIDER="nvidia"
    else
        PROVIDER="kimi"
    fi
fi

log() { printf '[bootstrap] %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit "${2:-1}"; }

command -v docker >/dev/null 2>&1 || die "docker not found in PATH" 2
command -v python3 >/dev/null 2>&1 || die "python3 not found in PATH (needed for JSON)" 2

# Provider-specific defaults + api-key lookup + custom model catalog entries.
#
# EXTRA_MODELS_JSON is a JSON array of extension entries injected into
# openclaw.json → models.providers.<provider>.models so the Gateway's
# catalog merger recognizes models that aren't in the pinned image's
# built-in provider plugin catalog. Without this, the Gateway rejects the
# model with 400 "Unknown model".
case "$PROVIDER" in
    kimi)
        # kimi/k2p5 is the Gateway alias for the Kimi "coding" tier —
        # aliased upstream to kimi-for-coding, which is currently Kimi 2.6
        # (see /app/dist/provider-catalog-BCrO6TZn.js: KIMI_UPSTREAM_MODEL_ID
        # and cdcd298 for the roboclaws-side k2.6 default commit). Free.
        MODEL="${MODEL:-kimi/k2p5}"
        PROVIDER_API_KEY="${KIMI_API_KEY:-}"
        PROVIDER_ENV_VAR="KIMI_API_KEY"
        PROVIDER_BASE_URL=""   # built-in catalog has the baseUrl; no override needed
        EXTRA_MODELS_JSON="[]"
        [[ -n "$PROVIDER_API_KEY" ]] || \
            die "KIMI_API_KEY env var is required for PROVIDER=kimi" 1
        ;;
    nvidia)
        # nvidia/nvidia/nemotron-nano-12b-v2-vl — the only NVIDIA NIM
        # vision model verified end-to-end with the demo:
        #   • free (cost=$0 in the Gateway's built-in catalog)
        #   • supports ≥2 images (FPV + overhead map per turn)
        #   • survives the Gateway's tool-bearing agent framework
        # Models like meta/llama-3.2-*-vision-instruct cap at 1 image
        # and 400 on every demo step; minimax/kimi-thinking on NIM
        # either don't support vision or hit server-side errors.
        MODEL="${MODEL:-nvidia/nvidia/nemotron-nano-12b-v2-vl}"
        # NV_API_KEY (roboclaws convention) or NVIDIA_API_KEY (Gateway plugin default).
        PROVIDER_API_KEY="${NV_API_KEY:-${NVIDIA_API_KEY:-}}"
        PROVIDER_ENV_VAR="NVIDIA_API_KEY"
        # NVIDIA NIM OpenAI-compatible endpoint — matches the built-in
        # Gateway catalog's NVIDIA_BASE_URL
        # (/app/dist/provider-catalog-C9xZ5Sl52.js) so our override merges
        # cleanly with the implicit plugin.
        PROVIDER_BASE_URL="https://integrate.api.nvidia.com/v1"
        # Single curated entry. Keeping the list short means every model
        # the bootstrap advertises is known to work; the tests assert on
        # this invariant so accidental "let me add another" edits trip
        # the CI free-tier / multi-image checks.
        EXTRA_MODELS_JSON='[
            {"id":"nvidia/nemotron-nano-12b-v2-vl","name":"NVIDIA Nemotron Nano 12B V2 VL","input":["text","image"],"reasoning":false,"contextWindow":131072,"maxTokens":4096}
        ]'
        [[ -n "$PROVIDER_API_KEY" ]] || \
            die "NV_API_KEY (or NVIDIA_API_KEY) env var is required for PROVIDER=nvidia" 1
        ;;
    *)
        die "Unsupported PROVIDER: '$PROVIDER' (supported: kimi, nvidia)" 1
        ;;
esac

[[ -d "$SKILLS_DIR" ]] || die "Skill directory not found: $SKILLS_DIR" 2
if ! [[ "$AGENTS" =~ ^[0-9]+$ ]] || (( AGENTS < 1 || AGENTS > 8 )); then
    die "AGENTS must be an integer 1..8 (got: $AGENTS)" 1
fi
# agentId regex from /app/dist/http-utils-*.js: [a-z0-9][a-z0-9_-]{0,63}
if ! [[ "$AGENT_PREFIX" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
    die "AGENT_PREFIX must match [a-z0-9][a-z0-9_-]* (got: $AGENT_PREFIX)" 1
fi

log "image        : $IMAGE"
log "container    : $CONTAINER"
log "volume       : $VOLUME"
log "bind         : ${HOST_IP}:${PORT}"
log "agents       : $AGENTS (prefix=$AGENT_PREFIX → ${AGENT_PREFIX}0 .. ${AGENT_PREFIX}$((AGENTS-1)))"
log "provider     : $PROVIDER"
log "model        : $MODEL"
log "skill        : $SKILLS_DIR"
[[ -n "$AGENT_SOULS" ]] && log "souls        : $AGENT_SOULS (dir: $SOULS_DIR)"

# Build the list of agent ids once so the pre-seed and docker-run stages agree.
agent_ids=()
for ((i=0; i<AGENTS; i++)); do
    agent_ids+=("${AGENT_PREFIX}${i}")
done
AGENT_IDS_CSV="$(IFS=,; printf '%s' "${agent_ids[*]}")"

# ----- Parse + validate AGENT_SOULS ------------------------------------------
# Builds soul_assignments[] indexed by agent integer (0..AGENTS-1).
# Accepts two forms:
#   csv positional: "aggressive,defensive"   → agent-0=aggressive, agent-1=defensive
#   dict form:      "agent-0:aggressive,agent-2:cooperative" → sparse; unset slots = ""
# Empty AGENT_SOULS → all slots empty (no SOUL.md written → stock OpenClaw SOUL).
declare -a soul_assignments
for ((i=0; i<AGENTS; i++)); do soul_assignments[i]=""; done

if [[ -n "$AGENT_SOULS" ]]; then
    # Detect form: if any entry contains ':', it's dict form; else csv positional.
    if [[ "$AGENT_SOULS" == *:* ]]; then
        # Dict form: agent-N:soulname
        IFS=',' read -ra _dict_entries <<< "$AGENT_SOULS"
        for _entry in "${_dict_entries[@]}"; do
            _aname="${_entry%%:*}"
            _soul="${_entry#*:}"
            # Map agent name to index
            _found=0
            for ((i=0; i<AGENTS; i++)); do
                if [[ "${agent_ids[$i]}" == "$_aname" ]]; then
                    soul_assignments[$i]="$_soul"
                    _found=1
                    break
                fi
            done
            [[ $_found -eq 1 ]] || die "AGENT_SOULS dict entry '$_aname' does not match any agent (agents: $AGENT_IDS_CSV)" 1
        done
    else
        # Positional csv: count must match AGENTS
        IFS=',' read -ra _soul_csv <<< "$AGENT_SOULS"
        if [[ "${#_soul_csv[@]}" -ne "$AGENTS" ]]; then
            die "AGENT_SOULS count (${#_soul_csv[@]}) must match AGENTS ($AGENTS)" 1
        fi
        for ((i=0; i<AGENTS; i++)); do
            soul_assignments[$i]="${_soul_csv[$i]}"
        done
    fi

    # Validate each non-empty soul name against files in SOULS_DIR.
    _available_souls="$(ls "$SOULS_DIR"/*.md 2>/dev/null | xargs -n1 basename | sed 's/\.md$//' | paste -sd, - 2>/dev/null || true)"
    for ((i=0; i<AGENTS; i++)); do
        _soul="${soul_assignments[$i]}"
        [[ -z "$_soul" ]] && continue
        if [[ ! -f "$SOULS_DIR/${_soul}.md" ]]; then
            die "unknown SOUL '${_soul}'; available: ${_available_souls:-<none found in $SOULS_DIR>}" 1
        fi
    done

    # Log assignments
    for ((i=0; i<AGENTS; i++)); do
        _soul="${soul_assignments[$i]}"
        if [[ -n "$_soul" ]]; then
            log "${agent_ids[$i]} → SOUL: $_soul"
        else
            log "${agent_ids[$i]} → SOUL: (default)"
        fi
    done
fi

# ----- 1. Clean slate for the container name ------------------------------
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    log "removing existing container $CONTAINER"
    docker rm -f "$CONTAINER" >/dev/null
fi

# ----- 2. Pull image ------------------------------------------------------
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    log "pulling $IMAGE (first run only)"
    docker pull "$IMAGE" >&2 || die "docker pull failed" 2
fi

# ----- 3. Ensure config volume exists and is writable by uid 1000 --------
docker volume create "$VOLUME" >/dev/null || die "docker volume create failed" 2

# Build AGENT_SOUL_CSV: positional csv of soul names for agent-0..agent-(AGENTS-1).
# Empty slot = "" (stock SOUL). Passed into the pre-seed container as one env var.
_soul_csv_for_preseed=""
for ((i=0; i<AGENTS; i++)); do
    [[ $i -gt 0 ]] && _soul_csv_for_preseed+=","
    _soul_csv_for_preseed+="${soul_assignments[$i]}"
done

log "pre-seeding config volume + $AGENTS agent(s)"
docker run --rm --user root \
    -v "$VOLUME:/home/node/.openclaw" \
    -v "${SOULS_DIR}:/host-souls:ro" \
    -e PROVIDER_API_KEY="$PROVIDER_API_KEY" \
    -e PROVIDER_ID="$PROVIDER" \
    -e MODEL="$MODEL" \
    -e AGENT_IDS_CSV="$AGENT_IDS_CSV" \
    -e EXTRA_MODELS_JSON="$EXTRA_MODELS_JSON" \
    -e PROVIDER_BASE_URL="$PROVIDER_BASE_URL" \
    -e AGENT_SOUL_CSV="$_soul_csv_for_preseed" \
    "$IMAGE" sh -lc '
set -eu
python3 - <<PY
import json, os, shutil
agent_ids = os.environ["AGENT_IDS_CSV"].split(",")
provider_id = os.environ["PROVIDER_ID"]
provider_key = os.environ["PROVIDER_API_KEY"]
model = os.environ["MODEL"]
extra_models = json.loads(os.environ.get("EXTRA_MODELS_JSON") or "[]")
provider_base_url = os.environ.get("PROVIDER_BASE_URL", "")
agent_soul_csv = os.environ.get("AGENT_SOUL_CSV", "")
base = "/home/node/.openclaw"

# Pre-create every dir so Docker doesnt create intermediate bind-mount
# parents as root. Also covers workspace/state which the Gateway writes to
# on first boot and would fail on root-owned parent.
os.makedirs(base, exist_ok=True)
os.makedirs(os.path.join(base, "logs"), exist_ok=True)
for aid in agent_ids:
    os.makedirs(os.path.join(base, "agents", aid, "agent"), exist_ok=True)
    os.makedirs(os.path.join(base, "workspaces", aid, "skills"), exist_ok=True)
    os.makedirs(os.path.join(base, "workspaces", aid, "state"), exist_ok=True)
# Keep the legacy "main" agent around with its own workspace too — the Gateway
# insists on a default agent existing even if we never route to it.
os.makedirs(os.path.join(base, "agents", "main", "agent"), exist_ok=True)
os.makedirs(os.path.join(base, "workspace", "skills"), exist_ok=True)
os.makedirs(os.path.join(base, "workspace", "state"), exist_ok=True)

# Per-agent SOUL.md distribution.
# soul_csv is positional, one entry per agent-id (empty string = leave default).
# Unconditionally remove any stale SOUL.md first (prevents stale persona
# surviving across bootstrap re-runs when AGENT_SOULS changes).
souls_csv_entries = agent_soul_csv.split(",") if agent_soul_csv else []
for idx, aid in enumerate(agent_ids):
    soul_path = os.path.join(base, "workspaces", aid, "SOUL.md")
    # Always clean up any leftover from a previous run.
    if os.path.exists(soul_path):
        os.remove(soul_path)
    soul_name = souls_csv_entries[idx] if idx < len(souls_csv_entries) else ""
    if soul_name:
        src = f"/host-souls/{soul_name}.md"
        shutil.copyfile(src, soul_path)

# openclaw.json: gateway settings + agents.list (array of per-agent entries).
# Schema reference: /app/dist/runtime-schema-*.js:5648 — agents.list items
# have { id, workspace, agentDir, model: {primary, fallbacks?}, ... }.
agent_entries = [
    {
        "id": aid,
        "workspace": f"/home/node/.openclaw/workspaces/{aid}",
        "agentDir": f"/home/node/.openclaw/agents/{aid}/agent",
        "model": {"primary": model},
    }
    for aid in agent_ids
]
config = {
    "gateway": {
        "auth": {"mode": "token"},
        "http": {"endpoints": {"chatCompletions": {"enabled": True}}},
    },
    "agents": {
        "defaults": {"model": {"primary": model}},
        "list": agent_entries,
    },
}
# Inject extra model catalog entries so the Gateways model-catalog merger
# recognizes the models we want to use. Without this, the Gateway rejects
# models with 400 "Unknown model: <id>" because the pinned images built-in
# provider plugin catalog does not include newer NIM / OpenRouter models.
# Schema: /app/dist/models-config-*.js — cfg.models.providers.<id>.models[]
# with { id, name, input, reasoning?, contextWindow?, maxTokens? }
# "mode: merge" is the default and merges these into the implicit plugin-
# supplied entries (see /app/dist/models-config-*.js:planOpenClawModelsJson).
if extra_models:
    # The Gateway config validator requires baseUrl when a provider entry
    # is declared explicitly. We pass the same value the built-in plugin
    # uses, so the merger (mode=merge) unions our new model entries with
    # the implicit catalog without shadowing anything.
    provider_entry: dict[str, object] = {"models": extra_models}
    if provider_base_url:
        provider_entry["baseUrl"] = provider_base_url
        provider_entry["api"] = "openai-completions"
    config["models"] = {
        "mode": "merge",
        "providers": {
            provider_id: provider_entry,
        },
    }
with open(os.path.join(base, "openclaw.json"), "w", encoding="utf-8") as fh:
    json.dump(config, fh, indent=2)

# Per-agent auth-profiles.json. Schema verified against
# /app/dist/store-*.js:parseCredentialEntry in image 2026.4.14:
#   type in {"api_key", "oauth", "token"} (snake_case)
#   provider must be non-empty
#   key is the credential material
# Provider id matches the Gateway plugin id (kimi, nvidia, ...).
profile = {
    "profiles": {
        f"{provider_id}:manual": {
            "type": "api_key",
            "provider": provider_id,
            "key": provider_key,
        }
    }
}
for aid in agent_ids + ["main"]:
    path = os.path.join(base, "agents", aid, "agent", "auth-profiles.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2)
    os.chmod(path, 0o600)
PY
chown -R 1000:1000 /home/node/.openclaw
' >&2 || die "volume pre-seed failed" 2

# ----- 4. Launch the Gateway — one skill mount per agent -----------------
log "starting Gateway with $AGENTS agent workspace(s)"
skill_basename="$(basename "$SKILLS_DIR")"
mount_args=(
    -p "${HOST_IP}:${PORT}:18789"
    -v "$VOLUME:/home/node/.openclaw"
    -e OPENCLAW_AUTH_MODE=token
    # Gateway plugins read the provider key from the env var named by the plugin
    # manifest (providerAuthEnvVars); the value comes from the roboclaws-side
    # secret (KIMI_API_KEY or NV_API_KEY, depending on PROVIDER).
    -e "${PROVIDER_ENV_VAR}=${PROVIDER_API_KEY}"
)
# Optional: bump Gateway log level to DEBUG for upstream-traffic debugging.
# Set GATEWAY_DEBUG=1 when you need to see what the Gateway sends to Kimi /
# NVIDIA on a failing call.  Off by default — DEBUG is verbose.
if [[ "${GATEWAY_DEBUG:-0}" == "1" ]]; then
    mount_args+=(-e "OPENCLAW_LOG_LEVEL=debug" -e "DEBUG=*")
    log "GATEWAY_DEBUG=1 — Gateway will log at DEBUG level"
fi
for aid in "${agent_ids[@]}"; do
    mount_args+=(-v "${SKILLS_DIR}:/home/node/.openclaw/workspaces/${aid}/skills/${skill_basename}:ro")
done
docker run -d --name "$CONTAINER" "${mount_args[@]}" "$IMAGE" >/dev/null \
    || die "docker run failed" 2

# ----- 5. Wait for /readyz -----------------------------------------------
# Token is generated on first boot. Read it from the volume so we can auth the
# readyz probe instead of relying on an env-provided value the Gateway ignores.
log "waiting up to ${READY_TIMEOUT}s for Gateway readiness"
deadline=$(( $(date +%s) + READY_TIMEOUT ))
_last_tick=$(date +%s)
ready=0
token=""
while (( $(date +%s) < deadline )); do
    _now=$(date +%s)
    _elapsed=$(( _now - (deadline - READY_TIMEOUT) ))
    # Per-10s progress tick so users don't think the bootstrap hung
    if (( _now - _last_tick >= 10 )); then
        log "readyz: still waiting (${_elapsed}s/${READY_TIMEOUT}s)"
        _last_tick=$_now
    fi
    token=$(docker exec "$CONTAINER" sh -lc \
        'cat /home/node/.openclaw/openclaw.json 2>/dev/null' \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("gateway",{}).get("auth",{}).get("token",""))' \
        2>/dev/null || true)
    if [[ -n "$token" ]] && \
       curl -sf --max-time 3 \
            -H "Authorization: Bearer $token" \
            "http://${HOST_IP}:${PORT}/readyz" >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 2
done
if [[ $ready -ne 1 ]]; then
    log "Gateway failed to become ready; dumping logs:"
    docker logs --tail 50 "$CONTAINER" >&2 || true
    die "readyz timeout" 3
fi
log "Gateway ready"

# ----- 6. Verify each named agent exists in the live config -------------
log "verifying $AGENTS named agent(s) registered"
docker exec "$CONTAINER" python3 - <<PY >&2 || die "agent registration check failed" 2
import json, sys
with open("/home/node/.openclaw/openclaw.json") as fh:
    cfg = json.load(fh)
want = "$AGENT_IDS_CSV".split(",")
have = {entry.get("id") for entry in cfg.get("agents", {}).get("list", [])}
missing = [a for a in want if a not in have]
if missing:
    print(f"missing agents in openclaw.json: {missing}", file=sys.stderr)
    sys.exit(1)
print("registered:", ", ".join(sorted(have & set(want))))
PY

# ----- 7. Sanity probe: one-shot /v1/chat/completions on agent-0 --------
probe_agent="${agent_ids[0]}"
log "probing /v1/chat/completions via model=openclaw/${probe_agent} (~30s cold start)"
probe=$(curl -s --max-time 90 -X POST "http://${HOST_IP}:${PORT}/v1/chat/completions" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"openclaw/${probe_agent}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with only PONG.\"}]}" 2>&1)
probe_rc=$?
if [[ $probe_rc -ne 0 ]]; then
    log "probe failed (curl exit $probe_rc): $probe"
    docker logs --tail 20 "$CONTAINER" >&2 || true
    die "probe curl failed" 4
fi
case "$probe" in
    *'"PONG"'*|*'"Pong"'*|*'content":"'[Pp][Oo][Nn][Gg]*)
        log "probe ok — openclaw/${probe_agent} is live and skill-aware"
        ;;
    *)
        log "probe response: $probe"
        docker logs --tail 20 "$CONTAINER" >&2 || true
        die "probe failed — see container logs above" 4
        ;;
esac

# ----- 8. Personality divergence probe (when AGENT_SOULS set + distinct) ----
# Ask each agent the same strategy question; assert responses diverge.
# Skipped when: AGENT_SOULS empty, only one agent, all souls identical, or
# PERSONALITY_PROBE=0 override.
_should_probe=0
if [[ -n "$AGENT_SOULS" && "$PERSONALITY_PROBE" != "0" && "$AGENTS" -gt 1 ]]; then
    # Check if all soul assignments are identical (e.g. cooperative,cooperative)
    _all_same=1
    _first_soul="${soul_assignments[0]}"
    for ((i=1; i<AGENTS; i++)); do
        if [[ "${soul_assignments[$i]}" != "$_first_soul" ]]; then
            _all_same=0
            break
        fi
    done
    [[ $_all_same -eq 0 ]] && _should_probe=1
fi

if [[ $_should_probe -eq 1 ]]; then
    log "personality probe: asking all agents 'describe your strategy in one sentence'"
    _probe_strategy_q="In one short sentence, describe your strategy."
    declare -A _strategy_hashes
    _probe_ok=1
    for ((i=0; i<AGENTS; i++)); do
        _agent_name="${agent_ids[$i]}"
        _resp=$(curl -s --max-time 90 -X POST "http://${HOST_IP}:${PORT}/v1/chat/completions" \
            -H "Authorization: Bearer $token" \
            -H "Content-Type: application/json" \
            -d "{\"model\":\"openclaw/${_agent_name}\",\"messages\":[{\"role\":\"user\",\"content\":\"${_probe_strategy_q}\"}]}" 2>&1 || true)
        _content=$(printf '%s' "$_resp" | python3 -c \
            'import json,sys; d=json.load(sys.stdin); print((d.get("choices") or [{}])[0].get("message",{}).get("content","") or "")' \
            2>/dev/null || true)
        # Hash first 64 chars to compare distinctness
        _hash=$(printf '%s' "${_content:0:64}" | sha256sum | cut -c1-16)
        log "  ${_agent_name} (SOUL=${soul_assignments[$i]}): ${_content:0:120}"
        _strategy_hashes[$_agent_name]="$_hash"
    done
    # Check all hashes are distinct
    declare -A _seen_hashes
    for _aname in "${!_strategy_hashes[@]}"; do
        _h="${_strategy_hashes[$_aname]}"
        if [[ -n "${_seen_hashes[$_h]+x}" ]]; then
            log "personality probe FAILED — ${_aname} and ${_seen_hashes[$_h]} returned identical strategy responses"
            log "SOUL assignments: $AGENT_SOULS"
            log "Hint: SOULs may not have loaded — check that SOULS_DIR ($SOULS_DIR) is correct"
            die "agents returned identical strategy responses — SOULs may not have loaded" 5
        fi
        _seen_hashes[$_h]="$_aname"
    done
    log "personality probe ok — $AGENTS distinct strategies confirmed"
fi

# ----- 9. Emit the token (only thing on stdout) --------------------------
printf '%s\n' "$token"
