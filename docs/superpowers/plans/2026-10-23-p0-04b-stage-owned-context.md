# P0-04B Stage-Owned Measurement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (native inline recommended for these
> dependent tasks) or superpowers:subagent-driven-development to implement task by task. Steps use checkbox syntax
> for tracking.

**Goal:** Implement a test-only public-SDK adapter with eight structured reads around the four existing main-stage
turns, and prepare bounded offline qualification without claiming full P0-04B acceptance.
**Architecture:** Closed reducers validate per-stage evidence; a public SDK bridge owns one connection/consumer per
stage. An isolated one-shot loopback harness exercises actual project files, the narrow Agent measurement hook and
resumed synthetic history, while full/live/role gates remain separate.
**Tech Stack:** Python stdlib, existing optional claude-agent-sdk/anyio, existing POSIX process ownership, Debian
WSL/bubblewrap, existing repository Node configuration tools and MCP fixture; no dependency installation.
**Spec:** `../specs/2026-10-23-p0-04b-stage-owned-context-design.md`, approved by the operator on 2026-10-23.
Implementation plan approved for native inline execution on 2026-10-24; native execution remains a separate gate.

## Global Constraints

- Planning baseline: `9e6eaf623bd46777f3f167817a4f9ed0f365ceb6`; reuse/verify the existing isolated
  `p0-04b-browser-automation` worktree, never implement on main. Preserve operator edits; rebase the plan's anchors
  if state differs.
- This plan is approved for native inline implementation on 2026-10-24. Design/plan approval does not grant native Claude execution,
  version probes, provider access, operator settings/credentials, downloads, push, PR or merge.
- Four ordered stages: skill, subagent, discovery, use; exactly one existing user query and one before/after pair
  per completed stage. No additional identity/warm-up query, M2 observer, concurrent client or automatic
  retry/fallback.
- Keep stage-specific tools/MCP policy, default permission mode and native auto-compaction enabled. No union grants,
  private wire controls, version/window pins or absolute capacity overrides.
- Public SDK/CLI capabilities must be detected; missing support is inconclusive. Do not install/update/copy the
  existing SDK installation or silently choose its bundled CLI.
- Proposed later OFFLINE ceiling: four main queries, eight context calls, forty generation HTTP requests INCLUDING
  nested work,192 counting requests total/48 per stage, four main CLI processes and at most four SDK auxiliary
  version probes. At most25 seconds per non-generating operation,120 seconds per stage and600 seconds total,
  including cleanup. A fresh exact-artifact grant is mandatory before that attempt.
- Offline continuity uses fresh marker text only in emulator terminal assistant replies for stages1-3. Existing user
  prompts and exact tool inputs remain unchanged. No real-provider reply rewriting.
- All remove/corrupt/substitute/wrong-session negative controls are local/in-memory, not additional native attempts.
  No native negative matrix is implicitly required or authorized.
- Native hook qualification is PreToolUse:Agent measurement proof only. Command/browser guards remain
  CONFIGURED_UNPROVEN; no invented PostToolUse:Agent, operational Bash/browser call or ACTIVE claim.
- Preserve the consumed provenance artifact `488de64310a64ab3fbd17194812b91a666ecee7db8123b2c8fb5197787ad6632`, its
  earlier predecessor and reservations/results. No runtime import from `.review-runtime` into product tests.
- Retain only closed numeric/structural results. Run/session identifiers stay in owned private evidence;
  marker/content/history never enter the public aggregate. Cleanup failure dominates any provisional success.
- Roles/live/provider/browser acceptance stay blocked/separate. No v2-to-v1 coercion, skipped role gate, full
  authenticated smoke or completed TODO in this increment.

## Review Focus

1. A public SDK event may omit a field or expose cumulative rather than per-response usage: fail closed without
   synthesizing values; Task2 tests missing/partial/nested/cumulative frames.
2. A native continuation or error can arrive after ResultMessage or during shutdown: provisional success must be
   revoked; Tasks2/4 test late faults and final snapshot ordering.
3. A correct session string can accompany another run's history: correlate the prior fresh assistant marker in the
   next top-level request; Task3 tests role/source/replay confusion.
4. Direct provider token-count requests are not SDK query counts: offline budgets count actual HTTP attempts, while
   no live HTTP-cap claim is made; Tasks3/4 test budgets and blocked live entries.
