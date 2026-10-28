# Secure CI Dependency and Isolation Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for direct execution with one independent final review. Steps use checkbox syntax for tracking. This proposed method preserves the direct execution used on this PR; wait for operator review of this plan before implementation.

**Goal:** Refresh the three full-gate jobs safely, optionally upgrade viable image
packages, and qualify a fixed private Bubblewrap plus selective AppArmor policy
without weakening offline isolation or claiming native acceptance.

**Architecture:** Share one CI-only bootstrap across the existing workflows.
Separate package-policy decisions, dependency identity, bounded policy diagnosis
and actual isolation proofs. Keep privileged operations narrow and cleanup owned;
no generic root launcher or automatic fallback can turn missing proof into green.

**Tech Stack:** Python standard library, fixed argv subprocesses, Ubuntu APT,
Meson/Ninja/libcap, AppArmor 4 ABI and existing GitHub Actions/Node test runtimes.

**Spec:** docs/superpowers/specs/2026-10-24-ci-isolation-bootstrap-design.md,
approved with the general-upgrade feasibility amendment on 2026-10-24.

<!-- cspell:ignore libcap setuid dbus libc libpam libnss libsystemd moby walinuxagent userns autoremove NEEDRESTART_MODE EPERM sysctls NoNewPrivs fcntl needrestart -->

## Global Constraints

- Reuse the isolated p0-04b-browser-automation worktree; preserve operator edits.
- Baseline 7aa88c09304ba6bb25476b836ef430145520d47a contains the original design;
  this plan and its approved amendment precede any runtime implementation.
- Retain Ubuntu 24.04, all three 40-minute full-gate jobs and mandatory real audit.
- No OS migration, reboot, removals, downgrade, forced holds or new repositories.
- No global AppArmor/sysctl relaxation, setuid/file capabilities, elevated suite,
  host-network payload, unverified source, release/tag, merge or TODO completion.
- Build/probe unprivileged. Root only installs verified owned data or invokes
  trusted package/parser commands with fixed arguments and sanitized environments.
- No Claude/provider/browser run, operator config/credentials, native reservation
  or reuse of any consumed grant. Additional remote dispatch is separately gated.
- Keep 15 seconds per probe and 120 seconds total for diagnosis/policy testing.
- Keep root 0.15.0 unreleased and browser component 1.0.2 unchanged for CI-only work.
- English deliverables; no disabled global lint/security rule or hidden test skip.
- Evidence remains bounded/structural; raw audit, environment, prompt/history and
  credential data do not become artifacts. Failure/cleanup dominate success.

## Review Focus

1. APT simulation differs from execution, changes protected services, or is
   malformed: no speculative upgrade, stale-package fallback or partial success.
2. Verified source becomes a substituted binary/path before privileged use:
   identities and immutable ownership must hold at every boundary.
3. AppArmor matches a foreign profile or grants setup privilege to executed
   children: refuse conflict and prove child restrictions rather than trust text.
4. An audit looks green with shared namespaces, hidden capabilities or writable
   host binds: negative controls must reject these actual boundary failures.
5. Cancellation or full-gate failure leaves owned policy installed or causes
   unrelated publishing: cleanup is bounded, ownership-safe and success-gating.

## File and interface map

- tests/ci-runtime-lock.json: immutable source/build/provenance baseline.
- tests/ci_image_upgrade.py: bounded APT parsing, Debian version comparison and
  general-upgrade feasibility; no installation side effects at import time.
- tests/ci_isolation_runtime.py: source/binary verification and safe private
  installation facts; no policy mutation or arbitrary command execution API.
- tests/ci_isolation_bootstrap.py: fixed CLI orchestration, diagnosis, policy
  lifecycle, structural report and owned cleanup.
- tests/ci_isolation_probe.py: fixed synthetic isolation payload/controller;
  cannot accept model-supplied commands, mount paths or native executables.
- tests/fixtures/ci-isolation/: reviewed policy template, source notices and
  bounded package/audit fixtures; no real operator data.
- tests/terminal_input_challenge.py: strengthen the existing portable audit while
  retaining audit_offline_namespace() and its three-boolean result.
