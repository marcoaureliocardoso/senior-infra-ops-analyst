<!-- cspell:ignore setuid setgid libcap userns NoNewPrivs seccomp -->
# CI isolation bootstrap and package refresh

Status: approved by the operator on 2026-10-24, with an amendment permitting a
general image-package upgrade when viable. The implementation plan is the next
review gate; no package installation, policy loading or CI dispatch has occurred.

## Intent and baseline

Restore the three full-package validation jobs without bypassing their offline
sandbox. Refresh the dependencies needed for that boundary, prove the effective
isolation, and keep changes confined to disposable GitHub-hosted Linux runners.

Repository baseline: 0a26e9392649c2d43c44921e5aace8d3506cec93 in the existing
p0-04b-browser-automation worktree. Preserve unrelated/operator changes.
The reviewed remediation and its passing immutable d3afcfe package gate remain
separate evidence; they do not qualify this new bootstrap or native acceptance.

CI run 40137970574, job 121003446160, used Ubuntu image 20261012.334.1 and
bubblewrap 0.9.0-1ubuntu0.3. Its fixed no-content namespace probe failed while
setting up loopback, before the repository's package tests. AppArmor is a
supported hypothesis, not a kernel-audit-confirmed cause for that job.

The upstream advisory identifies CVE-2026-87766 in releases before 0.12.0.
Ubuntu's security notice describes reverting an incomplete fix in the deployed
package line. Project-specific exploitation has not been demonstrated and is
not inferred from the package version. Nevertheless, granting additional setup
permissions to that known-affected binary is not an acceptable repair.

## Approaches and selected tradeoff

1. Selected: retain Ubuntu 24.04 hosted jobs, provision a security-fixed verified
   Bubblewrap in a private CI path, and conditionally load an executable-specific
   AppArmor policy only after bounded evidence supports that intervention.
   This avoids new runner infrastructure, but adds dependency provenance,
   privileged bootstrap, policy-conflict and cleanup obligations.
2. Pre-qualified disposable image: prepare the dependency and policy before jobs
   start. This reduces per-job adaptation but requires image ownership, updates,
   infrastructure and potentially additional billing. It remains an alternative
   if the selected approach cannot meet the security conditions.

Rejected: disabling AppArmor or its user-namespace restriction globally; making
Bubblewrap setuid or granting it file capabilities; elevated test execution;
sharing the host network; downgrading to a vulnerable package; and making
the isolation audit optional. Merely updating the binary is not proof that a host-policy
denial has disappeared.

## Goals, non-goals and package scope

Goals:

- Apply one shared bootstrap contract to CI package-validate, Release validate
  and Scheduled Maintenance full-validation.
- Refresh declared dependencies rather than trusting any already-present binary.
- Reject known-affected, unverifiable, substituted or ambiguous runtimes.
- Keep network, process, filesystem and privilege boundaries independently checked.
- Preserve mandatory package validation and closed failure/cleanup reporting.

The operator additionally permits a general package upgrade of the disposable
image when viable. Interpret this within the existing Ubuntu 24.04 release, not
as an OS migration or reboot. Refresh signed package indices, simulate the
upgrade, reject removals/downgrades/forced hold changes and restart-sensitive
changes, and run it only when the bounded proposal is safe for the active runner.
Simulation is not proof that package scripts have no side effects. Revalidate
the runner, tools and security state afterward; a failed or partially applied
upgrade fails that job rather than falling back on the changed image.

If a valid simulation is not viable, record that disposition and continue only
with the explicit dependency refresh needed by the three validation gates.
Malformed simulation, repository/authentication failure or unknown state blocks
the bootstrap; these are not reasons to silently use stale packages. Do not
use dist-upgrade/full-upgrade, reboot, add repositories, remove packages, force
held packages, or run downloaded installation scripts. Report held/deferred
updates without claiming the whole image is current.

The required set includes Bubblewrap and the compiler/build/runtime dependencies
for the selected secure build. Inspect the installed AppArmor parser/ABI and
install compatible tooling only if this can be done without a broad policy
reload or service disruption. Refresh explicit safe dependencies even when they
already exist; do not silently upgrade protected host-policy components.