5. A green package gate may omit the optional SDK, or main-only evidence may look like full acceptance: distinguish
   gate states and reject schema promotion; Tasks1/5 pin both cases.

## File and dependency map

All execution paths below are relative to the Git worktree, not the umbrella workspace.

Create runtime helpers (test-only):
- `tests/browser_context_contract.py`: projections, stage policies, v2 schema/reducers and public minimization.
- `tests/browser_context_sdk.py`: capability/options boundary, one consumer, native event reducer and stage runner.
- `tests/browser_context_gateway.py`: bounded loopback emulator, stage protocol, accounting and continuity flags.
- `tests/browser_context_project.py`: canonical local native-artifact fixture, installed semantic validation and
  exact local settings.
- `tests/offline-browser-context-smoke.py`: exclusive grant/fingerprint entry, namespace/orchestration,
  cleanup-before-publication.

Create five matching suites: `tests/test-browser-context-contract.py`, `tests/test-browser-context-sdk.py`,
`tests/test-browser-context-gateway.py`, `tests/test-browser-context-project.py`,
`tests/test-offline-browser-context-safety.py`.
Modify existing `tests/test-live-browser-operation-safety.py` only for full-gate rejection regression; modify
`tests/validate-package.sh` for zero-native local test wiring.
Reuse unchanged `tests/terminal_cancellation.py`, `tests/browser-measurement-guard.py`,
`tests/mcp-context-fixture.py`, installed-subagent validators, package staging and hook configurators. Do not
extract/refactor the legacy live harness as incidental work.
Documentation: versioned spec/plan, `docs/reviews/2026-10-23-p0-04b-native-provenance-result.md`, ADR-010/index,
`tests/validation-notes.md`, one README test-entry link and the existing unreleased CHANGELOG section.

Local test commands use `python3 tests/<suite>.py -v` from the worktree. For actual SDK-boundary tests use the
existing read-only venv Python instead, with `PYTHONDONTWRITEBYTECODE=1`. Test files prepend `tests` to imports as
existing suites do; they must not launch Claude. No shell glob discovery.

### Task 1: Pin the private evidence contract and main-only acceptance boundary

**Files:** create contract/suite; promote approved documents to
`docs/superpowers/specs/2026-10-23-p0-04b-stage-owned-context-design.md` and
`docs/superpowers/plans/2026-10-23-p0-04b-stage-owned-context.md`; add the full-gate rejection test to
`tests/test-live-browser-operation-safety.py`.
**Consumes:** approved spec, existing five-anchor/twelve-role validator (do not loosen it).
**Produces interfaces:**
- `STAGES = ('skill','subagent','discovery','use')`; `stage_policy(stage: str, nonce: str) -> dict` returns exact
  prompt, built-in tools, allowed call/input and MCP class.
- `project_context(raw: dict) -> dict`, `project_api_usage(raw: dict) -> dict`: the approved six-scalar and
  four-number/presence projections, dropping all other raw data.
- `offline_usage(before: dict, ordinal: int) -> dict`: safe synthetic accounting used only by the emulator. Set
  D=min(native maxTokens,rawMaxTokens), input=D//8+ordinal, output10/cache0/0; require global generation
  ordinal1..40, input+10<=D//4 and a tuple different from valid before accounting, otherwise stop
  CHALLENGE_UNAVAILABLE without another draw/query. No absolute window size.
- `finish_stage(stage: str, before: dict, after: dict, witness: dict) -> dict`; `validate_main(value: dict,
  expected_nonce: str, expected_session: str) -> dict`; `public_main(value: dict) -> dict`. Invalid schemas raise
  ValueError; closed stage reasons are returned for valid inconclusive evidence.

Pin shapes in this task, so later tasks do not invent fields:
- Observation is exactly `{context,apiUsage}`. Context keys:
  totalTokens,maxTokens,rawMaxTokens,percentage,autoCompactEnabled,categoryCount. Usage state is
  ABSENT/NULL/VALID/INVALID with `values=None` except VALID's exact four safe nonnegative integers; bool is not an
  integer. Category count<=4096; no content/name/path projection.