- tests/validate-package.sh: run new provider-free tests early, preserve real audit.
- .github/workflows/{ci,release,scheduled-maintenance}.yml: parity wiring and
  validation-job permissions/cleanup only; no unrelated action upgrades.
- docs/architecture/ADR-011-ci-isolation-bootstrap.md and README.md index:
  record the new CI trust boundary; CHANGELOG/validation notes record exact gates.

## Task 1: Lock provenance and classify image upgrades

**Files:** Create tests/ci-runtime-lock.json, tests/ci_image_upgrade.py,
tests/ci_isolation_runtime.py, tests/test-ci-image-upgrade.py and
tests/test-ci-isolation-runtime.py; add small fixture files under the new fixture
directory only as needed by these tests.

**Interfaces:** Frozen records UpgradeProposal(actions, held_count),
UpgradeDecision(status, reason, package_count) and RuntimeSpec(version, source_url,
source_sha256, source_size, source_commit, architecture, build_options).

```text
parse_apt_simulation(text: str) -> UpgradeProposal;
compare_debian_versions(left: str, right: str) -> int;
assess_upgrade(proposal, *, reboot_required: bool, service_packages: frozenset[str],
compare_versions: Callable[[str,str],int]) -> UpgradeDecision.
assess_dependency_install(proposal, *, requested: frozenset[str],
service_packages: frozenset[str], compare_versions) -> UpgradeDecision;
load_runtime_spec(path: Path) -> RuntimeSpec; verify_archive(data: bytes, spec) -> None.
```

The dependency-install assessment permits verified new build dependencies but
blocks protected/transitive service changes.
Statuses: ALLOW, UP_TO_DATE, SKIP_UNSAFE, BLOCKED. Exceptions expose closed reasons.

- [ ] Write tests for valid Inst/Conf records and literal decisions: safe upgrade
  ALLOW; zero actions UP_TO_DATE; removal/new-install/downgrade/held/reboot/service
  change SKIP_UNSAFE; malformed, duplicate, oversized or unknown records BLOCKED.
  Include simulation drift, Debian epochs/revisions and comparator error controls.
  Separately assert new safe requested dependency/closure packages are allowed
  by assess_dependency_install, whereas a service-bearing new package is blocked.

  Representative tests (the surrounding unittest class supplies the imports):

  ```python
  def test_debian_epoch_is_not_lexical(self):
      self.assertGreater(compare_debian_versions("2:0.1-1", "1:99.0-9"), 0)

  def test_oversized_simulation_is_rejected(self):
      with self.assertRaises(ValueError):
          parse_apt_simulation("x" * (512 * 1024 + 1))
  ```

- [ ] Write artifact tests: exact archive digest/size accepted; one changed byte,
  extra bytes, affected version, mutable URL, unsupported architecture and missing
  provenance rejected before any execution. A version banner is insufficient.
- [ ] Run python3 tests/test-ci-image-upgrade.py and
  python3 tests/test-ci-isolation-runtime.py; observe intended RED assertions.
- [ ] Implement bounded parsers (512 KiB/4096 records), strict Debian name/version
  arguments, C locale, no shell, and fixed /usr/bin/dpkg comparison with errors
  closed. Use literal test expectations, not outputs computed by the parser.
- [ ] General-upgrade protected names include apt, dpkg, sudo, apparmor, systemd,
  udev, dbus, openssh-server, libc6/libc-bin and package families linux-, grub,
  shim, initramfs-tools, libpam, libnss, libsystemd, snapd, docker, moby,
  containerd, runc, cloud-init and walinuxagent. Also reject candidates owning
  service/init files per bounded installed-package metadata. Unknown ownership
  blocks viability; a denylist is not proof about arbitrary package scripts.
- [ ] Pin Bubblewrap 0.12.0 source archive (126452 bytes), upstream commit
  2a76602a8c71f36c1527cf9fc3417d9149822e0c and SHA-256
  9760d007363e3abba7c747489910f9f82d9fca53ba3bd3282e396fa3c97a3314.
  URL: https://github.com/containers/bubblewrap/releases/download/v0.12.0/bubblewrap-0.12.0.tar.xz.
  These values were read from the official release API; do not replace them at
  execution time with floating metadata or a fetched checksum sidecar.
