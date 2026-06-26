# OpenClaw tool profiles: what changed across image bumps

Captures behavioral changes to the `agents.list[*].tools.profile` field across
OpenClaw Gateway image versions — the kind of thing that doesn't show up in any
release notes but silently breaks our agent's tool surface.

Audience: anyone bumping the `OPENCLAW_IMAGE_DEFAULT` pin or debugging "why does
my agent only see `session_status`."

## TL;DR

The bump from `2026.4.14` → `2026.4.25-beta.11` (commit `3b10d34`) silently
gated MCP-discovered tools behind a new `bundle-mcp` policy ID. The `minimal`
profile does NOT include this gate. Without `tools.alsoAllow: ["bundle-mcp"]`
on each agent, every `roboclaws__*` tool returns "Tool not found" and the agent
gives up with `capabilities=none`. Our bootstrap script now splices the gate
back in — see `scripts/openclaw/openclaw-bootstrap.sh`.

## The diff

Both snippets below are extracted live from `/app/dist/tool-policy-*.js` inside
each image (the hash suffix in the filename rotates per build; grep by basename).

### 2026.4.14 — what worked
```js
const CORE_TOOL_PROFILES = {
    minimal:   { allow: listCoreToolIdsForProfile("minimal") },
    coding:    { allow: listCoreToolIdsForProfile("coding") },
    messaging: { allow: listCoreToolIdsForProfile("messaging") },
    full:      {},
};
```
MCP-discovered tools (the `<server>__<tool>` namespaced ones — for us,
`roboclaws__observe`, `roboclaws__act`, `roboclaws__done`, ...) were exposed
through a separate, ungated path. No profile had to opt-in.

### 2026.4.25-beta.11 — what broke us
```js
const CORE_TOOL_PROFILES = {
    minimal:   { allow: listCoreToolIdsForProfile("minimal") },                          // unchanged
    coding:    { allow: [...listCoreToolIdsForProfile("coding"),    "bundle-mcp"] },     // ← added
    messaging: { allow: [...listCoreToolIdsForProfile("messaging"), "bundle-mcp"] },     // ← added
    full:      {},
};
```
MCP-tool exposure is now consolidated under the `bundle-mcp` policy ID. Only
`coding` and `messaging` get it for free. `minimal` looks unchanged but is
materially different in effect: MCP tools are no longer reachable from it.

## Symptom we observed

With our shipping config (`agents.list[*].tools.profile = "minimal"`,
`mcp.servers.roboclaws.transport = "streamable-http"`, MCP server live on
`host.docker.internal:18788`):

- Gateway boot log lists 7 plugins, none MCP-related:
  `[gateway] ready (7 plugins: acpx, bonjour, browser, device-pair, memory-core, phone-control, talk-voice; 5.8s)`
- The MCP server is alive and reachable (`curl host.docker.internal:18788/mcp`
  from inside the container returns a proper JSON-RPC response).
- The agent's effective tool surface = `{ session_status }`.
- Every `roboclaws__*` invocation returns `Tool <name> not found`.
- The agent reports `capabilities=none` and refuses the user's request.

## Our fix

Per-agent `alsoAllow: ["bundle-mcp"]` sibling-key on the `tools` block:

```python
# scripts/openclaw/openclaw-bootstrap.sh — Python heredoc that writes openclaw.json
"tools": {"profile": tool_profile, "alsoAllow": ["bundle-mcp"]},
```

The `alsoAllow` field is read by `mergeAlsoAllowPolicy` in
`/app/dist/tool-policy-*.js`:
```js
function mergeAlsoAllowPolicy(policy, alsoAllow) {
    if (!policy?.allow || !Array.isArray(alsoAllow) || alsoAllow.length === 0) return policy;
    return {
        ...policy,
        allow: Array.from(new Set([...policy.allow, ...alsoAllow])),
    };
}
```
The set-union semantics mean `alsoAllow` only ever ADDS to the profile's
allow-list — it cannot grant tools the profile didn't already cover unless they
go through the corresponding policy gate (which `bundle-mcp` does for MCP).

## Why we didn't just switch to `coding`

The `coding` profile broadens the agent's core surface — bash, file I/O, etc. —
beyond what the `minimal` profile was designed to enforce for our nav agents.
Keep `minimal` + the surgical `alsoAllow` splice unless an image-bump probe
shows `bundle-mcp` moved into `minimal` directly or an accepted OpenClaw plan
chooses the broader `coding` profile.

## Re-validation when bumping the image

```bash
# 1. Snapshot the new profile table
docker run --rm --entrypoint sh "$NEW_IMAGE" -c \
    "grep -A6 'CORE_TOOL_PROFILES' /app/dist/tool-policy-*.js"

# 2. Decision tree:
#    - `minimal` now lists `bundle-mcp` directly → drop alsoAllow.
#    - Policy ID renamed (`bundle-mcp` → something else) → update alsoAllow value.
#      Cross-reference: grep for the new ID in /app/dist/embedded-pi-mcp-*.js
#      and /app/dist/bundle-mcp-*.js to confirm it gates MCP exposure.
#    - Profiles unchanged → no action; existing alsoAllow keeps working.

# 3. Confirm end-to-end after bumping
just chat::run                           # in one terminal
just chat::tail                          # in another, send a tool-using message
# Look for `→ toolCall roboclaws__observe ...` in the tail output. If you only
# see `→ toolCall session_status`, the splice is wrong.
```

## Source-of-truth files inside the gateway image

Hash suffixes on these filenames rotate every image build — grep by basename.

| File | What it does |
|---|---|
| `/app/dist/tool-policy-*.js` | `CORE_TOOL_PROFILES`, `mergeAlsoAllowPolicy` — the authoritative profile definitions and merge logic |
| `/app/dist/embedded-pi-mcp-*.js` | `loadEmbeddedPiMcpConfig`, `loadMergedBundleMcpConfig` — reads `cfg.mcp.servers` from openclaw.json |
| `/app/dist/bundle-mcp-*.js` | `loadEnabledBundleConfig` — gated on `cfg.plugins.enabled`, but defaults to `true` when no `plugins` block exists |
| `/app/dist/pi-bundle-mcp-runtime-*.js` | `loadSessionMcpConfig`, `createSessionMcpRuntime` — per-session MCP server lifecycle |
| `/app/dist/pi-bundle-mcp-tools-*.js` | Tool name namespacing (`<server>__<tool>` + reserved-name avoidance) |

## Related

- `scripts/openclaw/openclaw-bootstrap.sh` — where the `alsoAllow` splice lives
- `docs/human/openclaw/gateway-internals.md` — broader Gateway image internals
- `docs/human/openclaw/local.md` — local-dev recipe + live-probed model matrix
