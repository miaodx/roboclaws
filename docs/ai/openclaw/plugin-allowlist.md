# OpenClaw plugin allow-list: why we pin it

Captures *why* `openclaw.json` carries an explicit `plugins.allow` block and
*how* to extend it safely. Companion to `docs/ai/openclaw/tool-profiles.md` — both
docs exist to keep image bumps from silently breaking startup.

Audience: anyone bumping the `OPENCLAW_IMAGE_DEFAULT` pin, adding a new
provider, or debugging a "why does the gateway take 60s to boot" report.

## TL;DR

The OpenClaw Gateway image ships ~100 extensions in
`/app/dist/extensions/`. Every plugin whose manifest declares
`"enabledByDefault": true` auto-loads on first start, and several lazy-load
heavy npm tarballs (`playwright-core`, `@homebridge/ciao`, `pdfjs-dist`,
`node-edge-tts`, `@mozilla/readability`, …) the first time the Control UI
enumerates capabilities.

We pin a strict allow-list to short-circuit that:

```json
"plugins": {
  "allow": ["acpx", "memory-core", "nvidia", "kimi", "xiaomi"]
}
```

Anything not on this list is hard-rejected by the gateway
(`/app/dist/bundled-runtime-deps-*.js`), so a future image that
auto-enables a new plugin (Slack, webhook, voice-call, whatever) is filtered
silently — no surprise install delay, no surprise outbound traffic.

Source of truth: [`scripts/openclaw/openclaw_plugin_allowlist.py`](../../../scripts/openclaw/openclaw_plugin_allowlist.py).
The supported seeder is `scripts/openclaw/openclaw-bootstrap.sh`; its
regression test pins the rendered config against this list.

## Live-probe before/after (image `2026.4.25-beta.11`)

| | Before allow-list | After allow-list |
|---|---|---|
| Plugins loaded at gateway-ready | 7 (`acpx, bonjour, browser, device-pair, memory-core, phone-control, talk-voice`) | 2 (`acpx, memory-core`) |
| Gateway-ready time | 37.2s | 27.0s |
| Lazy installs after first WS call | `document-extract`, `microsoft`, `web-readability` (~25s) | none |
| First-run npm tarballs installed | playwright-core, ciao, pdfjs, edge-tts, readability, linkedom, … | only `acpx@0.6.1` |

## Adding a plugin

1. Look up the **manifest id**, not the directory name. They often differ:

   ```bash
   docker run --rm --entrypoint sh ghcr.io/openclaw/openclaw:<TAG> \
     -lc 'cat /app/dist/extensions/<dirname>/openclaw.plugin.json' \
     | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
   ```

   Real example: directory `extensions/kimi-coding/` declares `"id": "kimi"`.
   Adding `"kimi-coding"` to the allow-list will trigger a
   `plugin not found: kimi-coding (stale config entry ignored)` warning at
   gateway startup, and the actual Kimi plugin will be filtered out.

2. Add the **id** to `scripts/openclaw/openclaw_plugin_allowlist.py` with a one-line
   doc-comment explaining *why* it's needed (which provider, which mode,
   which contract). Removing an entry later requires a probe; adding one
   should be cheap to justify.

3. Run the regression test:

   ```bash
   ./scripts/dev/run_pytest_standalone.sh \
     tests/contract/openclaw/test_openclaw_bootstrap.py -x -q
   ```

4. Live-probe by running `just chat::run` off the work network and
   watching for `plugin not found:` warnings near the top of the gateway
   log. The "ready (N plugins: …; …s)" line confirms what actually loaded.

## When to widen the list

You only need a plugin in the allow-list when something the gateway
actually consults references it:

- **Provider plugins** (`nvidia`, `kimi`, `xiaomi`, `moonshot`, `openai`,
  `anthropic`, `google`, …) — needed when `PROVIDER=<id>` is set AND the
  `models` config block uses `mode: merge` (so the plugin's implicit
  catalog is unioned in). The custom-mode path (`mode: replace` with
  `PROVIDER_ENTRY_JSON`) bypasses the plugin entirely; we still keep the
  matching plugin in the allow-list defensively in case a downstream code
  path consults the catalog merger.
- **Channel plugins** (`webchat`, `slack`, `discord`, `imessage`,
  `telegram`, `signal`, …) — needed only if the agent should listen on
  that channel. We don't use any (the Control UI's webchat is built into
  the gateway core, not a plugin).
- **Tool / contract plugins** (`memory-core`, `image-generation-core`,
  `speech-core`, `media-understanding-core`, …) — needed when the agent
  uses the corresponding tool surface. We keep `memory-core` because the
  agent's memory contract resolves through it even when
  `compaction.memoryFlush` is disabled.

When in doubt, ask: "if this plugin disappears, what fails?" If the answer
is "nothing in the demo path," leave it out.

## When to narrow the list

Same question, inverted. If a plugin is in the list and you can prove
nothing in the chat / appliance / coding-agent demos uses it, drop it and
re-probe. The list is meant to converge to a minimum, not grow.

## Image bump checklist

When bumping `OPENCLAW_IMAGE_DEFAULT`:

1. Run `just chat::run` off the work network and skim the first 60s of the
   gateway log for:
   - `plugin not found: <id>` — a manifest id renamed; update the list.
   - `plugins-disabled` / `disabled-in-config` — a new gateway-internal
     code path now consults a plugin we filter; investigate, then either
     add the id to `ALLOWED` or document why we keep it filtered.
   - `staging bundled runtime deps` for any plugin we don't recognize —
     means a new `enabledByDefault: true` slipped past the allow-list
     filter (shouldn't happen with strict allow-list, but worth a sanity
     check).
2. Confirm `gateway] ready (N plugins: …)` lists exactly what `ALLOWED`
   says, minus any provider plugins not yet activated.
3. Re-run the regression tests; they'll re-pin the rendered config
   against the source-of-truth list.

## Why allow-list, not deny-list

Deny-list (`plugins.deny: [...]`) was the obvious first move but trades
stability-on-upgrade for ease-of-discovery: every image bump risks
silently auto-enabling a new plugin we didn't list, and we'd only notice
when its npm install lands in the boot log. Allow-list flips it: the next
auto-enabled plugin is filtered immediately, the breakage on legitimate
new dependencies is loud and immediate, and the list stays a deliberate
artifact rather than a chase.

For a kitchen-sink third-party image like OpenClaw, that's the right
default.