- [ ] Record the AppArmor reference at immutable upstream revision
  72229df83059480f4e9fb1488624201bdbd61755, path
  profiles/apparmor/profiles/extras/bwrap-userns-restrict. Review origin/license
  notices before adapting/vendoring; stop if incompatible with repository policy.
  The adapted template's digest becomes part of the reviewed runtime lock.
- [ ] Run both suites GREEN; commit this independently testable policy layer.
  Expected: no package, root, policy, native or network operation in the tests.

## Task 2: Provision the fixed private dependency with owned rollback

**Files:** Extend tests/ci_isolation_runtime.py and tests/ci_image_upgrade.py;
create the provision/cleanup portion of tests/ci_isolation_bootstrap.py and
tests/test-ci-isolation-bootstrap.py. Update runtime lock/build fixtures as needed.

**Interfaces:** BuildReceipt(source_sha256, binary_sha256, template_sha256,
architecture, version, build_options); OwnedRuntime(prefix, binary, receipt).

```text
provision_runtime(spec: RuntimeSpec, *, executor, deadline: float) -> OwnedRuntime;
verify_installed_runtime(runtime: OwnedRuntime) -> None;
cleanup_runtime(runtime: OwnedRuntime, *, executor, deadline: float) -> bool.
```

The executor is internal trusted plumbing, not a CLI/configuration argument.

- [ ] Write failing behavioral tests using temporary trees and fake external
  package/build/parser executables, never a generic fake success mock. Verify
  install refusal for symlink/ownership/mode/capability drift, prefix collision,
  version/digest mismatch, build failure and substitution between stages.
  Name the refusal controls test_symlink_candidate_never_installs,
  test_prefix_substitution_before_publish_is_rejected and
  test_failed_upgrade_cannot_continue_to_build. Assert nonzero/blocked outcome,
  unchanged foreign state and absence of the next-stage marker; pair each with
  a valid same-fixture positive control.
- [ ] Exercise ALLOW, SKIP_UNSAFE and BLOCKED with actual orchestration outcomes:
  skipped valid general upgrade still refreshes required safe dependencies;
  malformed/index/signature errors stop. Upgrade failure/partial application
  stops with cleanup, never continues on the changed image. Watch RED.
- [ ] Refresh signed configured indices with failure-on-error behavior; simulate
  /usr/bin/apt-get upgrade and the explicit dependency install under a stable
  package-state snapshot. Require repeat identity immediately before execution.
  Never use dist-upgrade, full-upgrade, autoremove, force-yes or allow-* bypasses.
- [ ] For ALLOW only, execute bounded non-interactive upgrade with --no-remove,
  no hold changes and NEEDRESTART_MODE=l; this limits that tool, not every package
  script. Freeze the authenticated package lists and verified candidate archives
  under an owned private APT cache, then use fixed private-list/cache options and
  --no-download for the actual upgrade. Do not refresh or expand this approved
  cache during execution. Reject concurrent package changes or proposal drift;
  an unavailable unchanged transaction is not viable, not a reason to use live
  mutable resolver state. Cap the general proposal at 500 actions/2 GiB and
  package provisioning at 10 minutes within the unchanged 40-minute job.
  Compare actual package changes against the proposal and revalidate the
  runner/tool/security state. Held or deferred updates remain explicitly reported.
  Never modify policy-rc.d or globally disable service management to force success.
- [ ] Required signed packages start with gcc, meson, ninja-build, pkgconf,
  libcap-dev, libcap2-bin, python3, xz-utils and ca-certificates. Resolve the full
  simulated dependency closure; reject protected/disruptive transitive changes.
  Reuse a compatible installed AppArmor parser rather than silently upgrading
  its base policy package. If required tooling cannot be installed safely, stop.
- [ ] Build verified source as the runner user, with Meson man/SELinux optional
  features explicitly disabled and no network dependency fetching. Validate the
  safe archive before extraction. Install only verified regular data into
  /opt/senior-infra-ci/<source_sha256>/ using fixed trusted root commands.
- [ ] Recheck all root-owned ancestors, no writable substitution, no setuid/gid
  or file capabilities, binary digest and actual version. Do not replace system
  Bubblewrap. Publish the PATH entry only after verification.
- [ ] Establish cleanup ownership before publishing the prefix. Test timeout,
  interruption and every partial-install boundary; reject broad or replaced
  cleanup targets. Rollback of image package updates is VM disposal, not downgrade.