- Witness is exactly
  `{latestResponseUsage,sessionBound,policyFixed,historyLinked,measurementHook,claimVerified,actionCalls,toolResultsComplete,toolSearchAvailable,unexpectedCalls,fault}`.
  Flags are bool; historyLinked is NOT_REQUIRED for skill or OBSERVED/UNPROVEN otherwise; measurementHook is
  NOT_REQUIRED or OBSERVED/UNPROVEN. actionCalls/unexpectedCalls are bounded integers. No event text or identifiers.
- Stage record is exactly `{stage,before,after,witness,outcome,reason,deltaTokens}`. Outcome QUALIFIED/INCONCLUSIVE.
  Reason is one of
  NONE,USAGE_PROVENANCE_UNPROVEN,NON_COMPARABLE,SESSION_UNPROVEN,HISTORY_UNPROVEN,HOOK_UNPROVEN,POLICY_UNPROVEN,INVALID_OBSERVATION,UNEXPECTED_TOOL,STATE_UNPROVEN,BUDGET_INCONCLUSIVE,OPERATION_TIMEOUT,CLEANUP_INCONCLUSIVE,CAPABILITY_UNAVAILABLE,CHALLENGE_UNAVAILABLE.
  No arbitrary exception string.
- Private report is exactly `{schema,schemaVersion,runNonce,sessionId,stages,outcome,reason,cleanupVerified}` with
  schema MAIN_STAGE_CONTEXT_V2/version2. Success MAIN_STAGE_QUALIFIED requires all four ordered qualified records
  and verified final cleanup. Failure INCONCLUSIVE may contain an ordered prefix only. Before/after unavailable on
  failure are null, never fabricated readings. Private regular file<=64KiB,0600/no-follow,POSIX only.
- Public report removes runNonce/sessionId and retains the other exact fields; no runtime path, marker, raw hook
  payload or session UUID. Validate stage outcomes/deltas again, not merely success booleans.

- [ ] Write RED `test_usage_presence_and_safe_numeric_projection`,
      `test_zero_negative_delta_and_equal_percentage_can_qualify`,
      `test_replayed_cumulative_or_nested_usage_cannot_qualify`, `test_denominator_drift_is_non_comparable`,
      `test_main_v2_cannot_pass_full_role_validator`. Use literal input/output/cache values1250/10/0/0; change
      before100/after99 and expect delta-1 when usage association is distinctive. Require M1
      VALID==latestResponseUsage and !=valid before tuple; equal accounting is inconclusive, not a retry.
- [ ] Write RED `test_exact_schema_order_and_cleanup_are_required`,
      `test_partial_failure_contains_no_invented_samples`,
      `test_stage_policy_preserves_existing_prompts_and_inputs`, `test_offline_usage_uses_reported_window`. For
      D10000/ordinal1 expect1251/10/0/0; for insufficient headroom expect closed failure, never a configured window
      override.
- [ ] Run `python3 tests/test-browser-context-contract.py -v`. Expected: missing contract/API or assertion failures,
      not native execution. Capture the RED evidence.
- [ ] Implement the signatures and closed schema minimally. Copy only relevant pure projection logic from the
      predecessor conceptually; do not modify/import the immutable experiment or retain its universal positive-total
      predicate. A zero/negative delta is allowed; delta is null when denominators differ.
- [ ] Run that suite plus `python3 tests/test-live-browser-operation-safety.py -v`. Expected: both pass; existing
      full acceptance still rejects missing roles/v2 input.
- [ ] Commit only named files: `test: define main-stage structured context evidence`. Preserve nori.json
      version0.15.0; this is a test-only unreleased increment, not a new release.

Task1's literal numeric assertion (the test constructs all six context scalars and NULL before apiUsage):

```python
assert offline_usage(before, 1) == {
    "input_tokens": 1251, "output_tokens": 10,
    "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
}  # total100, max/raw10000, percentage0, autoTrue, categoryCount0
```

### Task 2: Implement the public SDK bridge and continuous event validation

**Files:** create `tests/browser_context_sdk.py` and `tests/test-browser-context-sdk.py`.
**Consumes:** Task1 policies, projections and finish_stage.
**Produces interfaces:**
- `detect_sdk(sdk: object) -> dict` returns closed available/reason flags without connecting or running a version
  command.
- `build_options(policy: dict, owned_root: Path, cli_path: Path, session_id: str, *, resume: bool) -> object` uses
  the installed public options type.
