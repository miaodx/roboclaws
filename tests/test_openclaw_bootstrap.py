"""Static checks on ``scripts/openclaw-bootstrap.sh`` — the contract this file
locks in is:

1. Every NVIDIA / OpenRouter model the bootstrap advertises as "free"
   actually carries ``cost.input == 0`` and ``cost.output == 0`` in the
   pinned Gateway image's built-in provider catalog (so a user running
   with the defaults can't accidentally rack up a bill on first try).

2. Each supported ``PROVIDER=…`` branch has a corresponding auth-profile
   entry with a non-empty ``EXTRA_MODELS_JSON`` array (except Kimi where
   the built-in catalog already has the single model we use) and a
   provider id that matches a Gateway plugin manifest at
   ``/app/dist/extensions/<id>/openclaw.plugin.json``.

The tests read the live ``scripts/openclaw-bootstrap.sh`` plus the pinned
image contents; if Docker + the image aren't available the affected
tests ``skip`` (so CI's ``lint-and-mock`` job passes without pulling the
Gateway image).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = ROOT / "scripts" / "openclaw-bootstrap.sh"
IMAGE_DEFAULT = "ghcr.io/openclaw/openclaw:2026.4.14"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _gateway_image_available(image: str = IMAGE_DEFAULT) -> bool:
    if not _docker_available():
        return False
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return result.returncode == 0


def _read_bootstrap() -> str:
    return BOOTSTRAP.read_text(encoding="utf-8")


def _extract_extra_models_for(provider: str) -> list[dict]:
    """Return the parsed ``EXTRA_MODELS_JSON`` block for a given PROVIDER case.

    Parses the bash script's heredoc-quoted JSON literal. Kept deliberately
    strict: if the script's structure changes, the test fails loudly rather
    than silently returning ``[]``.
    """
    text = _read_bootstrap()
    # Match the case branch, then capture the EXTRA_MODELS_JSON='[...]' literal.
    # Bash single-quote can't contain single quotes, so the regex is simple.
    pattern = (
        rf"^\s*{re.escape(provider)}\)\s*$"  # case label
        r"(?:(?!^\s*[a-z]+\)\s*$).)*?"  # up to next case label
        r"EXTRA_MODELS_JSON='(\[.*?\])'"
    )
    m = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    if not m:
        # Kimi branch uses "[]" double-quoted instead of single.
        pattern_alt = (
            rf"^\s*{re.escape(provider)}\)\s*$"
            r"(?:(?!^\s*[a-z]+\)\s*$).)*?"
            r'EXTRA_MODELS_JSON="(\[.*?\])"'
        )
        m = re.search(pattern_alt, text, flags=re.MULTILINE | re.DOTALL)
        if not m:
            raise AssertionError(
                f"bootstrap.sh does not declare EXTRA_MODELS_JSON for PROVIDER={provider}"
            )
    return json.loads(m.group(1))


def _extract_provider_base_urls() -> dict[str, str]:
    """Return ``{ provider_id: base_url }`` for every explicit PROVIDER_BASE_URL
    declaration in the bootstrap. Kimi's empty string is included too (it
    means "use the built-in catalog's baseUrl").
    """
    text = _read_bootstrap()
    out: dict[str, str] = {}
    for provider_match in re.finditer(
        r"^\s*([a-z][a-z0-9]*)\)\s*$"
        r"(?:(?!^\s*[a-z]+\)\s*$).)*?"
        r'PROVIDER_BASE_URL="([^"]*)"',
        text,
        flags=re.MULTILINE | re.DOTALL,
    ):
        out[provider_match.group(1)] = provider_match.group(2)
    return out


def _read_gateway_catalog(path_pattern: str) -> str:
    """Read a dist file matching ``path_pattern`` (glob-like) from the pinned
    Gateway image.
    """
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            IMAGE_DEFAULT,
            "sh",
            "-lc",
            f"cat {path_pattern}",
        ],
        capture_output=True,
        timeout=30,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(f"could not read {path_pattern} from {IMAGE_DEFAULT}: {result.stderr}")
    return result.stdout


# ---------------------------------------------------------------------------
# Free-tier claims
# ---------------------------------------------------------------------------


def test_nvidia_curated_to_single_multi_image_model() -> None:
    """The bootstrap's NVIDIA branch is deliberately curated to the one
    model we've verified end-to-end:

      - free (cost=$0 in the NIM catalog — checked by a separate test)
      - multi-image (demo sends FPV + overhead = 2 images per turn)
      - survives the Gateway's tool-bearing agent framework

    We assert the curated list stays minimal; if you want to broaden it,
    rerun the live probe and extend both the bootstrap and this test.
    """
    models = _extract_extra_models_for("nvidia")
    assert len(models) == 1, (
        "nvidia branch is curated to one verified model. To add another, "
        "probe it live against /v1/chat/completions with a 2-image payload "
        "+ tools, and update this test's expected count once verified."
    )
    model = models[0]
    assert model["id"] == "nvidia/nemotron-nano-12b-v2-vl", (
        f"unexpected nvidia model {model['id']!r}; curated entry is "
        "'nvidia/nemotron-nano-12b-v2-vl'. See docs/openclaw-local.md."
    )
    assert "image" in model.get("input", []), (
        "nvidia/nemotron-nano-12b-v2-vl must flag image input."
    )


def test_kimi_branch_has_empty_extra_models() -> None:
    """Kimi's EXTRA_MODELS_JSON stays empty because the kimi branch now uses
    the PROVIDER_ENTRY_JSON / mode=replace path (custom ``anthropic_kimi``
    provider) rather than merging extra models into the built-in plugin's
    catalog.  See :func:`test_kimi_branch_registers_anthropic_kimi_provider`
    for the assertions on the custom entry itself.
    """
    models = _extract_extra_models_for("kimi")
    assert models == [], (
        "kimi branch should keep EXTRA_MODELS_JSON='[]' — its catalog entry "
        "now lives in PROVIDER_ENTRY_JSON with mode=replace."
    )


def _extract_provider_entry_for(provider: str) -> dict | None:
    """Parse the ``PROVIDER_ENTRY_JSON`` heredoc-quoted JSON literal for a
    given PROVIDER case.  Returns ``None`` when the branch is using the
    legacy EXTRA_MODELS_JSON / mode=merge path (e.g. nvidia).
    """
    text = _read_bootstrap()
    pattern = (
        rf"^\s*{re.escape(provider)}\)\s*$"
        r"(?:(?!^\s*[a-z_]+\)\s*$).)*?"
        r"PROVIDER_ENTRY_JSON=\$\(cat <<JSON\n(.*?)\nJSON\n"
    )
    m = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    if not m:
        return None
    return json.loads(m.group(1))


def test_kimi_branch_registers_anthropic_kimi_provider() -> None:
    """Kimi's bootstrap branch must register a custom ``anthropic_kimi``
    provider (via PROVIDER_ENTRY_JSON / mode=replace) rather than relying
    on the built-in ``kimi-coding`` plugin, which drives
    ``api.kimi.com/coding/`` in a reasoning-heavy mode that serialises
    every multi-image turn at 60-120s and regularly trips the Gateway's
    idle watchdog (observed 2026-04-20).

    The custom entry pins the request shape we want — anthropic-messages
    at the same host, no forced reasoning, canonical
    ``User-Agent: Claude-Code/1.0``.  Kimi's direct-probe path in
    ``KimiCodingProvider`` uses the same host at a different surface for
    the same reason (see comments in ``roboclaws/core/vlm.py``).
    """
    entry = _extract_provider_entry_for("kimi")
    assert entry is not None, (
        "kimi branch no longer declares PROVIDER_ENTRY_JSON. Revert to the "
        "anthropic_kimi custom registration or this path silently falls back "
        "to the slow built-in kimi-coding plugin."
    )
    assert entry["baseUrl"] == "https://api.kimi.com/coding/"
    assert entry["api"] == "anthropic-messages"
    assert entry["auth"] == "api-key"
    # apiKey is interpolated from $PROVIDER_API_KEY by the heredoc at bootstrap
    # time; the literal string before interpolation is the env var reference.
    assert "${PROVIDER_API_KEY}" in entry["apiKey"] or entry["apiKey"].startswith("sk-"), (
        "apiKey must be injected from KIMI_API_KEY (heredoc interpolation)."
    )
    headers = entry.get("headers", {})
    assert headers.get("User-Agent") == "Claude-Code/1.0", (
        "Kimi-For-Coding gate requires a recognised coding-agent User-Agent."
    )
    assert headers.get("anthropic-version"), (
        "anthropic-messages calls require an ``anthropic-version`` header."
    )
    models = entry.get("models", [])
    assert len(models) == 1, "curated to a single verified model"
    m = models[0]
    assert m["id"] == "k2.6-code-preview"
    assert "image" in m.get("input", []), "demo sends 2 images per turn"
    assert m.get("reasoning") is False, (
        "reasoning:true on api.kimi.com/coding/ is exactly what we're routing "
        "around — flipping this to true would re-introduce the slow path."
    )


def test_bootstrap_uses_mode_replace_when_custom_entry_present() -> None:
    """When PROVIDER_ENTRY_JSON is supplied, the Python pre-seed block must
    register the custom provider with ``mode: replace`` — not merge.  The
    merge path would union our entry with the built-in plugin catalog and
    the Gateway could still route via the slow built-in kimi model id
    during request-shaping, defeating the fix.
    """
    text = _read_bootstrap()
    assert re.search(
        r'if provider_entry_json:.*?"mode":\s*"replace"',
        text,
        flags=re.DOTALL,
    ), "bootstrap pre-seed must write mode=replace when PROVIDER_ENTRY_JSON is set"


def test_only_two_providers_supported() -> None:
    """The bootstrap's ``case "$PROVIDER"`` statement should list exactly
    the two curated providers: kimi and nvidia. If this test fails because
    a third provider was added, make sure you've also:

      1. Added EXTRA_MODELS_JSON entries verified live
      2. Added a PROVIDER_BASE_URL matching the Gateway plugin catalog
      3. Added a parametrize row in test_provider_env_var_matches_plugin_manifest
      4. Updated docs/openclaw-local.md
    """
    text = _read_bootstrap()
    case_labels = re.findall(r"^\s*([a-z][a-z0-9]*)\)\s*$", text, flags=re.MULTILINE)
    # Filter to labels inside the provider case block (between
    # `case "$PROVIDER" in` and the closing `esac`).
    m = re.search(r'case "\$PROVIDER" in(.*?)\nesac', text, flags=re.DOTALL)
    assert m, "could not find the PROVIDER case block"
    block = m.group(1)
    provider_labels = re.findall(r"^\s*([a-z][a-z0-9]*)\)\s*$", block, flags=re.MULTILINE)
    assert set(provider_labels) == {"kimi", "nvidia"}, (
        f"bootstrap.sh PROVIDER case declares {sorted(set(provider_labels))!r}; "
        "expected exactly {'kimi', 'nvidia'} per curated contract."
    )
    # Quieten the unused variable from earlier refactor.
    del case_labels


def test_provider_base_urls_match_image_catalog() -> None:
    """The ``PROVIDER_BASE_URL`` values hard-coded in the bootstrap must
    match the base URL the Gateway's built-in provider plugin catalog
    publishes — otherwise our ``models.providers.<id>`` override spawns a
    second Gateway-side catalog entry with a mismatched base URL and
    routes requests to the wrong host.
    """
    if not _gateway_image_available():
        pytest.skip(f"{IMAGE_DEFAULT} not pulled locally; skip catalog cross-check")

    declared = _extract_provider_base_urls()
    # Only nvidia injects an override — kimi intentionally has no override so
    # the built-in catalog is authoritative.
    assert declared.get("nvidia"), "bootstrap.sh missing PROVIDER_BASE_URL for nvidia branch"

    catalog_text = _read_gateway_catalog("/app/dist/provider-catalog-C9xZ5Sl52.js")
    match = re.search(r'BASE_URL\s*=\s*"([^"]+)"', catalog_text)
    assert match, "could not find BASE_URL in the NVIDIA provider catalog"
    implicit = match.group(1)
    assert declared["nvidia"] == implicit, (
        f"nvidia: bootstrap declares {declared['nvidia']!r} but the pinned "
        f"image's built-in catalog uses {implicit!r}. Update one to match."
    )


def test_nvidia_extra_models_cost_free_in_image_catalog() -> None:
    """Any NVIDIA model id that also exists in the pinned image's built-in
    catalog must carry ``cost.input = 0`` / ``cost.output = 0`` (the NIM
    free tier). If NVIDIA's catalog ever lists one of our entries as paid,
    this test flags it before users get billed.

    Models present only in NVIDIA's live API (not in the pinned image's
    built-in catalog) are exempted: all NIM models are free-tier for
    individual developer accounts regardless of whether the pinned
    Gateway image happens to know about them.
    """
    if not _gateway_image_available():
        pytest.skip(f"{IMAGE_DEFAULT} not pulled locally; skip catalog cross-check")

    catalog_text = _read_gateway_catalog("/app/dist/provider-catalog-C9xZ5Sl52.js")
    # Find every cost block in the catalog — they all point at
    # NVIDIA_DEFAULT_COST which we require to be {input:0, output:0,...}.
    default_cost_match = re.search(r"NVIDIA_DEFAULT_COST\s*=\s*\{([^}]+)\}", catalog_text)
    assert default_cost_match, (
        "built-in NVIDIA catalog no longer exposes NVIDIA_DEFAULT_COST; "
        "the pinned image has changed shape — verify free-tier claim manually."
    )
    cost_block = default_cost_match.group(1)
    assert re.search(r"input\s*:\s*0\b", cost_block), (
        f"NVIDIA_DEFAULT_COST.input is no longer 0 in the pinned image — cost block: {cost_block!r}"
    )
    assert re.search(r"output\s*:\s*0\b", cost_block), (
        "NVIDIA_DEFAULT_COST.output is no longer 0 in the pinned image — "
        f"cost block: {cost_block!r}"
    )

    # Every entry in the built-in catalog references NVIDIA_DEFAULT_COST —
    # no paid entry has snuck in for NVIDIA on this image.
    cost_refs = re.findall(r"cost:\s*([A-Z_][A-Z0-9_]*)", catalog_text)
    assert cost_refs, "catalog has no cost references — unexpected shape"
    non_default = [c for c in cost_refs if c != "NVIDIA_DEFAULT_COST"]
    assert not non_default, (
        f"NVIDIA catalog has non-free cost refs {non_default!r} — "
        "not all advertised models are free on this image."
    )


def test_reasoning_entries_have_enough_token_budget() -> None:
    """Any bootstrap entry marked ``reasoning: true`` triggers a hidden
    chain-of-thought pass. Without a generous ``max_tokens`` budget the
    answer comes back with ``content: null`` (verified on
    ``nvidia/nemotron-nano-12b-v2-vl:free`` via OpenRouter during Phase 2.2
    exploration). If any curated entry ever flips to ``reasoning: true``,
    ``_DEFAULT_MAX_TOKENS`` in the bridge must stay ≥ 1024.
    """
    reasoning_ids: set[str] = set()
    for provider in ("kimi", "nvidia"):
        for model in _extract_extra_models_for(provider):
            if model.get("reasoning"):
                reasoning_ids.add(f"{provider}:{model['id']}")
    if not reasoning_ids:
        pytest.skip("no reasoning-flagged curated models right now")
    bridge_text = (ROOT / "roboclaws" / "openclaw" / "bridge.py").read_text(encoding="utf-8")
    m = re.search(r"_DEFAULT_MAX_TOKENS\s*=\s*(\d+)", bridge_text)
    assert m, "bridge.py missing _DEFAULT_MAX_TOKENS constant"
    assert int(m.group(1)) >= 1024, (
        "bridge.py _DEFAULT_MAX_TOKENS too small for reasoning model entries "
        f"{sorted(reasoning_ids)!r} — tested minimum is 1024."
    )


# ---------------------------------------------------------------------------
# Plugin id ↔ auth env var sanity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "provider_id, expected_auth_env",
    [
        ("kimi", "KIMI_API_KEY"),
        ("nvidia", "NVIDIA_API_KEY"),
    ],
)
def test_provider_env_var_matches_plugin_manifest(provider_id: str, expected_auth_env: str) -> None:
    """The ``PROVIDER_ENV_VAR`` the bootstrap passes into the container must
    match the Gateway plugin's declared ``providerAuthEnvVars[<id>]`` or
    the plugin won't pick up the api key and the probe fails with 401/503.
    """
    text = _read_bootstrap()
    pattern = (
        rf"^\s*{re.escape(provider_id)}\)\s*$"
        r"(?:(?!^\s*[a-z]+\)\s*$).)*?"
        r'PROVIDER_ENV_VAR="([^"]+)"'
    )
    m = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert m, f"bootstrap.sh missing PROVIDER_ENV_VAR for {provider_id}"
    assert m.group(1) == expected_auth_env, (
        f"{provider_id}: bootstrap sets PROVIDER_ENV_VAR={m.group(1)!r} but "
        f"the Gateway plugin expects {expected_auth_env!r}."
    )

    if not _gateway_image_available():
        pytest.skip(f"{IMAGE_DEFAULT} not pulled locally; skip plugin-manifest check")
    # A provider id may be served by a differently-named plugin directory
    # (e.g. the `kimi` provider is declared by the `kimi-coding` plugin).
    # Search every manifest under /app/dist/extensions for one that claims
    # the provider id.
    manifests_listing = _read_gateway_catalog("/app/dist/extensions/*/openclaw.plugin.json")
    # `cat file1 file2 …` concatenates — we need per-file reads. Use find + loop.
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            IMAGE_DEFAULT,
            "sh",
            "-lc",
            "find /app/dist/extensions -name openclaw.plugin.json -print",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    declared_env_vars: list[str] = []
    for path in result.stdout.strip().split("\n"):
        if not path.strip():
            continue
        manifest = json.loads(_read_gateway_catalog(path.strip()))
        providers = manifest.get("providers") or []
        if provider_id not in providers:
            continue
        envs = (manifest.get("providerAuthEnvVars") or {}).get(provider_id, [])
        declared_env_vars.extend(envs)
    assert declared_env_vars, (
        f"no /app/dist/extensions/*/openclaw.plugin.json declares provider "
        f"{provider_id!r} in its `providers` list — bootstrap needs updating."
    )
    assert expected_auth_env in declared_env_vars, (
        f"{provider_id}: plugin manifests declare {declared_env_vars!r} for "
        f"this provider; bootstrap uses {expected_auth_env!r} which isn't "
        "in the accepted list."
    )
    # Silence the unused binding from earlier (readability).
    del manifests_listing


# ---------------------------------------------------------------------------
# SOUL injection: static contract checks (no Docker required)
# ---------------------------------------------------------------------------


def test_bootstrap_declares_agent_souls_env_var() -> None:
    """AGENT_SOULS env var is declared and consumed by the bootstrap."""
    text = _read_bootstrap()
    assert "AGENT_SOULS" in text, "bootstrap.sh does not reference AGENT_SOULS"


def test_bootstrap_passes_soul_csv_to_preseed() -> None:
    """AGENT_SOUL_CSV is exported so the pre-seed container can copy SOUL files."""
    text = _read_bootstrap()
    assert "AGENT_SOUL_CSV" in text, (
        "bootstrap.sh does not pass AGENT_SOUL_CSV to the pre-seed container; "
        "per-agent SOUL injection will silently do nothing"
    )


def test_bootstrap_binds_souls_dir_readonly() -> None:
    """SOULS_DIR is bind-mounted read-only into the pre-seed container."""
    text = _read_bootstrap()
    assert "/host-souls:ro" in text, (
        "bootstrap.sh does not bind-mount SOULS_DIR as /host-souls:ro in the "
        "pre-seed container; SOUL files cannot be copied into agent workspaces"
    )


def test_bootstrap_declares_exit_5_for_personality_collision() -> None:
    """Bootstrap exits with code 5 when the divergence probe detects identical responses.

    The bootstrap uses ``die "..." 5`` (die helper calls ``exit ${2:-1}``),
    not a bare ``exit 5``.
    """
    text = _read_bootstrap()
    assert "die(" in text or "die " in text, "bootstrap.sh missing 'die' helper"
    # die() is called with exit-code 5 for the personality-collision case.
    assert re.search(r"die\b.*\b5\b", text), (
        "bootstrap.sh does not call die with exit-code 5; personality collision in "
        "the divergence probe should fail with exit 5 so the caller detects SOUL load failures"
    )


def test_bootstrap_personality_probe_is_skippable() -> None:
    """PERSONALITY_PROBE=0 must be supported to skip the probe for identical-soul runs."""
    text = _read_bootstrap()
    assert "PERSONALITY_PROBE" in text, (
        "bootstrap.sh does not reference PERSONALITY_PROBE; there is no way to "
        "skip the probe for identical-soul runs (e.g. cooperative,cooperative)"
    )
