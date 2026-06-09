# Agent SDKs vs. Frameworks for the Code-Holds-the-Loop, MCP-Driven Robot Agent

> Research date: 2026-06-09
> Status: Complete. Intended as decision context for replacing the Codex-CLI subprocess driver.
> Scope: (1) OpenAI Agents SDK vs. Claude Agent SDK; (2) whether any other framework beats them for this use case.

## Key Finding

For the roboclaws "Mode 3 / code-agent-via-MCP" architecture — where a simulator drives time, **the host code must own the agent loop**, every robot MCP tool call must be written to `trace.jsonl`, episodes run long and terminate on a `done` tool, and mid-episode resilience matters — the decisive axis is **who owns the loop**, not provider/wire-protocol compatibility (already neutralized: Kimi and MiMo expose both Anthropic-style and OpenAI-Responses-style interfaces, and Responses-API models are available).

Against that axis:

- **Of the two big vendor SDKs, the OpenAI Agents SDK is the better default fit** — it is in-process (no subprocess), exposes typed per-tool lifecycle hooks (`on_tool_start`/`on_tool_end`) that map 1:1 onto `trace.jsonl` rows, and lets host code drive each `Runner.run` turn. The **Claude Agent SDK** is a strong alternative whose automatic context compaction, session resume/fork, and subagent context isolation are best-in-class, but it spawns the Claude Code CLI as a subprocess and is designed to *own* the loop — the same pattern roboclaws is leaving.
- **No mainstream framework cleanly beats either SDK on host-owned step cadence.** The genuinely strong "beyond the two SDKs" options are: a **thin DIY loop on the official MCP Python SDK + the model client(s)** (the contrarian top pick, endorsed by Anthropic's own "Building Effective Agents"), and **PydanticAI** (best off-the-shelf framework that still lets the host drive node-by-node via `agent.iter()`).
- **Neither SDK retries transient 429 / model-unavailable in a way that protects a long run by default** — the #1 current pain does not vanish automatically; resilience must be engineered regardless of choice.

This report is descriptive decision context, not a committed decision. A follow-up ADR should record whichever path is chosen.

---

## Part 1 — OpenAI Agents SDK vs. Claude Agent SDK

### 1.1 Loop ownership is the decisive axis

The OpenAI Agents SDK is a library of small in-process primitives (`Agent`, `Runner`, `function_tool`, sessions, hooks); each `Runner.run()` is one application-level turn and the host decides when to call it again. Its docs explicitly say that if you want to own the loop yourself you can drop to the Responses API directly.[^oai-sdk] The Claude Agent SDK is the inverse: it is "the infrastructure that powers Claude Code, exposed as a library," whose value proposition is that you are *not* writing the agent loop — it spawns the Claude Code CLI (`cli.js`) as a subprocess and runs the gather-context → act → verify loop for you.[^claude-loop][^promptfoo] For a simulator that drives time with host code holding the loop, the OpenAI model is the more natural fit; the Claude model requires working *with* its loop (via hooks and `max_turns`) rather than around it.

### 1.2 Tracing every robot tool call into trace.jsonl

OpenAI exposes typed lifecycle hooks — `RunHooks` (whole-run) and `AgentHooks` (per-agent) with `on_tool_start`, `on_tool_end` (receives the tool result), `on_llm_start`, `on_llm_end`, `on_handoff`, with `ToolContext` exposing `tool_call_id` — an almost exact match for "append one JSONL row per robot tool call," as in-process Python callbacks.[^oai-mcp] Claude's equivalent is `PreToolUse`/`PostToolUse`/`Stop`/`SubagentStart`/`PostToolUseFailure` hooks plus a streamed message channel; `PostToolUse` can even rewrite tool output before the model sees it — but these fire inside the CLI subprocess and are received over the stdio/JSON stream (or via OpenTelemetry).[^claude-loop]

### 1.3 Observability

OpenAI ships a built-in tracing dashboard (on by default) with custom spans and third-party integrations (AgentOps, Langfuse, LangSmith); the caveat is the data lives in OpenAI's platform and is weaker for non-OpenAI models.[^oai-sdk] The Claude Agent SDK has no structured telemetry on by default, but the bundled CLI has first-class OpenTelemetry: `CLAUDE_CODE_ENABLE_TELEMETRY=1` + an OTLP exporter yields spans per model request and per tool execution, token/cost metrics, and structured events exportable to Honeycomb/Datadog/Grafana/Langfuse.[^claude-loop] For a custom `trace.jsonl` + checker pipeline driven by host code, OpenAI's in-process hooks are the shortest path; Claude's OTel is excellent but oriented toward shipping telemetry to a backend rather than synchronous in-loop interception.

### 1.4 Context & session management

- **OpenAI** — explicit, swappable Session backends (`SQLiteSession`, `SQLAlchemySession`, `OpenAIConversationsSession`, Redis) plus `OpenAIResponsesCompactionSession` for compaction; `RunContextWrapper` for local (non-LLM) mutable state and `wrapper.usage` for token usage; `session_input_callback` / `call_model_input_filter` to trim/dedupe/reorder context per turn. Auto-compaction can be disabled and `run_compaction()` called manually.[^oai-sdk] You cannot combine a client-side Session with a server-managed `conversation_id` in the same run.
- **Claude** — automatic compaction near the context limit (summarize in place, re-read CLAUDE.md afterward), session **resume** and **fork** (fork inherits full history + reuses prompt cache), file checkpointing, and subagents with isolated context windows returning only a summary to the parent.[^claude-loop] Anthropic's own "Effective harnesses for long-running agents" found compaction alone insufficient for very long tasks, recommending an initializer + context resets with state persisted in files/git — a pattern that transfers directly to a robot episode log.[^harness]

Trade-off: OpenAI = you see and control what's in context; Claude = the harness manages it (levers: `/compact`, `max_turns`, `max_budget_usd`).

### 1.5 MCP support

Both are mature and reuse the existing robot MCP servers unchanged. OpenAI supports stdio / HTTP-SSE / Streamable HTTP (SSE deprecated upstream; prefer Streamable HTTP or stdio), with static and dynamic tool filtering and an opt-in `include_server_in_tool_names` to avoid cross-server name collisions.[^oai-mcp] Claude has the deepest MCP integration (Anthropic authored MCP): in-process "SDK MCP servers" that avoid subprocess overhead, external stdio/HTTP/SSE servers, `mcp__{server}__{tool}` naming, and Tool Search enabled by default to withhold tool definitions from context until needed (useful with many robot tools).[^claude-loop]

### 1.6 Reliability — the crux of the migration

Part of the current pain is inherent to the *CLI-subprocess* pattern: `openai/codex` issue #233 reports a 429 bubbling out and crashing the CLI process, losing work/context. The Claude Agent SDK shares that subprocess architecture (it spawns `cli.js`), so it does not magically solve the class of problem.[^claude-loop] The OpenAI Agents SDK, being in-process, gives more direct hooks, but per its own source *"By default, no automatic retries occur unless you explicitly configure `ModelSettings(retry=...)`."*[^oai-errors] Its `error_handlers` catch only `max_turns` and `model_refusal` — a raw 429/500 aborts the run unless the retry policy catches it or the call is wrapped in tenacity.[^oai-errors] The Claude SDK provides no built-in retry/turn/budget defaults; 429/529 handling is on you. Both therefore require explicitly engineering retry/resume — but OpenAI's in-process `RunState.to_json()`/resume plus opt-in retry policy give finer code-level control than driving a CLI subprocess.

### 1.7 Maturity

Both are pre-1.0 and move fast; pin exact versions. OpenAI warns it raises minor version Y for breaking changes and recommends pinning to `0.0.x`; recent breaking changes include dropping Python 3.9 and requiring `openai` v2.x.[^oai-changelog] The Claude SDK bundles the CLI and has documented sharp edges (camelCase vs snake_case option names; checking `message.subtype` rather than `is_error` to distinguish a max-turns stop from success).[^claude-py] A known Claude footgun: `allowed_tools` *pre-approves* rather than *restricts* — under `bypassPermissions` all built-in tools remain available regardless of the allowlist (SDK v0.1.9 / CLI 2.0.50).[^claude-py]

### 1.8 When each wins

- **OpenAI Agents SDK** — when host-owned step cadence, in-process tracing, and zero subprocess in the data path are paramount (this matches roboclaws today).
- **Claude Agent SDK** — when a single observation step routinely blows the context window and you'd rather inherit best-in-class automatic compaction + subagent isolation than hand-roll trimming; instrument via hooks + OTel, drive with `ClaudeSDKClient`, set `max_turns`/`max_budget_usd` from the start, and put robot tools in an in-process SDK MCP server.

---

## Part 2 — Is any other framework a better fit?

### 2.1 The hardest constraint eliminates most of the field

"Host code holds the loop" is a control-inversion requirement. Most candidate frameworks own execution: LangGraph compiles a graph executed by the Pregel runtime; Google ADK's `Runner` drives an event loop; Microsoft Agent Framework, CrewAI, and AutoGen all own orchestration. Recommending any of those "because it owns the loop better" solves the wrong problem. Two escape hatches matter: **step iteration** and **per-tool hooks**. MCP client support is now table stakes across every serious candidate, so neither "many providers" nor "has MCP" is a differentiator.[^zenml][^firecrawl]

### 2.2 Tier 1 — Strong fit

**A. Thin DIY loop on the MCP Python SDK + the model client(s) — contrarian top pick.**
The official MCP Python SDK gives `ClientSession` with `session.list_tools()`, `session.call_tool(name, args)`, and a `progress_callback` — everything needed to write the loop yourself.[^mcp-py] Loop ownership is total (`while not done and turns < max_turns:`); instrumentation is trivial because tool name/args/result are held at the call site; you own the message list (fixing the context/session pain); and resilience is explicit — on 429/unavailable, back off and retry *the current turn* rather than re-running the episode (fixing the "429 forces full re-run" pain). Anthropic's "Building Effective Agents" explicitly endorses this: the most successful implementations "weren't using complex frameworks… they were building with simple, composable patterns."[^bea] Weakness: you build/maintain multi-tool dispatch, parallel calls, streaming, schema edge cases, token accounting, and there is no built-in tracing UI. Right call precisely because the loop is custom and simple (one agent, a handful of tools, a `done` terminator).

**B. PydanticAI — best off-the-shelf framework here.**
`agent.iter()` returns an `AgentRun` you can `async for` over node-by-node, or drive manually with `.next()` to inspect/modify each node before it runs — the closest thing to "framework owns the mechanics, host owns the loop."[^pyd-agent] MCP servers are first-class `toolsets` (`MCPServerStdio`/`MCPServerStreamableHTTP`) with a `process_tool_call` hook to wrap calls.[^pyd-tools] Resilience is granular: `ModelRetry`, per-tool retry counters, `FallbackModel`, and an HTTP-level `AsyncTenacityTransport` + `wait_retry_after` that respects `Retry-After` headers — directly relevant to the 429 pain (note issue #2311: retry budget can be shared across parallel tool calls).[^pyd-retry][^pyd-issue] OpenTelemetry-native. V1 reached API stability in Sept 2025 (no breaking changes until V2, no earlier than April 2026); built by the Pydantic team whose validation library underpins the OpenAI, Anthropic, Google ADK, LangChain, LlamaIndex, and CrewAI SDKs.[^pyd-agent] Weakness: still a framework with its own graph abstraction; bare `agent.iter()` does not call node hooks (use `.next()`); no built-in checkpointing without bolting on Temporal/DBOS; Python-only.

**C. smolagents — strong if you embrace code-as-action for robot control.**
The workflow "emerges dynamically from the Python script in which the agent is run"; `CodeAgent` writes actions as executable Python (claimed ~30% fewer steps than JSON tool-calling), with `step_callbacks` after each step and `final_answer_checks`.[^zenml] `ToolCollection.from_mcp` loads MCP tools.[^smol] ~27k stars, ~1,000-line core, Apache-2.0.[^smol-stars] Weaknesses: executes arbitrary Python (needs sandboxing — the built-in executor is explicitly not a security boundary); no persistent state; weaker resilience than PydanticAI.

### 2.3 Tier 2 — Situational

- **Strands Agents (AWS)** — model-driven loop, native MCP, lifecycle hooks, `agent.cancel()`, session managers, OTel out of the box; reached 1.0 July 2025, used in production by Amazon Q Developer / AWS Glue.[^strands-gh][^strands-session] But the loop is Strands', not yours, and durability is weak — "conversation restore is not execution resume," and only 429s auto-retry (per Diagrid, a vendor of a competing durable-execution product).[^diagrid] Wins when deploying on AWS/Bedrock/AgentCore.
- **LangGraph** — the most mature durable-execution engine (checkpointers, time-travel, human-in-the-loop, LangSmith), GA 1.0 Oct 2025, used by Uber/JPMorgan/LinkedIn/Klarna.[^langgraph] But "you define the graph, the runtime executes it" is the opposite of host-owns-the-loop, and it is self-described as very low-level. Wins if requirements shift to durable, resumable, branching multi-agent orchestration with audit trails.
- **LlamaIndex Workflows** — event-driven `@step` control with MCP, but center of gravity is RAG/retrieval, not environment-acting agents.[^firecrawl] Situational.
- **Vercel AI SDK (TS)** — `ToolLoopAgent` documents explicit loop control (`stopWhen`, `prepareStep`, `isLoopFinished()`, a done-tool pattern) and Core functions for full loop ownership; a Tier-1 contender if the repo were TS-first, a fallback at ~90% Python.[^vercel]

### 2.4 Tier 3 — Poor fit

CrewAI (role-based, opaque, heaviest token footprint, MCP "emerging"); Microsoft Agent Framework (owns execution, heaviest on .NET/Azure, new for production Python); AutoGen/AG2 (AutoGen in maintenance mode; conversation-centric); Google ADK (`Runner` owns the loop, GCP-centric); and Agno/Atomic Agents/DSPy/Letta/Inngest/Mastra/Restate/BAML (none uniquely beat Tier 1 on these criteria). `mcp-agent` is worth a look if pattern scaffolding on MCP is desired.[^alex][^qubit]

### 2.5 How the alternatives map to the four current pains

| Pain | Root cause | Fix in Tier-1 options |
|------|-----------|----------------------|
| 429 forces full re-run | vendor SDKs run the loop opaquely | DIY/PydanticAI retry the *current turn* with `Retry-After`-aware backoff + persisted progress |
| context/session not controllable | CLI black box / hand-rolled continuation prompts | DIY = own the message list; PydanticAI `agent.iter()` exposes node/message history |
| tool misrouting needs prompt workarounds | provider-dependent tool protocol | own dispatch (DIY) or `process_tool_call`/interceptors validate routing in code |
| shelling out to Codex CLI subprocess | subprocess boundary + fragile session mgmt | every Tier-1 option is an in-process library |

---

## Recommendations (staged, conditional — not a committed decision)

1. **Spike both seams first (1–2 days).** A fake MCP server exposing `observe/navigate/pick/place/done`, driven ~20 steps, one `trace.jsonl` row per tool call: one version on a thin DIY loop, one on PydanticAI `agent.iter()`. Confirm the host can own step cadence + termination cleanly and that per-tool-call tracing lands in the existing trace/checker pipeline.
2. **Default to the thin DIY loop on the MCP Python SDK** for the current single-agent, MCP-driven, step-traceable loop. Implement `trace.jsonl` per tool call, per-turn `asyncio.timeout`, `max_turns`, `done` termination, current-turn `Retry-After`-aware backoff, and message-list + turn-index checkpointing for resume.
3. **Graduate to PydanticAI** when DIY boilerplate (typed tools, structured outputs, fallback models, OTel spans, parallel calls) costs more than the framework's abstraction tax.
4. **Add durable execution (PydanticAI + Temporal/DBOS, or LangGraph checkpointers) only if** crash-resume across process restarts becomes a hard requirement.
5. **Among the two big SDKs specifically**, prefer the **OpenAI Agents SDK** for host-owned loop control; keep the **Claude Agent SDK** as an instrumented fallback if context-window pressure makes its automatic compaction + subagent isolation worth ceding loop ownership.

### Thresholds that change the recommendation
- Single observation step routinely overflows the context window → Claude Agent SDK's compaction/subagents become worth it.
- More than ~3–4 cooperating agents, branching/handoff, or audit-grade replay → LangGraph (or Microsoft Agent Framework if Azure-bound).
- Hard crash-resume SLA → Temporal/DBOS under PydanticAI, or LangGraph checkpointers.
- Model-written code desirable for robot control AND sandboxable → smolagents `CodeAgent`.
- AWS/Bedrock standardization → Strands.

## Caveats
- Both vendor SDKs and PydanticAI/Strands are pre-1.0 or recently 1.0; version numbers, MCP maturity, and stability commitments are as of mid-2026 and should be re-verified before committing.
- Vendor adoption claims (PydanticAI/Strands production users, smolagents' "~30% fewer steps," LangGraph monthly-download figures that vary by source) are testimonials/self-reported, not independent benchmarks.
- The Strands durability critique comes from Diagrid, a competing durable-execution vendor — directionally consistent with Strands' own docs but read with that lens.
- The DIY-loop recommendation is deliberately contrarian and assumes the loop stays simple (one agent, modest tool count, clear terminator). If that breaks, maintenance burden flips the calculus toward PydanticAI or LangGraph.

---

## References

[^oai-sdk]: OpenAI Agents SDK — overview & sessions. https://openai.github.io/openai-agents-python/
[^oai-mcp]: Model context protocol (MCP) — OpenAI Agents SDK. https://openai.github.io/openai-agents-python/mcp/
[^oai-errors]: Run Error Handlers — OpenAI Agents SDK. https://openai.github.io/openai-agents-python/ref/run_error_handlers/
[^oai-changelog]: Release process / changelog — OpenAI Agents SDK. https://openai.github.io/openai-agents-python/release/
[^claude-loop]: How the agent loop works — Claude Code / Agent SDK Docs. https://code.claude.com/docs/en/agent-sdk/agent-loop
[^claude-py]: anthropics/claude-agent-sdk-python. https://github.com/anthropics/claude-agent-sdk-python
[^promptfoo]: Claude Agent SDK — Promptfoo. https://www.promptfoo.dev/docs/providers/claude-agent-sdk/
[^harness]: Effective context engineering / harnesses for long-running agents — Anthropic Engineering. https://www.anthropic.com/engineering
[^bea]: Building Effective Agents — Anthropic. https://www.anthropic.com/research/building-effective-agents
[^mcp-py]: A Quick Introduction to Model Context Protocol (MCP) in Python (modelcontextprotocol/python-sdk usage). https://medium.com/@adev94/a-quick-introduction-to-model-context-protocol-mcp-in-python-bee6d36334ec
[^pyd-agent]: Agents — Pydantic AI Docs (agent.iter / iter nodes / V1 stability). https://ai.pydantic.dev/agents/
[^pyd-tools]: Advanced Tool Features — Pydantic AI Docs (process_tool_call, MCP toolsets). https://ai.pydantic.dev/tools-advanced/
[^pyd-retry]: HTTP Request Retries — Pydantic AI Docs (AsyncTenacityTransport, wait_retry_after). https://ai.pydantic.dev/retries/
[^pyd-issue]: Max tool retry is inconsistent with parallel tool calling — pydantic/pydantic-ai #2311. https://github.com/pydantic/pydantic-ai/issues/2311
[^zenml]: Smolagents vs LangGraph — ZenML Blog. https://www.zenml.io/blog/smolagents-vs-langgraph
[^smol]: huggingface/smolagents (ToolCollection.from_mcp, CodeAgent). https://github.com/huggingface/smolagents
[^smol-stars]: smolagents project stats. https://awesome.ecosyste.ms/projects/github.com/huggingface/smolagents
[^strands-gh]: strands-agents/sdk-python. https://github.com/strands-agents/sdk-python
[^strands-session]: Session Management — Strands Agents Docs. https://strandsagents.com/latest/documentation/docs/user-guide/concepts/
[^diagrid]: Still Not Durable: How Microsoft Agent Framework and Strands Agents Repeat the Same Mistakes — Diagrid Blog. https://www.diagrid.io/blog/still-not-durable-how-microsoft-agent-framework-and-strands-agents-repeat-the-same-mistake
[^langgraph]: LangGraph 1.0 is now generally available — LangChain Changelog. https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available
[^firecrawl]: The best open source frameworks for building AI agents in 2026 — Firecrawl. https://www.firecrawl.dev/blog/best-open-source-agent-frameworks
[^vercel]: Agents: Loop Control — Vercel AI SDK Docs. https://ai-sdk.dev/docs/agents/loop-control
[^alex]: AI Agent Frameworks Compared (2026 Developer Guide) — Alex Cloudstar. https://www.alexcloudstar.com/blog/ai-agent-frameworks-comparison-2026/
[^qubit]: 2026 AI Agent Framework Showdown — QubitTool. https://qubittool.com/blog/ai-agent-framework-comparison-2026