- `StageEvents(policy: dict, expected_session: str)` with `feed(message: object) -> None`, `snapshot() -> dict`,
  `terminal: bool`, `fault: str`: one sticky reducer; snapshots are content-free witnesses.
- `async run_stage(client: object, policy: dict, expected_session: str, *, resume: bool, before_query: callable,
  history_check: callable, claim_check: callable, stage_deadline: float) -> dict` returns exactly
  `{sessionId,record,clientsClosed}`. Returned sessionId is ACTUALLY observed and remains private. Invoke
  before_query(projected_before) exactly once between the before read and query; Task4 supplies Gateway.arm.
  Injected checks read owned gateway/claim facts, not operator input flags.

- [ ] Write RED `test_options_are_fixed_project_local_and_default_permission`, checking system preset claude_code,
      setting_sources=['project','local'], strict MCP, canonical supplied cli_path, exact tools/allowed_tools, no
      agents override, no user source and no union grants. Use max_turns4 per top-level query, while global HTTP
      generation cap includes child work. No snapshot override or extra version probe.
- [ ] Write RED actual SDK in-memory controls `test_parser_preserves_latest_usage_and_agent_hook_fields`,
      `test_missing_partial_cumulative_nested_or_replayed_usage_is_unproven`, `test_actual_init_result_must_match`,
      `test_unexpected_background_reset_or_compaction_stops`. Exercise actual installed SDK typed/parser boundaries
      without connect/native subprocesses. No programmatic replacement of project agents.
- [ ] Write RED `test_one_consumer_before_query_after_close_order`,
      `test_after_result_tool_or_hook_failure_revokes_success`, `test_close_timeout_dominates_pair`,
      `test_declared_sdk_missing_never_qualifies`. Use a fake public client and actual contract reducers. Exactly
      one consumer spans before/query/after/disconnect; query once; native Result success is provisional until final
      lifecycle/cleanup checks.
- [ ] Run `python3 tests/test-browser-context-sdk.py -v` using the existing venv. Expected: RED for missing bridge.
      Without the optional SDK, only pure fake-boundary cases run and real-SDK cases explicitly skip; qualification
      remains unavailable, not pass.
- [ ] Implement bridge. Pair native tool IDs/results and init/result session IDs on that one owned consumer; never
      fill a missing event session field with the requested ID. Where public UserMessage omits session metadata,
      report only actual tool-ID/owned-stream association, not invented per-envelope native SID proof. Missing
      required proof is CAPABILITY_UNAVAILABLE/SESSION_UNPROVEN. Stage latest usage comes from the last completed
      top-level AssistantMessage, never ResultMessage cumulative usage or child output; ambiguous fields/IDs fail
      closed. ToolSearch absence is valid only from an actual bounded advertised tool list; missing advertisement
      metadata is not evidence of absence.
- [ ] Require the Agent hook's matching lifecycle, FIRST_CALL output, successful completion and fresh private claim.
      NOT_REQUIRED is valid for other stages only; never assert operational Bash/browser coverage. Reject unexpected
      tool calls at any parent depth, hanging tool results or deferred/background tasks. Keep fault monitoring
      active through final close.
- [ ] Run contract+SDK suites with all actual-SDK cases executed, zero native processes. Expected: PASS with
      explicit SDK-boundary coverage, not merely a skipped suite. Commit `test: add stage-owned public SDK context
      adapter`.

Task2's public-options assertion, with temporary owned paths and no connection:

```python
options = build_options(stage_policy("skill", "run-001"), owned_root,
                        cli_path, "native-001", resume=False)
assert options.tools == ["Skill"]
assert options.allowed_tools == ["Skill(context-continuity)"]
assert options.permission_mode == "default"
assert options.setting_sources == ["project", "local"]
```

### Task 3: Implement the bounded owned emulator and continuity proof

**Files:** create `tests/browser_context_gateway.py`, `tests/test-browser-context-gateway.py`.
**Consumes:** Task1 stage_policy/offline_usage and Task2 stage progression.
**Produces:** `Gateway(nonce: str)` context manager with `begin_stage(stage: str)`, `arm(before: dict)`, `snapshot()
-> dict`, `stopped: bool`, `port: int`. `arm` binds native window metadata after the before read; no generation is
accepted before it. The gateway has no forwarder or real-provider URL option.

