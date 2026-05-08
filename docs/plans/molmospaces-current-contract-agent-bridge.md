# MolmoSpaces Current-Contract Agent Bridge

**Status:** Draft
**Created:** 2026-05-08
**Source:** `grill-with-docs` discussion, `CONTEXT.md`, ADR-0004
**Workflow intent:** Insert this bridge before implementing the ADR-0003
real-world-style cleanup harness.

## Problem

The current MolmoSpaces cleanup demo is not agent-driven. It runs a deterministic
Python loop over `MolmoCleanupToolContract`, and the `public_heuristic` planner
builds the cleanup plan before executing semantic substeps.

That is useful for proving MolmoSpaces/MuJoCo state mutation and visual reports,
but it does not prove that a coding agent or OpenClaw can use the Molmo cleanup
tools correctly.

Before making the cleanup scenario more realistic under ADR-0003, we should
first prove the current curated contract is usable by external agents. This
isolates MCP/tool/skill/Gateway problems from the later public/private realism
changes.

## Goal

Build the **MolmoSpaces Current-Contract Agent Bridge**: a transitional harness
that exposes the existing Molmo cleanup contract over FastMCP and hardens the
agent instructions through direct coding-agent dogfood before running OpenClaw.

This phase may keep current-contract shortcuts, including global
`scene_objects`, but every artifact must label the run as
`contract=current_contract` and must not claim to satisfy ADR-0003.

## Architectural Decision

Use a new Molmo-specific MCP server, not the AI2-THOR navigation server.

See ADR-0004:
[`docs/adr/0004-use-separate-mcp-servers-for-ai2thor-and-molmo-cleanup.md`](../adr/0004-use-separate-mcp-servers-for-ai2thor-and-molmo-cleanup.md).

Expected shape:

- `roboclaws/molmo_cleanup/mcp_server.py`
- class: `MolmoCleanupMCPServer`
- factory: `make_molmo_cleanup_mcp(...)`
- wraps `MolmoCleanupToolContract`
- owns FastMCP tool registration, trace writing, `done_event`, startup/close
  lifecycle, and snapshot/report hooks where needed
- reuses small MCP binding/readiness patterns from the AI2-THOR server where
  useful, but does not subclass it

## Tool Contract

Expose the current Molmo cleanup tools over MCP:

- `observe`
- `scene_objects`
- `navigate_to_object`
- `navigate_to_receptacle`
- `pick`
- `open_receptacle`
- `place`
- `place_inside`
- `object_done`
- `done`

The current `scene_objects` behavior is allowed in this bridge because the goal
is MCP/skill viability, not scenario realism. The real-world-style harness will
later retire or restrict this global movable-object view.

Tool descriptions should be hardened for external agents, especially:

- call `observe` first;
- use `scene_objects` to find current public objects and receptacles;
- choose the object/receptacle sequence externally;
- use semantic substeps per object:
  `navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? ->
  place/place_inside -> object_done`;
- use `open_receptacle` before `place_inside` for fridge-like targets;
- call `done` only after all intended objects have been completed;
- do not treat deterministic `public_heuristic` as the policy.

## Molmo Cleanup Skill

Add:

```text
skills/molmo-cleanup/SKILL.md
```

The skill should be compact and explicit like the hardened AI2-THOR navigator
skill:

- exact MCP tool names;
- expected loop;
- object completion expectations;
- fridge/open/place-inside rule;
- artifact/report expectations;
- stop/done rule;
- no private scoring truth or heuristic replay.

The skill and tool descriptions must be refined together through dogfood runs.
First-pass instructions are expected to be weak.

## Direct Coding-Agent Dogfood

Use Codex as the primary dogfood agent.

Run up to five direct coding-agent attempts against the Molmo MCP server. Early
stop is allowed after a **Clean Agent Cleanup Run**.

A clean run requires:

- `cleanup_status=success`;
- 5/5 current curated targets restored;
- external agent chose the tool sequence;
- intended semantic substeps are present;
- every completed object has `object_done`;
- fridge/food case uses `open_receptacle` before `place_inside`;
- no stale-reference errors;
- no premature `done`;
- no private-manifest/scripted-reference policy path;
- complete `trace.jsonl`, `run_result.json`, and `report.html`;
- no manual operator intervention beyond launching the agent.

Each dogfood attempt should produce a small log entry:

- predicted weakness;
- actual failure/success behavior;
- MCP tool-description or skill change made;
- resulting status.

After Codex hardening, run one Claude Code compatibility smoke against the same
server and skill to check the contract is not Codex-specific.

## OpenClaw Gate

After direct MCP hardening:

- run OpenClaw Gateway against the same Molmo MCP server;
- require MCP tool-use viability and a useful trace;
- full 5/5 cleanup success is a stretch goal, not a blocker.

Minimum viable OpenClaw evidence:

- Gateway discovers Molmo MCP tools;
- OpenClaw calls `observe`;
- OpenClaw calls `scene_objects`;
- OpenClaw attempts at least one semantic cleanup substep;
- run produces a trace with enough detail to diagnose behavior;
- run terminates cleanly or records an attributable failure.

## Run Results And Reports

`run_result.json` should distinguish deterministic and agent-driven paths:

- `contract=current_contract`;
- `policy=public_heuristic | codex_agent | claude_code_agent | openclaw_agent`;
- `agent_driven=true|false`;
- `policy_uses_private_truth=false`;
- `cleanup_status`;
- `score`;
- `semantic_loop_variant`;
- `tool_event_counts`;
- `mcp_server=molmo_cleanup`;
- `primitive_provenance` summary;
- artifacts paths.

Reports should clearly label:

- current-contract shortcuts;
- whether the run was heuristic or agent-driven;
- tool sequence;
- semantic substep completeness;
- errors and stale references;
- final score.

## Recipes

Preferred names:

- `just harness::molmo-agent-bridge`
- `just verify::molmo-agent-bridge`

The verify recipe should run focused contract/server/skill tests plus a cheap
non-agent smoke where possible. Real dogfood/OpenClaw runs remain local
operator gates.

## Acceptance Criteria

- New `MolmoCleanupMCPServer` wraps `MolmoCleanupToolContract` and exposes the
  current cleanup tools over FastMCP.
- Direct MCP server entrypoint prints setup instructions for Codex and Claude
  Code.
- `skills/molmo-cleanup/SKILL.md` exists and is used by dogfood prompts.
- Codex dogfood loop runs up to five attempts, with early stop after a clean
  run.
- Each dogfood attempt records a log entry and any MCP/skill hardening change.
- Claude Code compatibility smoke runs after Codex hardening.
- OpenClaw viability run produces useful tool traces.
- Reports and `run_result.json` label `contract=current_contract`.
- Docs explicitly state this bridge does not satisfy ADR-0003.

## Non-Goals

- Do not implement the ADR-0003 real-world-style cleanup contract here.
- Do not remove global `scene_objects` in this phase.
- Do not hide current curated target shape in this phase.
- Do not require OpenClaw 5/5 success as a hard gate.
- Do not claim planner-backed robot navigation or manipulation.
- Do not introduce a generic cross-backend MCP server abstraction.

## Follow-Up

After this bridge:

1. Implement the MolmoSpaces Real-World-Style Cleanup Harness.
2. Replace global `scene_objects` with robot-local visible-object perception.
3. Re-run Codex/Claude/OpenClaw against the stricter ADR-0003 contract.
4. Compare agent behavior between current-contract and real-world-style runs.
