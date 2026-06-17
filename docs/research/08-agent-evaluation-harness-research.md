# Agent Evaluation Harness Research

Date: 2026-06-14

This research note captures the first breadth pass over public agent evaluation
practice and keeps a place for deeper follow-up. It is not yet an
implementation plan for Roboclaws; it is the source packet that should feed one.

## Research Question

Roboclaws wants development to be eval-driven instead of relying on broad
implementation effort plus partial tests. The question is:

- What are current public best practices for evaluating agent systems?
- What are OpenAI, Anthropic, Cursor, and related labs doing publicly?
- Which parts map cleanly to a household robotics repo with MCP tools,
  simulated or robot-backed environments, private scorer truth, and HTML
  reports?

## Initial Conclusion

Agent evaluation practice has converged around a product-local eval system, not
one public leaderboard:

```text
eval sample
  -> environment reset
  -> agent trial
  -> trace and artifacts
  -> deterministic and optional model/human graders
  -> aggregate metrics
  -> failure replay and regression samples
```

Public benchmarks are useful for calibration and vocabulary, but product
development is driven by internal suites that match the product's real task
distribution.

For Roboclaws, this suggests two layers:

- `agent-validation-matrix` continues to answer "which gates should this
  diff/plan run?"
- a new repo-native eval layer should answer "is household-agent capability
  improving across versioned task suites?"

## Sources Surveyed So Far

### OpenAI

OpenAI's public agent-eval guidance is trace-first. It presents agent evals as a
combination of traces, graders, datasets, and eval runs. The relevant trace
surface includes model calls, tool calls, handoffs, guardrails, and custom
events. Their skill-eval guidance frames a skill eval as a captured run plus
trace/artifacts that are checked and scored.

Useful takeaways:

- Start from traces before trying to judge aggregate quality.
- Make graders explicit and reusable.
- Treat skill or workflow changes as eval targets, not just model targets.
- Preserve enough artifact detail to debug why a run passed or failed.

Important platform note: OpenAI's legacy Evals platform is being retired, with
existing evals read-only on 2026-10-31 and dashboard/API shutdown on
2026-11-30 according to OpenAI deprecation docs. Roboclaws should borrow the
dataset/grader/eval-run pattern, not bind core infrastructure to that platform.

Initial sources:

- OpenAI agent evals:
  https://developers.openai.com/api/docs/guides/agent-evals
- OpenAI skill evals:
  https://developers.openai.com/blog/eval-skills
- OpenAI deprecations:
  https://developers.openai.com/api/docs/deprecations
- OpenAI Agents SDK tracing:
  https://openai.github.io/openai-agents-python/tracing/

### Anthropic

Anthropic's public writing is one of the clearest high-level frameworks for
agent evals. Their vocabulary distinguishes task, trial, grader,
transcript/trace, outcome, evaluation harness, agent harness, and evaluation
suite. A key point is that outcome should usually be the final environment
state, not the agent's claim that it completed the job.

They also emphasize infrastructure noise in agentic coding evals: hardware,
resource limits, time limits, parallelism, network behavior, and runtime setup
can change the measured result. This is directly relevant to Roboclaws because
world/backend/provider/profile/network/GPU state all affect run quality and
latency.

Useful takeaways:

- Separate agent harness from evaluation harness.
- Use code-based graders where possible; use model or human graders for cases
  that deterministic checks cannot capture.
- Treat resource budget and environment configuration as part of the eval
  identity.
- Maintain both capability evals and regression evals.

Initial sources:

- Demystifying evals for AI agents:
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Infrastructure noise in agentic coding evals:
  https://www.anthropic.com/engineering/infrastructure-noise

### Cursor

Cursor's public work is the closest product-team reference. CursorBench is built
from real Cursor engineering sessions and evaluates ambiguous multi-file tasks.
Cursor discusses correctness, code quality, efficiency, and interaction
behavior rather than only final pass/fail. Their agent-harness writing also
tracks product metrics such as latency, token efficiency, tool call count, cache
hit rate, Keep Rate, user follow-up feedback, and per-tool/per-model error
baselines.

Useful takeaways:

- Public benchmarks are insufficient; product teams need internal benchmarks
  taken from real usage.
- Online and offline evals should correct each other's blind spots.
- The agent harness itself is part of the product and must be evaluated.
- Interaction behavior and efficiency are first-class quality dimensions.

