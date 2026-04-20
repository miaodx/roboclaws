# OpenClaw Gateway — internals notes for maintainers

Pointers into the pinned Gateway image (`ghcr.io/openclaw/openclaw:2026.4.14`)
that were useful when building Phase 2.1 and that future phases (2.2, 2.5)
will want on hand. Keeps you from re-spelunking `/app/dist/` every time.

> Scope: this file is for contributors touching the
> `roboclaws/openclaw/` bridge or `scripts/openclaw-bootstrap.sh`. End users
> should reach for `docs/openclaw-local.md` instead.

## How the Gateway loads config + models

- **Startup config** — `/home/node/.openclaw/openclaw.json`. The bootstrap
  seeds this before the first container start. The Gateway will rewrite it
  (add a generated auth token, seed `controlUi.allowedOrigins`, etc.) on
  first boot, backing up to `openclaw.json.bak`.
- **Models catalog** — built at startup by `planOpenClawModelsJson` in
  `/app/dist/models-config-B-YHRI3g.js`. It merges:
  - the *implicit* per-plugin catalog (e.g. `buildNvidiaProvider()` in
    `/app/dist/provider-catalog-C9xZ5Sl52.js`)
  - the *explicit* override from `cfg.models.providers.<id>` in
    `openclaw.json` (mode defaults to `merge`)
  If you add a model ID that isn't in the implicit catalog, it **must** go in
  the override, with matching `baseUrl` + `api`. Otherwise the Gateway
  logs `Error: Unknown model: <id>` + `model_not_found` and `/v1/chat/completions`
  surfaces a failover error.

## Provider plugin manifests

- `/app/dist/extensions/<plugin-id>/openclaw.plugin.json` declares:
  - `providers: [<provider-id>, ...]` — note plugin-id ≠ provider-id. The
    `kimi-coding` plugin serves both `kimi` and `kimi-coding` providers.
  - `providerAuthEnvVars.<provider-id>: [<ENV_VAR>, ...]` — the list of env
    vars the Gateway picks up as the provider's API key.
  - `contracts.mediaUnderstandingProviders` — whether this plugin can be
    chosen for vision-understanding fallback when the primary model is text-only.
- Two plugins serve the providers roboclaws uses today:
  - `extensions/kimi-coding/openclaw.plugin.json` → provider `kimi` →
    env vars `KIMI_API_KEY` | `KIMICODE_API_KEY`. Base URL
    `https://api.kimi.com/coding/`, API surface `anthropic-messages`.
  - `extensions/nvidia/openclaw.plugin.json` → provider `nvidia` → env var
    `NVIDIA_API_KEY`. Base URL `https://integrate.api.nvidia.com/v1`, API
    surface `openai-completions`.

## Named-agent routing

`POST /v1/chat/completions` with `model="openclaw/<agentId>"`:

- Parser: `/app/dist/http-utils-*.js:resolveAgentIdFromModel` — splits on the
  first `/` after `openclaw`. `agentId` must match
  `[a-z0-9][a-z0-9_-]{0,63}`.
- Missing / unregistered agentId → 4xx at the chat endpoint.
- Each registered agent has:
  - a workspace at `/home/node/.openclaw/workspaces/<agentId>/`
  - an agent dir at `/home/node/.openclaw/agents/<agentId>/agent/` with its
    own `auth-profiles.json`
  - its own `model.primary` in `openclaw.json` → `agents.list[]`

## Per-agent workspace contents (populated on first boot)

```
/home/node/.openclaw/workspaces/<agentId>/
├── AGENTS.md       # Gateway-provided system prompt
├── BOOTSTRAP.md
├── HEARTBEAT.md
├── IDENTITY.md
├── SOUL.md         # ← persona slot — Phase 2.2 writes here
├── TOOLS.md
├── USER.md
├── skills/         # host-side bind mount to skills/ai2thor-navigator/
└── state/          # per-agent runtime state (MEMORY lives here)
```

Phase 2.1 seeds all of these with defaults. Phase 2.2 replaces `SOUL.md`
per agent. Phase 2.5 will likely care about `state/MEMORY.md` persistence
across game turns.

## Auth profile shape

`/home/node/.openclaw/agents/<agentId>/agent/auth-profiles.json`:

```json
{
  "profiles": {
    "<provider>:manual": {
      "type": "api_key",
      "provider": "<provider>",
      "key": "<api-key>"
    }
  }
}
```

Schema validator: `/app/dist/store-*.js:parseCredentialEntry`. `type` must
be one of `api_key | oauth | token` (snake_case). `provider` must match
an id declared in some plugin's `providers` list.

## Internal "webchat" channel gotcha

`/app/dist/channel-config-helpers-TKYu6OEn.js:INTERNAL_MESSAGE_CHANNEL = "webchat"`.
The OpenAI HTTP endpoint sets `defaultMessageChannel: "webchat"` for every
request, but `isKnownChannel` in `channel-selection-*.js` rejects `webchat`
for *tool dispatch*. Models that return plain text in
`choices[0].message.content` work fine. Models aggressive enough to always
call the `message` tool (`{action: send, channel: webchat, ...}`) dead-
lock the agent turn — tool dispatch errors, framework retries, timeout.

Practical rule: when adding a new model to the curated list, probe the
actual `/v1/chat/completions` path with a plain "reply PONG" prompt; if
the model returns a tool call instead of text content, it won't survive
under the Gateway's agent framework in its default config.

## Useful spelunking commands

```bash
# Dump a dist file
docker run --rm ghcr.io/openclaw/openclaw:2026.4.14 sh -lc \
  'cat /app/dist/<file>.js' | head -200

# Find a symbol
docker run --rm ghcr.io/openclaw/openclaw:2026.4.14 sh -lc \
  'grep -rnE "<pattern>" /app/dist/ 2>/dev/null' | head -20

# Live-inspect a running Gateway's openclaw.json (auth token lives here)
docker exec openclaw-gateway sh -lc 'cat /home/node/.openclaw/openclaw.json'

# Check what the Gateway materialized per-agent
docker exec openclaw-gateway sh -lc \
  'ls -la /home/node/.openclaw/workspaces/agent-0/'
```

The `/app/dist/` tree is one giant bundle of minified JS modules; `grep` is
the fastest way in. Search for symbols (function names, string literals)
rather than filenames — the file names are content-hashed and change
between image versions.