- [ ] Run Tasks 1/2 suites GREEN; commit. Expected: simulated unit controls only;
  real privileged provisioning runs later solely on the approved disposable CI VM.

## Task 3: Diagnose and arm only the owned AppArmor exception

**Files:** Extend tests/ci_isolation_bootstrap.py and its tests; create reviewed
policy template/notices under tests/fixtures/ci-isolation/; finalize template hash
in tests/ci-runtime-lock.json.

**Interfaces:** PolicySnapshot(enforcing, restriction, attachments),
DenialEvidence(executable_identity, time_window, profile, capability, correlated),
OwnedPolicy(parent_name, child_name, path, digest).

```text
diagnose_namespace(runtime, *, executor, deadline) -> DiagnosticResult;
arm_policy(runtime, evidence, *, executor, deadline) -> OwnedPolicy;
cleanup_policy(policy, *, executor, deadline) -> bool.
```

DiagnosticResult has closed status SUPPORTED, POLICY_NEEDED or BLOCKED plus reason.
Add policy_is_needed(snapshot: PolicySnapshot, evidence: DenialEvidence) -> bool
as the pure gate used by arm_policy before any privileged command.

- [ ] Add RED tests for baseline success (no policy mutation), matching denial,
  unrelated/missing evidence, foreign attachment, wrong ABI, broad path, template
  drift, failed load and failed child transition. Verify no fallback command runs.

  ```python
  def test_uncorrelated_denial_cannot_request_policy(self):
      snapshot = PolicySnapshot(True, 1, ())
      evidence = DenialEvidence("verified-binary", (1, 2),
                                "unprivileged_userns", "net_admin", False)
      self.assertFalse(policy_is_needed(snapshot, evidence))
  ```

  The matching correlated control returns True; the real arm_policy tests must
  still prove verified identity, owned installation and actual command ordering.
- [ ] Define exactly two fixed isolated probes: original namespace/capability
  flags and, only after its failure, minimal user+network control; both end in
  /usr/bin/true and have no checkout/operator mounts. No host-network variant.
  Use 15-second per-invocation and 120-second aggregate deadlines, with no retry.
- [ ] Collect bounded security scalars and only denial fields matching this
  verified executable/invocation window. Missing attribution stops the intervention;
  do not infer AppArmor causality from EPERM or sysctl state alone.
- [ ] Render unique parent/child names from a validated digest, attach only to
  the private binary, omit foreign local includes, verify root-owned template
  bytes and use a trusted absolute parser. No generic unconfined profile.
- [ ] Permit setup capabilities only through the reviewed constructor policy;
  stack executed children with capability denial. Preserve global sysctls and
  existing profiles. Retest the exact probe once after loading, then require the
  stronger child proofs from Task 4 before declaring SUPPORTED.
- [ ] Exercise cancellation at load/retest/cleanup, partial parent/child policy
  creation and replaced/unowned paths. Cleanup must unload both owned names only,
  verify removal and preserve all foreign state. Failed cleanup dominates status.
- [ ] Run Tasks 1-3 suites GREEN and commit. Expected: fake external executables
  observe correct real orchestration; no actual policy load on the operator host.

## Task 4: Strengthen portable audit and add real synthetic CI proofs

**Files:** Modify tests/terminal_input_challenge.py and
tests/test-terminal-input-challenge.py; create tests/ci_isolation_probe.py and
tests/test-ci-isolation-probe.py; extend tests/test-offline-terminal-resume-safety.py.

**Interfaces:** Preserve audit_offline_namespace() -> the existing three booleans
or InputProofError(INPUT_PROBE_SCOPE_REJECTED). Add private
validate_privilege_status(text: str) -> None. CI-only
run_isolation_proof(runtime, policy: OwnedPolicy | None, *, deadline: float)
-> IsolationProof with closed booleans namespace/network/mount/process/privilege
and cleanup; never return raw /proc, audit data, process lists or terminal content.