Initial sources:

- CursorBench:
  https://cursor.com/blog/cursorbench
- CursorBench 3.1:
  https://cursor.com/cursorbench
- Continually improving our agent harness:
  https://cursor.com/blog/continually-improving-agent-harness
- Composer:
  https://cursor.com/blog/composer

### Eval And Observability Frameworks

LangSmith splits complex agent eval into final response, trajectory, and
single-step evaluation. This maps naturally to Roboclaws:

- final response -> completion claim and final run result;
- trajectory -> MCP tool calls and state transitions;
- single-step -> one observe, navigate, pick, place, map, or done decision.

Braintrust emphasizes golden datasets, snapshots of production or staging
dependencies, tool-call and parameter accuracy, online evals, and turning real
traces into future eval cases.

Inspect AI is an important open-source reference because its core abstractions
are dataset, solver, scorer, tools, agents, and sandbox. Its public docs also
cover agents and MCP-style tool usage. This looks like a strong conceptual
match even if Roboclaws does not adopt it as a dependency.

Initial sources:

- LangSmith complex agent eval:
  https://docs.langchain.com/langsmith/evaluate-complex-agent
- Braintrust agent best practices:
  https://www.braintrust.dev/docs/best-practices/agents
- Braintrust evaluation docs:
  https://www.braintrust.dev/docs/evaluate
- Inspect AI:
  https://inspect.aisi.org.uk/
- Inspect tutorial:
  https://inspect.aisi.org.uk/tutorial.html
- Inspect agents:
  https://inspect.aisi.org.uk/agents.html

### Public Benchmarks And Repos

Coding-agent benchmarks:

- SWE-bench uses real GitHub issues, repository checkouts, patches, and tests.
  The harness and Dockerized reproducibility are more important to Roboclaws
  than the coding domain itself.
- SWE-bench Verified is a human-filtered subset, useful as a reminder that
  public benchmark items need quality control.
- AutoGenBench and OpenHands benchmark infrastructure are useful references for
  repeatable agent execution and reporting.

Tool and user-interaction benchmarks:

- tau-bench is highly relevant. It uses simulated users, domain APIs, policy
  guidelines, final database state, annotated goal state, and `pass^k` for
  multi-trial reliability.
- AgentDojo focuses on tool-using agents under untrusted data and prompt
  injection. It is relevant to Roboclaws private-truth separation and future
  perception/tool-output trust boundaries.

Web and computer-use benchmarks:

- OSWorld, WebArena, WorkArena, and BrowserGym share an important shape:
  resettable environments, task configs, execution-based scoring, and
  trajectory evidence.

Embodied and robotics benchmarks:

- BEHAVIOR-1K and RoboCasa are the closest robotics references. They emphasize
  household tasks, object state, resettable simulation, goal predicates, and
  progress or completion metrics.

Initial sources:

- SWE-bench:
  https://www.swebench.com/SWE-bench/
- SWE-bench Verified:
  https://www.swebench.com/verified.html
- SWE-bench harness:
  https://www.swebench.com/SWE-bench/reference/harness/
- AutoGenBench:
  https://microsoft.github.io/autogen/0.2/blog/2024/01/25/AutoGenBench/
- OpenHands benchmarks:
  https://github.com/OpenHands/benchmarks
- tau-bench:
  https://arxiv.org/abs/2406.12045
- tau-bench repo:
  https://github.com/sierra-research/tau-bench
- AgentDojo:
  https://github.com/ethz-spylab/agentdojo
- AgentDojo paper:
  https://arxiv.org/html/2406.13352v3
- OSWorld:
  https://os-world.github.io/
- WebArena:
  https://github.com/web-arena-x/webarena
- WorkArena:
  https://github.com/ServiceNow/WorkArena
- BrowserGym:
  https://github.com/ServiceNow/BrowserGym
- BEHAVIOR-1K:
  https://github.com/StanfordVL/BEHAVIOR-1K
- BEHAVIOR-1K paper:
  https://arxiv.org/html/2403.09227v1
- RoboCasa:
  https://github.com/robocasa/robocasa
- RoboCasa paper:
  https://arxiv.org/html/2406.02523v1

## Roboclaws Fit From Breadth Pass

Roboclaws already has several strong ingredients:

- public/private evaluation truth separation;
- `trace.jsonl`, `agent_view.json`, `run_result.json`, model metrics, runtime
  map artifacts, and HTML reports;
- `agent-validation-matrix` for diff-aware gate selection;
- launch intent evaluation specs for cleanup, map-build, and open-ended tasks.

The missing product-level layer is a versioned eval suite:

```text
evals/
  household_world/
    suites/
    samples/
    scorers/
```

Candidate scorer layers:

- artifact scorer: required artifacts exist and have the expected schema;
- state/outcome scorer: private final world state satisfies the goal;
- trajectory scorer: MCP tool sequence and arguments satisfy necessary process
  constraints without requiring one canonical path;
- privacy scorer: private truth never appears in agent-facing artifacts;
- efficiency scorer: tool calls, retries, latency, model work, and cost;
- model/human rubric scorer: only for open-ended semantic satisfaction.

Candidate aggregate metrics:

- pass@1 for first-attempt success;
- pass^k for reliability across repeated trials;
- restoration or progress rate;
- disturbance or side-effect count;
- trace-policy violation count;
- model/tool work per successful task.

## Deep Dive Notes

### Inspect AI: Useful Architecture, Optional Dependency

Inspect AI is the clearest open-source architecture reference for Roboclaws'
next eval layer. Its core shape is:

```text
dataset -> task -> solver/agent -> tools/sandbox -> scorer -> log
```

The fit is strong conceptually:

- dataset maps to versioned Roboclaws eval samples;
- solver maps to direct-runner, Codex CLI, Claude Code, OpenAI Agents SDK, or
  future robot agents;
- tools map to MCP tools and launch-surface capability profiles;
- sandbox maps to MuJoCo/Isaac/Agibot/OpenClaw runtime setup and reset;
- scorer maps to private cleanup scorer, artifact checker, trajectory checker,
  privacy checker, and optional model/human rubric;
- logs map to existing `trace.jsonl`, `run_result.json`, `report.html`, and
  report-performance artifacts.

Recommendation from this pass: copy the abstraction vocabulary before adding a
dependency. Roboclaws already has launch catalog, Just recipes, MCP tools, and
HTML reports. Introducing Inspect directly would be useful only if its runner
and log viewer reduce enough local orchestration code to justify another
framework boundary. A repo-native first slice keeps the household-specific
public/private truth and report contracts easier to audit.

Second-pass detail: Inspect already has explicit support for agent evaluations,
external software-engineering agents such as Claude Code and Codex CLI, custom
agents, agent bridge, MCP tools, and sandboxed execution. That makes it a
strong reference for future live-agent orchestration, especially if Roboclaws
later wants one eval runner that can launch multiple agent harnesses under a
consistent logging contract.

Risk: Inspect's generic abstractions may obscure Roboclaws-specific launch
axes. If adopted too early, it could move important concepts such as
`surface`, `world`, `backend`, `evidence_lane`, `camera_labeler`, and
private-scorer truth into adapter glue instead of keeping them obvious in the
eval result packet.

Follow-up question: prototype one toy `cleanup_capability` sample in
repo-native Python, then compare what Inspect would remove or complicate.

### tau-bench: Final State And Reliability

tau-bench is the strongest reference for tool-using service agents. The useful
pieces for Roboclaws are not the airline/retail domains; they are:

- a task instance includes user intent plus domain policy;
- the agent interacts with tools and a simulated user/environment;
- final state is compared against an annotated goal state;
- repeated trials matter;
- `pass^k` measures whether the agent succeeds consistently, not just whether
  one retry eventually works.

Mapping to Roboclaws:

- domain policy -> household skill instructions, allowed capability profile,
  safety constraints, and private-truth boundary;
- domain APIs -> MCP observe/navigate/pick/place/map/done tools;
- database state -> final world state, generated mess state, runtime map state,
  and optional planner-proof state;
- annotated goal state -> private scorer manifest, acceptable destination sets,
  open-ended goal rubric, and task-specific predicate set;
- `pass^k` -> repeated seeds or repeated live-agent trials over the same
  sample identity.

Recommendation from this pass: introduce both `pass@k` and `pass^k`, but use
them for different decisions. `pass@k` is useful for "can a retry rescue this
task?" `pass^k` is useful for "is this reliable enough to trust as product
behavior?"

### BEHAVIOR And RoboCasa: Predicate Goals For Household Tasks