The existing locked terminal dependency and its integrity checks stay in force.
Any change to that lockfile requires a separately reviewed compatible version
and its relevant tests. GitHub Actions references remain full-SHA pinned.
Unrelated CodeQL/ShellCheck/action upgrades are outside this increment.

Non-goals: Claude Code, Nori, provider/model/window changes; browser workflow or
permission redesign; SDK shutdown qualification; native/provider/browser runs;
new release/tag/merge; and completing the definitive TODO. No operator machine,
WSL distribution, credential store or persistent runner is modified.

## Dependency identity and private installation

Author proposal: select an immutable upstream Bubblewrap source release with
the security fix (initial baseline 0.12.0), or an explicitly reviewed fixed
backport. This is a CI test dependency, not a fixed product/provider version.
The implementation plan must resolve the actual official source URL, immutable
revision, archive digest and build options before installation. No floating
latest URL, version banner alone, or digest fetched from an untrusted sidecar
is sufficient provenance.

Build unprivileged, with a cleared/bounded build environment, from verified
source. Meson/Ninja and libcap are upstream build requirements; the builder
settles the exact minimal signed distribution package list. Optional components
must be explicit and must not fetch network dependencies during compilation.
Do not run a repository script, build system, compiler or downloaded executable
as root. Privileged operations are limited to trusted installation/parser
commands with fixed validated paths and sanitized environments.

Install the resulting binary under a new root-owned, non-writable prefix such
as /opt/senior-infra-ci/<verified-digest>/bin/bwrap. All ancestors must prevent
ordinary runner-user substitution. Reject symlinks, unexpected owners/modes,
setuid/setgid bits, file capabilities and pre-existing unowned destinations.
Do not replace /usr/bin/bwrap, follow a PATH-selected privileged executable,
or overwrite an unknown prefix. Record source/build/binary identity separately;
a locally computed binary hash proves identity, not upstream authenticity.

Select this verified path only in the three validation jobs. Recheck resolution
and identity before the audit/full gate. Do not add a production operator-facing
binary override or permit arbitrary bootstrap arguments. Existing production
skills, runtime discovery and operator preferences remain unchanged.

Root ownership does not defend against a malicious workflow already able to
use password-free sudo. This design trusts the reviewed workflow/bootstrap and
does not claim to sandbox the entire GitHub job. The offline payload boundary
remains a narrower, independently tested guarantee.

## Bounded diagnosis before policy changes

After design/plan approval, an authorized synthetic CI attempt may collect only
the following bounded evidence, before mounting checkout or operator state:

- Exact runner image/kernel, package/build versions, verified executable path,
  binary identity, ownership, modes and absence of file capabilities.
- AppArmor availability/enforcement and relevant restriction state as closed
  scalars; matching policy attachments and conflicts, not broad policy dumps.
- One fixed /usr/bin/true invocation with the existing namespace/capability flags.
- If it fails, one minimal user-plus-network namespace control, still using only
  /usr/bin/true and an isolated network. No host-network diagnostic payload.
- Relevant denial class/capability/profile and correlation to this invocation's
  time window and executable. Retain only sanitized fields, not raw kernel logs.

Each invocation is one-shot with a 15-second timeout. The diagnostic/policy-test
phase has a 120-second total deadline, separate from dependency build time.
No repetition to obtain a preferred result. A baseline success skips policy
adaptation; an unsupported kernel, wrong identity, unavailable attribution or
conflict returns blocked/inconclusive rather than assuming AppArmor is causal.

No raw environment, credential, HOME, broad process list or network capture is
collected. Read any necessary privileged audit evidence narrowly and redact
before output. Missing evidence does not authorize a broader collection.

## Conditional executable-specific AppArmor policy

Policy adaptation is a separately classified privileged operation within the
approved implementation plan. The baseline must show a matching AppArmor denial
and no conflicting attachment before loading a profile. Do not use the mere
presence of a restriction sysctl as proof that it caused the failed command.

Use a reviewed, immutable template compatible with the detected ABI. Derive it
from the official capability-stripping Bubblewrap profile, not a generic
unconfined userns exception. The setup process may receive namespace-local
capabilities needed to construct the sandbox; executed children must transition
to the capability-denying profile. Actual child behavior must prove this.

