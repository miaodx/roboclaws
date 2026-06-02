# Bring Brain to Robots: How Hard Can It Be? — GPT-5.5 Outline

> Draft checkpoint for PR #122. This file is intentionally added as a separate variant instead of replacing the existing outline.

## Title

**Bring Brain to Robots: How Hard Can It Be?**

## Subtitle

**Why coding agents may be the simplest baseline for robot intelligence**

**为什么 coding agent 可能是机器人智能最简单的起点**

## Positioning

This is not a normal project feature announcement. It is a builder essay using Roboclaws as a case study for a method:

> To bring brain to robots, start from coding-agent baseline, keep behavior in skills, keep robot capabilities bounded through MCP, and verify every run through traces, maps, reports, and explicit backend evidence.

Roboclaws is the proof surface, not merely the object being introduced.

## Core thesis

Large models make robot control look easy. The hard part is not making a robot move once. The hard part is making a robot complete open-ended tasks, preserve experience, recover from failure, migrate across backends, and remain auditable.

Roboclaws' current answer is:

```text
code-agent first
skills first
MCP bounded
harness verified
```

Expanded:

- **code-agent first**: treat Claude Code / Codex-style coding agents as the default near-term baseline for robot intelligence development.
- **skills first**: keep task strategy in reusable, editable, reviewable skills.
- **MCP bounded**: expose only stable robot capability boundaries through MCP tools.
- **harness verified**: make runs reviewable through trace, map, report, score, provenance, and public/private evidence boundaries.

## Two English punchlines to preserve

> **Don’t build a robot brain from scratch until you have beaten a coding agent with tools.**

Use after explaining why coding agents are not just development helpers, but a practical baseline for robot-intelligence loops.

> **OpenClaw gave us the shape. Coding agents gave us the loop.**

Use at the transition from OpenClaw to coding-agent-native development. This keeps OpenClaw as part of the answer rather than a discarded path.

## Definition of brain

In this essay, **brain** should not mean a single model, framework, SDK, UI, or robot policy.

Brain means a maintainable skill system:

- skill carries task strategy;
- MCP carries the public robot capability boundary;
- runtime map carries world state;
- trace/report carries feedback and audit evidence;
- backend variant carries concrete execution details;
- coding agent and human review keep the loop improving.

Suggested sentence:

> Brain is not one bigger model. Brain is a skill system that can run, fail, leave evidence, be edited, and run again.

## Section structure

### 0. How Hard Can It Be?

Start from the Top Gear feeling: with large models, controlling a robot looks like a weekend demo. Camera in, action API out, MCP in the middle.

Punchline: making it move is not the hard part; making it complete open-ended tasks and improve over time is the hard part.

### 1. Making the robot move is not hard

Use VLM direct control as the first stage. It proves the minimal loop: model sees image/state, emits actions, robot moves.

But it is not enough because strategy lives in prompt templates, Python loops, one-off rules, and manual tuning.

### 2. Why we needed a harness

Robot tasks are loops, not single model calls:

```text
understand goal -> choose strategy -> call tools -> observe -> record evidence -> judge success/failure -> improve skill -> reuse next time
```

Harness is not peripheral engineering. It is part of the intelligence system because it controls what the agent sees, what it can call, how failure is recorded, and where experience goes.

### 3. OpenClaw gave us the shape

OpenClaw was the natural initial choice because it already had high-level harness ingredients: Skills, SOUL, MCP, UI, daemon, and user-facing assistant shape.

Frame OpenClaw positively:

- It showed that robots should not expose only low-level actions.
- It gave a high-level user-interaction and deployment shape.
- It remains useful as a channel for UI, voice, daemon, and assistant-facing experiences.

Transition:

> OpenClaw gave us the shape. Coding agents gave us the loop.

### 4. Coding agents gave us the loop

Coding agents can:

- read repo files;
- read SKILL.md;
- call MCP tools;
- run tasks;
- inspect trace.jsonl;
- inspect reports;
- edit skills;
- rerun tasks;
- preserve changes as diffs.

This makes them a natural robotics R&D harness. They are not only code writers; they are loop runners.

Use the manifesto sentence:

> Don’t build a robot brain from scratch until you have beaten a coding agent with tools.

Clarify: this is not saying coding agents are the final product form. It says they are the first baseline to beat.

### 5. Skills first

Open-ended task strategy belongs in skills, not opaque MCP tools or backend code.

Do not turn `clean the room` into one opaque `clean_room()` tool. Put strategy into a skill that can be read, edited, tested, reviewed, and reused.

Layering:

```text
open-ended goal
  -> runnable task
  -> agent skill
  -> capability profile
  -> MCP tools
  -> backend variant
  -> artifacts and reports
```

### 6. MCP bounded

MCP should expose bounded robot capability tools, such as observe, move, navigate, pick, place, open, close, and done.

Privileged simulator helpers may be useful for demos and debugging, but they must be labeled honestly and not treated as real robot capabilities.

Key sentence:

> The larger the tool, the faster the demo; the cleaner the tool boundary, the more transferable the intelligence.

### 7. Harness verified

Robots are hard to fool. They either reached the goal or did not. They either observed evidence or did not.

Every serious run should produce reviewable artifacts:

- trace;
- frames;
- map;
- agent view;
- runtime state;
- score;
- failure reason;
- report.html.

Minimal map and Runtime Metric Map belong here: they show that robot intelligence includes world-state construction, not just action selection.

### 8. Backend variants prove the abstraction

Backend support should not become the main narrative. Use it as evidence that the abstraction can migrate.

- AI2-THOR: early control, navigation, photo task, and multi-agent substrate.
- MolmoSpaces/MuJoCo: household cleanup and runtime-map path.
- Isaac Lab: backend/report parity and stricter visual/provenance evidence.
- Agibot G2 / ROS2/Nav2: real-robot backend boundary, operator gates, navigation/perception pilot, physical manipulation still blocked until proven.

Claim boundary matters: do not overclaim hardware or manipulation proof.

### 9. OpenClaw, Agent SDK, voice, and UI can come back

Coding-agent-first is the R&D loop, not necessarily the end-user interface.

Once skills are verified, they can be served through OpenClaw, voice UI, a custom app, Anthropic/OpenAI Agent SDK, or a robot-specific runtime.

### 10. Multi-agent is a later amplifier

Mention briefly. Roboclaws started with multi-agent motivations, but multi-agent should not carry this article. If one robot's skill/tool/map/report boundary is unclear, multi-agent only amplifies confusion.

### 11. This is not only robotics

The same pattern may apply to other domains that need open-ended tasks, tools, evidence, feedback loops, and reusable skills.

If a domain-specific agent framework cannot beat coding agent + tools + reports, start by making the domain legible to coding agents.

### 12. Closing answer

How hard can it be?

- Moving once: not hard.
- Open-ended tasks: hard.
- Continuous improvement: harder.
- Backend migration with honest evidence: harder still.

But it becomes tractable with the right cut:

```text
code-agent first
skills first
MCP bounded
harness verified
```

## Follow-up TODOs

- Add screenshots, traces, report excerpts, and map visuals.
- Add concrete run evidence and Git history examples.
- Tighten WeChat prose style.
- Decide how much of PR #92's photo-task story to reuse.
- Add a backend matrix figure.
- Add a minimal-map / Runtime Metric Map figure.
- Add references only after the prose direction is stable.