BEHAVIOR-1K and RoboCasa are the robotics references most relevant to
Roboclaws. Their shared lesson is that household tasks should be scored from
world state and task predicates, not only from high-level textual success.

Roboclaws already has the raw material for predicate-like scoring:

- generated mess objects and expected acceptable destinations;
- runtime metric maps and actionable semantic map snapshots;
- observed object evidence and public/private object handles;
- cleanup progress and disturbance counts;
- planner-proof bundles for manipulation feasibility.

Recommendation from this pass: define Roboclaws predicates narrowly, not as a
general task language at first. Examples:

- `object_in_acceptable_destination(object_id)`;
- `object_not_disturbed(unrelated_object_id)`;
- `runtime_map_contains_public_anchor(anchor_id)`;
- `agent_observed_before_acting(object_handle)`;
- `private_truth_not_in_agent_view(field_path)`;
- `planner_proof_attached_for_action(action_id)`.

These can back cleanup, map-build, and open-ended household evals without
inventing a large declarative planning language.

### Cursor: Product-Local Benchmarks Beat Generic Leaderboards

Cursor's strongest lesson is organizational rather than technical: an agent
product needs its own benchmark from real usage. CursorBench uses real
engineering tasks and evaluates more than correctness. Cursor also treats the
agent harness as a product surface with metrics such as latency, token
efficiency, tool-call counts, cache behavior, Keep Rate, and user follow-up
signals.

Mapping to Roboclaws:

- real usage -> successful and failed household-world reports, operator console
  runs, and local-dev proof attempts;
- ambiguous multi-file task -> open-ended household prompt with several
  plausible action plans;
- code quality -> world-state quality, semantic acceptability, map usefulness,
  trace honesty, and report reviewability;
- Keep Rate / user feedback -> future operator confirmation or human report
  review labels.

Recommendation from this pass: do not treat public benchmarks as release
criteria. Use public benchmarks to choose vocabulary and calibrate expectations;
use Roboclaws eval suites as release criteria.

Second-pass detail: Cursor's agent-harness work separates straightforward
operational metrics from harder quality metrics. Straightforward metrics include
latency, token efficiency, tool-call count, and cache hit rate. Harder product
signals include Keep Rate and user follow-up semantics. Cursor also treats
unknown tool errors as harness bugs and classifies expected errors by cause,
including invalid arguments, unexpected environment, provider errors, user
aborts, and timeouts.

Mapping to Roboclaws:

- `InvalidArguments` -> malformed MCP tool arguments or stale handles;
- `UnexpectedEnvironment` -> simulator/backend mismatch, missing object,
  blocked waypoint, or stale map prior;
- `ProviderError` -> model route, VLM sidecar, DINO sidecar, or provider timing
  failure;
- `UserAborted` -> operator stopped live run;
- `Timeout` -> step, wall-clock, provider, or planner-proof budget exhausted;
- unknown tool/runtime error -> harness bug until classified.

Recommendation from this pass: normalize failure classes in eval results before
adding many more suites. Otherwise run reports will stay visually useful but
hard to aggregate.

### Anthropic: Eval Identity Must Include Runtime Conditions

Anthropic's infrastructure-noise warning is directly applicable. A Roboclaws
eval result is not comparable unless it records at least:

- eval suite version and sample id;
- agent engine and version;
- model and provider profile;
- skill version or prompt source;
- MCP profile and tool surface;
- world, backend, evidence lane, camera labeler, and seed;
- hardware/runtime constraints where relevant;
- network/provider route where live models are used;
- time, step, token, and cost budgets;
- artifact schema versions.

Recommendation from this pass: make this identity part of every eval result
packet. Do not let the report UI be the only place where these details exist.

### OpenAI: Trace-First Skill Evaluation

OpenAI's skill-eval framing fits Roboclaws skills well. A useful eval should
start with concrete prompts or tasks, capture the run, then evaluate trace and
artifacts with explicit checks.

Mapping to Roboclaws:

- prompt set -> open-ended household prompts, cleanup preset samples, map-build
  samples, camera-grounded samples;
- captured run -> existing output directory and report artifact set;
- checks -> deterministic artifact/state/trajectory/privacy/efficiency
  scorers;
- score -> suite-level pass/fail plus diagnostic dimensions.