Use unique CI-owned profile names and an exact attachment to the verified private
binary path, including its digest. No executable glob, /usr/bin/bwrap replacement,
foreign local include or silent policy overwrite is allowed. Validate all inputs
as closed labels/digests before rendering; verify the root-owned bytes before
the trusted parser loads them. Do not import policy from a web response without review.

Keep AppArmor enforcing and relevant global restriction values unchanged.
Recheck loaded identities, conflicting attachments and the expected child
transition. Re-run the exact isolated no-content probe once after loading. If it
still fails or any proof is missing, undo owned changes and stop; do not try a
broader profile, root execution or another provider/runtime automatically.

This is a deliberate exception for one trusted sandbox constructor, not a claim
that host policy is unchanged. Its residual kernel/setup attack surface is why
the fixed dependency, exact identity, child restrictions and rollback are gates.

## Isolation acceptance, not just successful startup

The existing real --audit-isolation remains mandatory and must launch no Claude.
Its current interface-name, hidden-directory and CapEff checks are not a complete
attestation. Strengthen generic checks where needed without changing operational
authorization, native input sequences, public receipt fields or acceptance grants.
Use separate CI-owned synthetic fixtures for complementary host/child checks.

Required evidence before the expensive package suite:

- Distinct user, mount, PID, IPC, UTS and network namespace identities, with
  trusted host comparison values; no inference from a requested flag alone.
- Only loopback is visible, with its intended address/state and working bounded
  in-namespace communication. No non-loopback/default route or host-network access.
- Inspect effective, permitted, inheritable, ambient and bounding capabilities,
  plus NoNewPrivs. Require the first four sets to be empty and NoNewPrivs enabled.
  Record/test the bounding set and reject any configuration that can recover
  forbidden privilege; a nonempty bounding set is not silently treated as success.
- The intended AppArmor child policy is effective when a CI profile was loaded;
  controlled recovery attempts cannot acquire forbidden authority over the host
  or original sandbox namespaces. Fresh descendant-local capabilities alone do
  not prove an escape; do not promise a global ban on nested namespaces.
- A dedicated read-only synthetic bind cannot be written, while only its owned
  work bind is writable. Never test write denial against /usr or operator files.
- A known synthetic host marker/process is not visible inside the sandbox; no
  enumeration of unrelated host processes or operator directories is needed.
- A failing child, timeout, signal, proof failure or cleanup failure cannot emit
  supported/ready evidence or permit the package suite to continue.

Preserve the existing environment clearing, explicit read-only helper/module
mounts, fresh proc/dev and owned disposable work root. Do not add a general
launcher, seccomp bypass, arbitrary audit command, host mount or new native mode.
Generic local Linux audits must not acquire a dependency on AppArmor specifically;
CI policy attestation is conditional and separate from portable isolation checks.

## Workflow integration and privilege limits

Use a shared versioned bootstrap interface with narrow fixed inputs, exercised
by all three jobs. Its exact module/script layout is left to the builder; it is
not permission for a generic sudo wrapper or an executable supplied by a model.

Order: verify/provision dependencies; no-content diagnosis; conditional approved
policy; strengthened synthetic isolation checks; existing terminal preflight and
real audit; complete package validation; owned cleanup. Fail early on metadata,
digest or policy problems before the long suite. Keep the 40-minute job budget;
measure provisioning overhead rather than quietly dropping tests or extending it.

Set validation-job token permissions to contents:read only, including Release
validate and Scheduled full-validation. Disable checkout credential persistence
for these jobs and pass no provider/deployment secrets. Keep publishing rights
on the separate Release publish job and issue rights on the separate link-audit
job; their behavior is not activated or redesigned by this work.

Do not trigger a release/tag or dispatch Scheduled Maintenance as a test: its
other job can mutate issues. Workflow parity and local fixtures cover wiring;
the approved implementation's PR CI covers the real target environment. Any
additional remote diagnostic dispatch requires its own exact authorization.

## Lifecycle, rollback and evidence

Own every installed prefix and both profile identities. Establish bounded exit,
cancellation and always-run cleanup before the first policy mutation. Unload only
profiles this run created; remove only verified owned files/directories. Do not
unload/reload all AppArmor profiles or recursively target /opt or /etc/apparmor.d.