- [ ] Add RED privilege fixtures: missing/duplicate/oversized fields, every
  nonzero capability set, NoNewPrivs absent/zero and valid all-zero control.
  Author implementation choice: require all five capability sets empty for this
  CI baseline; unsupported/nonempty bounding state blocks rather than receiving
  an unproved exception. No JSON receipt or native authorization field is added.

  ```python
  def test_zero_effective_caps_alone_are_not_proof(self):
      with self.assertRaises(ValueError):
          validate_privilege_status("CapEff:\t0000000000000000\n")
  ```

  The private validator raises ValueError on invalid text; the public audit maps
  this to the existing InputProofError reason and never leaks the status text.
- [ ] Implement bounded /proc/self/status validation and preserve current hidden
  directory/interface checks. Keep it portable/fail-closed; no global fcntl or
  AppArmor import that breaks Windows module loading. Static audit has no active
  network traffic and does not repeat connectivity probes on every input check.
- [ ] Create CI-only owned synthetic fixtures: read-only file, writable work file,
  host process marker and frozen host namespace identifiers. Launch a fixed trusted
  child in the requested isolated namespaces, never arbitrary commands or Claude.
- [ ] Assert namespace IDs differ, only loopback is present/up/addressed with
  bounded internal communication, no default/non-loopback route, read-only write
  denial and absence of the known host marker/process. Tests must not enumerate
  unrelated host state or try writing /usr. Compare the intended child policy.
- [ ] Negative controls remove one isolation condition at a time; require proof
  rejection, not just a failing helper. Check useful capability recovery against
  host/original sandbox resources; descendant-local capabilities alone are not
  an escape and nested user namespaces are not globally outlawed by this plan.
- [ ] Prove bounded timeout, child exit/reaping, disposal and proof publication
  order. Any fault rejects before the package suite. Retain only a bounded report
  (maximum 4096 encoded bytes), with existing failure/cleanup precedence.
- [ ] Run new probe tests and existing input/offline safety suites with explicit
  terminal Node/module paths; run the real audit locally with no Claude mount.
  Expected: all GREEN, actual isolation proof and no native/provider execution.
- [ ] Commit the proof/audit changes; do not promote them to native/browser acceptance.

## Task 5: Wire identical guarded bootstrap into the three jobs

**Files:** Modify .github/workflows/ci.yml, release.yml and
scheduled-maintenance.yml; tests/validate-package.sh, tests/test-ci-workflows.py
and tests/validate-ci-workflows.sh. Create tests/test-ci-isolation-wiring.py.

**Interfaces:** Fixed CLI in tests/ci_isolation_bootstrap.py:
--prepare --manifest PATH --report PATH; --verify --manifest PATH --report PATH;
--cleanup --manifest PATH --report PATH. No arbitrary command/path/policy selector.
The manifest is the fixed repository tests/ci-runtime-lock.json, with a reviewed
content identity; reject alternate manifests or path aliases. The workflow-provided
report path is beneath the owned RUNNER_TEMP directory and cannot escape by symlink.
Exit 0 only after required proof (or verified cleanup); all blocked/fault states
nonzero. Bootstrap verification freezes the exact private binary used by the gate.

- [ ] Build RED wiring controls from the real workflow definitions: each full
  job uses the shared fixed interface before terminal provisioning/full validation;
  cleanup is always-run, and wrong order/missing proof/elevated suite is rejected.
  Cover Release/scheduled token grants without dispatching their side-effect jobs.
  In test_full_jobs_execute_the_same_bootstrap_order, execute selected real run
  steps against temporary external fixtures and assert the literal phase sequence
  (prepare, terminal-provision, verify, package-gate, cleanup). In
  test_prepare_failure_runs_only_cleanup, assert (prepare, cleanup), nonzero
  status and no package/release/issue marker. Do not merely grep YAML strings.
- [ ] Wire prepare/verify/cleanup in all three jobs, retaining Ubuntu 24.04 and
  40 minutes. The workflow contract explicitly permits guarded general upgrade,
  not blanket success or unsupported-package fallback. Publish only the verified
  private binary path, and recheck it before real audit/full validation.
- [ ] Restrict the three validation jobs to contents:read and checkout credential
  persistence false. Keep Release publishing and link-audit issue rights only on
  their separate jobs. Never execute their mutation paths as a wiring test.
- [ ] Run new zero-provider suites early in validate-package.sh, including
  dependency/version contracts before the long terminal suites. Keep the existing
  real audit mandatory; no --try option, optional namespace skip or || true path.