- [ ] Write RED actual-wire tests `test_json_and_sse_accounting_agree`, `test_stage_tool_script_is_exact`,
      `test_agent_child_requests_count_toward_global_budget`, `test_available_and_unavailable_search_branches`,
      `test_nonce_ping_occurs_once`. Use actual HTTP JSON/SSE bodies and native fixture tool formats, not a mocked
      reply generator.
- [ ] Write RED `test_prior_marker_must_be_assistant_history_from_current_run`,
      `test_fixed_ack_system_user_text_other_stage_and_other_run_do_not_bind`,
      `test_local_removed_corrupt_substitute_history_fails`. Markers occur only in stages1-3 terminal emulator
      assistant text. The next stage's FIRST top-level request must carry the prior marker. Nested child traffic
      cannot replace it. These are local HTTP/in-memory negative tests, zero Claude processes.
- [ ] Write RED `test_40_generation_192_total_48_stage_budgets`,
      `test_duplicate_generation_parser_methods_and_timeout_faults_are_sticky`,
      `test_late_request_fault_is_visible_after_exit`. Count HTTP attempts/retries separately from accepted actions;
      limit rejection is a failed attempt, never a qualified report with exhausted/overrun budgets. Reuse
      duplicate/nonfinite JSON rejection, unsupported method rejection and bounded request-read timeout from the
      proven gateway pattern. Set an explicit1MiB ephemeral HTTP-body cap for the full-project fixture (not the
      minimal spike's128KiB input cap); SDK/control-message cap remains128KiB and published report64KiB. Test each
      exact boundary/one-byte overflow. No body is retained or logged.
- [ ] Run `python3 tests/test-browser-context-gateway.py -v`. Expected: RED for missing implementation; no SDK/CLI
      process.
- [ ] Implement Gateway. First request for each required action returns its exact tool_use; completed tool_result
      permits the terminal acknowledgment. Foreground Agent child ACK requests receive ACK-only replies, counted
      globally, not new top-level turns. ToolSearch is emitted only when actually advertised; otherwise use the
      existing zero-call branch. Final use carries exactly the existing nonce argument; connect/list/use evidence
      comes from the real reused MCP fixture signal, not a gateway assertion.
- [ ] Return safe synthetic four-field usage consistently in JSON/SSE, based on each stage's native before and
      accepted generation ordinal. Generate fresh reply-only markers in memory, never log/return them in snapshots.
      Other paths/content/protocol sequences fault permanently. No retry convenience or extra native profile.
- [ ] Run contract+SDK+gateway suites. Expected: PASS, zero native calls. Commit `test: add bounded stage context
      emulator`.

Gateway.snapshot is exactly {fault,generationAttempts,countAttempts,stageCounts,historyLinked}.
stageCounts has four STAGES keys with counting-attempt integers; historyLinked has three resumed-stage
keys with bools. A fault is sticky. No body, marker or model text appears in the snapshot.
Gateway faults use Task1 closed reasons: malformed/unarmed HTTP maps to STATE_UNPROVEN, missing prior marker
maps to HISTORY_UNPROVEN, quota excess to BUDGET_INCONCLUSIVE, unexpected action to UNEXPECTED_TOOL. Preserve
that final reason rather than passing an arbitrary HTTP/parser exception string.

```python
with Gateway("run-001") as gateway:
    gateway.begin_stage("skill")
    assert gateway.snapshot()["generationAttempts"] == 0
    assert gateway.snapshot()["fault"] == "NONE"
# The actual-wire tests POST before arm and assert409 plus a permanent fault.
```

### Task 4: Compose project loading, exclusive launcher and main-only offline profile

**Files:** create `tests/browser_context_project.py`, `tests/test-browser-context-project.py`,
`tests/offline-browser-context-smoke.py`, `tests/test-offline-browser-context-safety.py`.
**Consumes:** Tasks1-3; existing canonical staging/native installed-form validation, narrow measurement hook, MCP
fixture and TerminalCancellation.
**Produces interfaces:**
- `prepare_project(source: Path, owned_root: Path, *, node_path: Path) -> dict` returns exactly
  `{project,config,home,claim,signal}`, all owned Path objects used privately; never publishes paths. No caller
  settings source.
- `async run_main(client_factory: callable, gateway: Gateway, project: dict, *, nonce: str, requested_session: str,
  deadline: float) -> dict` composes four sequential run_stage calls, stopping on first failure. Uses the actually
  observed session for subsequent resume; emits the Task1 private schema only after all cleanup.
- CLI default/`--self-test`: local non-native checks; `--audit-isolation`: Python-only namespace audit, zero CLI
  mount; `--fingerprint`: read-only artifact hash; `--run-offline <sha256>`: exclusive new main-stage reservation
  and one native attempt. Fingerprint/audit/offline modes accept explicit `--cli <path> --sdk-root <path> --node
  <path>` runtime references, validate/fingerprint them, and never search operator configuration. Audit must not
  mount the CLI despite its reference. ALL live/provider/legacy entries blocked before preparing a client.

- [ ] Write RED `test_project_fixture_uses_canonical_files_not_operator_settings`,
      `test_flat_agents_and_placeholder_paths_pass_existing_validator`,
      `test_only_agent_measurement_hook_is_claimed`, `test_symlink_missing_agent_and_dependency_drift_fail`. Use the
      repository's canonical local staging and installed-form test pattern: AGENTS.md content becomes project
      CLAUDE.md, skills/references are copied from canonical source, agents flatten from SUBAGENT.md with only the
      existing skills_dir substitution. Do not replace agents via SDK options.
- [ ] Implement prepare_project using local repository content, not the credential-reading live-harness setup and
      not a fresh Nori CLI/registry install. Reuse installed-subagent semantic validation and existing hook
      configurators in the owned root with the supplied observed Node runtime. Explicitly label this as canonical
      local native-artifact projection, NOT a new Nori installation or dependency-resolution acceptance. Do not
      fetch the external read-the-damn-docs dependency; its complete Nori environment remains outside this main-only
      qualification. No operator user settings, preferences or secrets are copied/mounted.
- [ ] Write RED `test_four_queries_eight_reads_four_clients_no_overlap`,
      `test_mismatch_partial_failure_does_not_start_next_stage`,
      `test_missing_guard_claim_or_continuity_cannot_promote`, `test_shutdown_fault_refreshes_final_snapshot`. Use
      fake SDK clients with actual reducers/gateway; remove/corrupt/substitute-history controls stay local. Expected
      action counts are1 for skill/Agent/use; discovery1 if advertised,0 otherwise. Exactly one measurement Agent
      claim; operational coverage stays CONFIGURED_UNPROVEN.
- [ ] Write RED `test_default_live_legacy_wrong_hash_and_reused_grant_never_spawn`,
      `test_actual_zero_cli_namespace_audit`,
      `test_partial_cleanup_oversize_output_and_deadline_cannot_publish_success`,
      `test_no_operator_environment_or_bundled_cli_mount`. Test the existing supervisor with harmless Python
      children only; fail if an actual Claude/version subprocess starts.
- [ ] Run `python3 tests/test-browser-context-project.py -v` and `python3
      tests/test-offline-browser-context-safety.py -v`. Expected: RED before implementation; no native run.
- [ ] Implement launcher with the existing ownership pattern: bubblewrap isolated loopback network, dropped
      capabilities, hidden operator home/config/workspace, read-only explicit SDK/dependency/executable mounts,
      bundled SDK CLI masked. Reuse TerminalCancellation; do not introduce a new process supervisor. Synthetic
      environment/config only; synthetic native API confirmation may not be auto-clicked/added if not already
      covered by a later exact grant. Any unsupported native startup stops, without repair/retry.
- [ ] Share only owned project/history among the four clients; verify per-stage close/reap before advancing. Keep
      timeout caps25/120/600 and the same outer deadline through parsing, deletion and final publication. Refresh
      all facts after clients/gateway shutdown; terminate owned children and verify the exact owned root
      inode/prefix before deletion. Publish no raw stream and at most64KiB of validated aggregate. No raw diagnostic
      export.
- [ ] Fingerprint the current committed source, canonical fixture bytes, source helpers/tests/docs, read-only SDK
      dependency bytes, CLI binary and any explicit Node/configuration runtime dependencies. Native reservation uses
      exclusive no-follow0600 creation and is consumed BEFORE launch; result/attempt marker reuse always blocks.
      Recheck artifact identity after cleanup. No CLI `--help` or manual version command during preparation; the
      later grant covers at most the SDK's one auxiliary probe per stage.
- [ ] Run all five new suites, plus existing measurement guard/MCP fixture/cancellation/browser-safety regressions.
      Expected: PASS, no unexpected skips, zero Claude processes; actual SDK boundary cases must run under the
      existing venv. Commit `test: compose isolated main-stage context qualification`.

Task4's lifecycle test uses real reducers and a fake client factory, never Claude:

```python
assert result["schema"] == "MAIN_STAGE_CONTEXT_V2"
assert len(result["stages"]) == 4
assert [s["stage"] for s in result["stages"]] == ["skill", "subagent", "discovery", "use"]
assert len(fake_factory.clients) == 4
assert all(c.query_calls == 1 and c.context_calls == 2 for c in fake_factory.clients)
assert all(c.closed for c in fake_factory.clients)
```

The CLI self-test is non-recursive: run a small pure contract fixture, not the five full suites again.
Its exact output is {"scope":"SELF_TEST_ONLY","outcome":"LOCAL_SELF_TEST_PASSED","nativeProcesses":0}.
For a reserved native attempt, the OUTER report is exactly {artifactSHA256,sourceCommit,outcome,reason,main,
traffic,elapsedSeconds,cleanupVerified}. main is the Task1 public projection or null on pre-measurement failure.
traffic is exactly {userQueries,contextCalls,generationAttempts,countAttempts,stageCounts}, using real controller/
gateway counters. Success requires all eight reads/four queries, qualified main, current hash and verified cleanup;
recompute it after final gateway facts, never infer it from process exit. A missing/overrun counter fails closed.
reason uses Task1's closed reasons plus ARTIFACT_CHANGED and ISOLATION_UNPROVEN; no raw exception/string.
Do not report inferred auxiliary probe PID counts as observed; enforce the maximum through the qualified frozen
SDK connect/spawn path and one connect per owned client.

### Task 5: Wire safe package gates, document boundaries and freeze a reviewed handoff

**Files:** modify `tests/validate-package.sh`, ADR-010 and `docs/architecture/README.md`,
`tests/validation-notes.md`, README and CHANGELOG; create the short versioned prior-result report named in the file
map. Do not modify live-browser-operations-smoke.sh, its full validator, role list or workflow authorization as part
of wiring.
**Consumes:** Tasks1-4's working local-only adapter and all typed test reports.
**Produces:** versioned architecture/plan and reproducible source artifact ready to REQUEST, not perform, one
separately authorized offline attempt.

- [ ] Write RED `test_package_gate_wires_only_zero_native_context_suites`,
      `test_sdk_unavailable_is_not_adapter_qualification`, `test_new_profile_never_emits_full_acceptance_or_active`,
      `test_nori_staging_excludes_adapter_and_sdk`. Put wiring/release assertions in the existing
      safety/content/staging suites where appropriate, not a general new test framework. Pure tests always run;
      actual SDK tests explicitly skip when absent and cannot satisfy the adapter readiness gate.
- [ ] Run named safety/staging tests. Expected: RED for missing wiring/claims. Wire only the five non-native suites
      and --self-test into the package gate. No new package.json at repo root, dependency installer, registry job or
      native --run-offline invocation in CI/package validation. Keep all these helpers and SDK out of Nori
      deliverables.
- [ ] Amend ADR-010/index with new test-only sampling/schema status, operational guards still unproved, missing role
      route and exact future native/live boundaries. Record prior one-client result as structural evidence, not full
      acceptance or new grant. Update README with a short entry/link; record only actually run tests in validation
      notes and existing0.15.0 unreleased CHANGELOG. No version bump/tag/release for this test-only increment; do
      not fabricate CI/Security/native results.
- [ ] Run explicit focused commands using the existing venv for SDK coverage, with PYTHONDONTWRITEBYTECODE=1: the
      five new suite paths, test-live-browser-operation-safety.py, test-browser-measurement-guard.py,
      test-mcp-context-fixture.py, test-terminal-cancellation.py, test-installed-subagents.py,
      test-architecture-docs.py, test-nori-package-contract.py and test-nori-staging.py. Expected: PASS; report
      exact tests/skips. No native CLI invocation.
- [ ] Run the complete `bash tests/validate-package.sh` gate through Debian WSL with the proven explicit observed
      Node PATH and the existing verified terminal runtime environment. Resolve/check the configured
      P004B_TERMINAL_NODE and P004B_TERMINAL_MODULE_ROOT first; do not install or overwrite them. Use the
      immutable-source/owned-output verification procedure already recorded in tests/validation-notes.md. Expected:
      exit0 and `package validation passed`, canonical source/archive identity preserved and owned temporary roots
      removed. Record platform/optional skips honestly; this is not remote CI/Security.
- [ ] Commit named test/docs/gate files: `docs: record main-stage SDK qualification boundary`. Request the final
      independent whole-change review required by the chosen execution method. It must read this plan, spec, the
      five Review Focus cases and current ledger rulings, and must not execute Claude. Fix blocking implementation
      defects with observed RED/GREEN plus full affected suite; do not widen design/authority to rescue a missing
      runtime field.
- [ ] After review/fixes, verify clean source state, unchanged predecessor artifacts, no new main-stage
      attempt/result marker, and full current fingerprint. Record local/SDK/review/package/native/CI/live/role
      statuses separately. Expected: local qualification prepared, native NOT_RUN, live EXCLUDED, roles BLOCKED,
      CI/Security NOT_RUN unless independently observed. No push/PR/merge or TODO completion.
- [ ] Hand off exact source/artifact ID and proposed offline limits for NEW operator authorization, explicitly
      including synthetic reply-only markers and disposable history. Do not run it under this plan approval. If
      later authorized offline qualification passes, design the remaining live/role integration separately; if
      inconclusive, stop and report the causal boundary without another automatic observer/attempt.

Task5's full-gate safety assertion keeps the existing validator unchanged:

```python
with self.assertRaises(ValueError):
    validate_trusted_measurement(
        {"schema": "MAIN_STAGE_CONTEXT_V2", "schemaVersion": 2},
        "run-001", {"workflow-001"})
```

## Execution setup and command route

The current product worktree is
`C:/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation`; WSL
counterpart is
`/mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/p0-04b-browser-automation`.
Before execution re-read AGENTS.md and applicable safety/skill instructions, inspect Git status/HEAD locally with
command-local safe.directory, and use the worktree/implementation skill selected by the operator. Do not start
implementation while this plan is still awaiting review.
The current existing SDK interpreter is
`/mnt/c/projects/senior-infra-ops-analyst/.review-runtime/p004b-sdk-feasibility/.venv/bin/python`; use it read-only,
no pip/install/update. These are observed local routes, not product path/version pins. Runtime inputs to the later
launcher are explicit validated/fingerprinted dependencies, never operator config discovery.
WSL commands use `wsl.exe -d Debian --cd <worktree> -- ...` through the authorized host route. No bare bash from
PowerShell. A focused SDK command is `env -i HOME=/tmp PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1
<existing-venv-python> tests/test-browser-context-sdk.py -v`. Do not accidentally run the legacy --run-live or new
--run-offline while verifying local tests.

## Self-review and handoff

- Scope: one subsystem, main-stage test instrumentation. The SDK bridge/emulator/project fixture are dependencies of
  one working offline route, not separate product projects.
- Coverage: contracts/sampling/schema Task1; SDK/tool/hook/late lifecycle Task2; continuity/wire/accounting/budgets
  Task3; real file loading/ownership/reservation Tasks4; full-gate separation, optional dependency and package/ADR
  evidence Task5.
- Interfaces: Task1 defines shapes, policies and finish_stage; Task2 produces StageResult; Task3 supplies gateway
  facts; Task4 alone owns whole-run publication and cleanup; Task5 never relaxes the full validator.
- Review Focus: each of the five cases has named tests in its owning task. Native compatibility is deliberately NOT
  claimed by the local controls.
- Decisions: local canonical projection does not claim a new Nori installation; tool-ID/owned-stream association is
  not invented per-envelope SID data; offline counts are not live HTTP caps; approval of this plan is not a native
  grant.
- Method recommendation: native inline, because all five tasks consume the preceding contracts and one final
  independent review is proportionate. The operator selected native inline execution on 2026-10-24; this does not authorize a native Claude run.