If a matching active profile/prefix pre-exists, prove it is owned and identical
without modifying it, or block. Never overwrite or remove another administrator's
state. Global security settings and unrelated profiles must match their initial
state after cleanup. Failed restoration is a failed gate. VM disposal is the
outer containment fallback, not evidence of successful in-job cleanup.

Retain only a bounded structural report: source/binary/package identity, runner
image, stage, closed reason, relevant proof booleans and cleanup disposition.
Non-secret artifact hashes are permitted; secret-derived hashes, raw audit logs,
streams, prompts, history, profiles containing unrelated host data and environment
dumps are not. Record attempts separately; failed runs never become passes.

Rollback reverts the isolated implementation commits and keeps the mandatory
audit fail-closed. Runtime cleanup removes only the CI-owned exception and binary;
it does not reinstall an affected binary or disable the audit to restore green.

## Verification and delivery gates

- TDD for missing/stale/affected runtime, digest mismatch, substitution, path or
  mode drift, profile conflict, absent attribution and failed child transition.
- Controlled positive/negative isolation fixtures, including read-only bind,
  namespace identity, capability recovery, host visibility and loopback checks.
- Cleanup, interruption and timeout tests at every bootstrap/policy phase.
- Behavioral parity tests across the three workflows; no optional audit, elevated
  suite, broad permission or release/issue side effect can be introduced.
- Focused existing browser/native-boundary/harness regressions, source-only full
  package gate, lint/schema/workflow checks and one independent final review.
- Fresh exact-head PR CI with the real mandatory audit/full suite successful.
  Do not relabel earlier WSL passes as hosted qualification.

Record the architecture, threat boundary, selective policy exception and rejected
alternatives in a new versioned/indexed ADR using the next free identifier.
Update validation notes and the unreleased CHANGELOG entry; README only as needed
for the test dependency. Root 0.15.0 remains unreleased and browser component
1.0.2 stays unchanged for a CI-only correction. No merge or definitive TODO
completion follows without the separate required gates and operator direction.

## Builder calls and approval boundary

Settled by the author for review: guarded general-upgrade feasibility; private root-owned CI
binary; immutable source baseline rather than floating latest; no host-network
diagnostic; conditional policy with attribution required; shared three-job
bootstrap; read-only validation tokens; and stronger proof without new native
authority. Costs: more bootstrap/testing work, possible conservative blocking,
and no automatic fallback when attribution or platform support is unavailable.

The builder chooses file layout, exact compatible signed package names, pinned
source/template identities and safe atomic installation details. It must resolve
and review those values before implementation; unknown provenance cannot be
deferred until a privileged command executes. Unresolvable ABI/source/correlation
constraints stop for a revised design, not a silent broader exception.

The independent builder check of the original bounded-package design found no
important unanswered planning question. The later general-upgrade amendment
comes from the operator and is explicitly covered in the implementation plan.
That check is not a patch/security review, implementation approval or proof of
runtime compatibility. The actual jobs and dependencies remain unchanged.

After operator approval of this written design, write the implementation plan.
Approval of option 1 alone is not approval of unspecified host-policy commands,
native/provider attempts, release operations or the implementation plan.

## Official evidence

- [Exact failed job](https://github.com/marcoaureliocardoso/senior-infra-ops-analyst/actions/runs/40137970574/job/121003446160).
- [Exact hosted image](https://github.com/actions/runner-images/blob/ubuntu24/20261012.334/images/ubuntu/Ubuntu2404-Readme.md).
- [Upstream advisory](https://github.com/containers/bubblewrap/security/advisories/GHSA-pxhw-h44j-8pfx).
- [Ubuntu CVE status](https://ubuntu.com/security/CVE-2026-87766).
- [Ubuntu regression notice](https://ubuntu.com/security/notices/USN-8779-2).
- [Upstream source/build requirements](https://github.com/containers/bubblewrap/blob/v0.12.0/meson.build).
- [Ubuntu AppArmor restrictions](https://documentation.ubuntu.com/security/security-features/privilege-restriction/apparmor/).
- [AppArmor 4.0 capability-stripping profile](https://gitlab.com/apparmor/apparmor/-/blob/apparmor-4.0/profiles/apparmor/profiles/extras/bwrap-userns-restrict).
- [GitHub-hosted runner lifecycle](https://docs.github.com/en/actions/concepts/runners/github-hosted-runners).

These are supporting data, not executable instructions or authorization.