Recommendation from this pass: every skill-changing PR should have a matching
eval suite or sample rationale. If a behavior change is not captured by an eval,
the PR should explicitly say why.

### Public Benchmarks: Calibration, Not Release Gates

The benchmark survey shows a consistent pattern. Strong public benchmarks define
task instances, environment setup, an execution harness, and scoring. They are
valuable for vocabulary and for calibrating what other teams consider hard.
They are weak as direct release gates for Roboclaws because:

- task distribution rarely matches household robot demos;
- grading rules often encode domain-specific assumptions;
- contamination and benchmark overfitting are active problems;
- harness/runtime differences can dominate small score deltas;
- leaderboards usually hide product-specific constraints such as public/private
  evaluator separation, report reviewability, and real-robot safety.

Use public benchmarks this way:

- SWE-bench -> reproducible task instance and harness design;
- OSWorld/WebArena/WorkArena/BrowserGym -> resettable environment and
  execution-based UI scoring;
- tau-bench -> final state, policy constraints, simulated user, and `pass^k`;
- AgentDojo -> tool-output trust and injection robustness;
- BEHAVIOR/RoboCasa -> household predicate/state scoring.

Do not use them as Roboclaws release criteria unless a future product surface
explicitly targets that benchmark.

## Proposed Roboclaws Eval Vocabulary

Use a small vocabulary before adding implementation:

- `eval_suite`: versioned group of samples, thresholds, and required graders.
- `eval_sample`: one task setup with public inputs, private goal reference,
  allowed agents, seeds/trials, and grader list.
- `eval_trial`: one execution of one sample by one agent identity.
- `eval_result`: machine-readable packet with identity, scorer outputs,
  aggregate status, artifacts, and limitations.
- `grader`: deterministic, model, or human scoring unit.
- `outcome`: final world/map/task state, not the agent's completion claim.
- `trajectory`: ordered tool and state-transition evidence.
- `failure_class`: normalized reason a trial failed.

Candidate first failure taxonomy:

- `artifact_missing`;
- `environment_blocked`;
- `agent_no_completion_claim`;
- `private_goal_not_satisfied`;
- `partial_progress_only`;
- `trajectory_policy_violation`;
- `private_truth_leak`;
- `tool_argument_invalid`;
- `tool_noop_or_repeated_failure`;
- `perception_miss`;
- `map_actionability_failure`;
- `planner_proof_missing_or_failed`;
- `model_or_provider_unavailable`;
- `budget_exhausted`;
- `grader_inconclusive`.

## Candidate First Implementation Slice

This is still a research recommendation, not an approved plan:

1. Define `evals/household_world/suites/smoke_regression.yaml`.
2. Define 3-5 samples each for:
   - cleanup with world-oracle labels;
   - map-build with runtime metric map output;
   - open-ended household goal with a simple human-readable rubric.
3. Implement a deterministic runner that lowers a sample to existing
   `just run::surface` commands for direct-runner only.
4. Implement artifact, state/outcome, privacy, and basic trajectory graders.
5. Write `output/evals/<suite>/<stamp>/eval_results.json` and
   `eval_report.html`.
6. Only after this works, add live-agent repetitions and `pass^k`.

## Open Questions For Deeper Research

1. How much of Inspect AI's dataset/solver/scorer/sandbox structure should be
   adopted directly versus mirrored in repo-native Python?
2. How should tau-bench's final database-state scorer and `pass^k` map to
   Roboclaws household-world state, private scorer manifests, and generated
   mess sets?
3. How should BEHAVIOR/RoboCasa-style goal predicates map to cleanup,
   map-build, open-ended household goals, and future real-robot proofs?
4. What should be first-class in eval identity: model, provider profile,
   agent engine, tool surface, skill version, world, backend, evidence lane,
   camera labeler, seed, hardware/runtime, network, and budget?
5. What failure taxonomy should Roboclaws standardize so report failures become
   regression samples instead of one-off notes?
6. Where should eval artifacts live relative to existing
   `output/agent-validation-matrix/`, live reports, and retrospectives?

## Provisional Direction

The likely plan is not to replace current gates. Instead:

1. keep `agent-validation-matrix` as the change-aware gate selector;
2. add a versioned eval sample and suite layer;
3. implement deterministic direct-runner evals first;
4. add live-agent repetitions and `pass^k` once sample schemas and scorers are
   stable;
5. route failures from human report review back into regression samples.