- [ ] Run python3 tests/test-ci-isolation-wiring.py,
  python3 tests/test-ci-workflows.py and bash tests/validate-ci-workflows.sh;
  compare GREEN outputs and run all new bootstrap suites. Commit.

## Task 6: Verify, review and deliver without accepting unrelated gates

**Files:** Create docs/architecture/ADR-011-ci-isolation-bootstrap.md; update
docs/architecture/README.md, CHANGELOG.md, tests/validation-notes.md and README.md
only where needed for CI prerequisites. Preserve root/component versions.

- [ ] Run all focused suites, all browser/guard regressions, ShellCheck, Markdown,
  spelling, schema, content and workflow checks. Inspect outputs and explicit
  platform exclusions; never substitute static text tests for the negative proofs.
- [ ] Run the complete immutable package gate on the exact candidate through
  Debian WSL with Node24.17.0 and the existing read-only terminal dependencies.
  Preserve source/archive identity and owned cleanup proof. No actual provider.
- [ ] Obtain one fresh final independent review of the full implementation range,
  including general upgrade, provenance, privileged boundaries and all Review
  Focus cases. Use the established direct-execution method's single TDD fix pass
  for blocking findings; record residual decisions and deferred minors honestly.
- [ ] Add the versioned/indexed ADR and truthful validation notes: general-upgrade
  disposition (applied/up-to-date/skipped/block), exact package/source identities,
  profile/namespace proof, duration, exclusions and cleanup. No raw host data.
- [ ] Push the reviewed branch to PR 58 only after the implementation plan is
  approved for execution. Inspect fresh exact-head CI/Security and the actual
  mandatory audit/full-gate outcome. No manual CI dispatch or native grant reuse.
- [ ] Hosted success requires verified isolation, complete package success and
  successful owned cleanup within 40 minutes. A new platform failure remains
  blocked; stop rather than broadening policy or trying repeated repair variants.
- [ ] Keep native SDK shutdown, provider/browser/twelve-role acceptance, full-PR
  security qualification, merge and release separate. Report the next decision
  rather than marking the definitive TODO complete.

## Execution route, feasibility and self-review

Run ordinary zero-provider Python/Node tests using explicit Debian WSL paths;
never bare bash from PowerShell. Use host Git with command-local safe.directory
and explicit -C for this linked worktree. Do not modify persistent Git settings.
The documented existing runtime paths are validation tools, not production pins.
No installation, upgrade or AppArmor operation is permitted on Windows/WSL for
this CI-only increment. Privileged real tests run only on the approved ephemeral
target CI VM; all local bootstrap/root commands are controlled external fixtures.

Self-review mapping: source identity/upgrade scope -> Task1; installation and
partial-update refusal -> Task2; policy cause/child restrictions/rollback -> Task3;
strong negative isolation and portable compatibility -> Task4; parity/permissions/
early failure -> Task5; ADR/exact-head evidence/independent review -> Task6.
Each Review Focus condition has a failing test in its owning task. Cross-task
types/CLI names are defined above; payloads and CLI remain closed, not extensible
model-directed execution. APT simulation cannot guarantee maintainer behavior;
the conservative skip rule and post-update rejection make that limitation explicit.

Readiness: plan prepared for operator review, not implemented. The operator may
confirm direct execution plus one final review or choose another execution mode.
No jobs, packages, policy, release or native/provider state changed while planning.

## Primary references

- [Approved design](../specs/2026-10-24-ci-isolation-bootstrap-design.md).
- [Official fixed release](https://github.com/containers/bubblewrap/releases/tag/v0.12.0).
- [Release metadata](https://api.github.com/repos/containers/bubblewrap/releases/tags/v0.12.0).
- [Upstream advisory](https://github.com/containers/bubblewrap/security/advisories/GHSA-pxhw-h44j-8pfx).
- [APT semantics](https://manpages.debian.org/bookworm/apt/apt-get.8.en.html).
- [needrestart modes](https://manpages.debian.org/bookworm/needrestart/needrestart.1.en.html).
- [GitHub runner package provisioning](https://docs.github.com/en/actions/how-tos/manage-runners/github-hosted-runners/customize-runners).
