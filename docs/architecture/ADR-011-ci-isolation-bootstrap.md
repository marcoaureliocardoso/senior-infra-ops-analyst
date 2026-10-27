<!-- cspell:ignore AppArmor Bubblewrap libcap NEEDRESTART NoNewPrivs userns setuid setgid RTF autoremove EPERM -->
# ADR-011: Guarded CI image refresh and private isolation runtime
Status: Implemented locally; hosted qualification pending.
Date: 2026-10-25.

## Context
PR 58's hosted full-package job failed while Bubblewrap configured loopback,
before repository tests or native/provider execution. That failure alone does
not identify AppArmor as its cause. The distribution Bubblewrap build is not
accepted merely because a version command succeeds; the selected upstream
baseline is 0.12.0 with a reviewed archive digest, size and source revision.

The operator approved the [design](../superpowers/specs/2026-10-24-ci-isolation-bootstrap-design.md)
and [inline plan](../superpowers/plans/2026-10-24-ci-isolation-bootstrap.md).
This record describes the local implementation, not a completed hosted gate.

## Decision
The CI package job, Release validation job and scheduled full-validation job use
one closed `prepare`, `verify`, `cleanup` interface. They retain Ubuntu 24.04 and
40 minutes, use only `contents: read` and disable checkout credential persistence.
Release publishing and link-audit issue authority stay in their separate jobs.

Prepare refreshes signed configured package indices in an owned private cache.
General upgrades are conditional: bounded, coherent proposals may be applied;
protected/service-bearing/removal/new-install/downgrade/reboot/deferred proposals
are skipped explicitly. Unknown state or a failed/partial transaction blocks.
Required build dependencies are assessed separately. Explicit native holds are
checked independently of APT's count of unrelated pending updates. Suggested,
recommended and autoremove lists are data only, never an action source.
A general candidate that introduces service files only after archive freezing
is also skipped, but only after unchanged proposal/package/hold proof. This is
not a fallback for unknown state or unsafe required dependencies; both still block.

Execution repeats the proposal and package/hold identity after archive freezing,
uses private lists/archives and `--no-download --no-remove`, then compares actual
installed changes and security-tool state. The bounds are 500 actions, 2 GiB of
archives and ten minutes for provisioning. No repository addition, distribution
migration, reboot, removal, downgrade or forced hold change is allowed.
`NEEDRESTART_MODE=l` limits that tool; it does not prove arbitrary maintainer
scripts harmless. A postcondition failure discards the job, not an attempted
package downgrade or a stale-package fallback.

The simulator's official action suffixes are parsed explicitly, never stripped.
Inst may contain zero or more exact relational blocks `[fullname on fullname]`
and then at most one ShortBreaks list. Configuration/removal records allow only that optional list.
Each block has one leading space; ShortBreaks contains zero or more distinct
bounded Debian full names, each followed by one space. Empty `[]` is valid.
Duplicate relational edges are allowed; duplicate ShortBreaks names, foreign
syntax, reversed order, extra lists or invalid names reject. Positional parsing
consumes the whole line without repeated suffix copies. These intermediate
simulation annotations never become selected actions or authority and waive
none of the command-success, complete-Conf/version/count, protected-package,
service, hold, reboot, frozen-proposal or postcondition checks. Schema3 still
reports the first unknown suffix without its content.

The runner builds the exact verified Bubblewrap archive without dependency
fetching. Only the two reviewed COPYING aliases are materialized as regular
license copies; arbitrary archive links and traversal paths reject. A data-only
privileged worker installs an exclusive digest-named prefix under
`/var/lib/senior-infra-ci/`, with private caches under `/var/cache/senior-infra-ci/`.
The hosted image makes `/opt` writable by ordinary users, so it is not a safe
ancestor for this receipt. No global permissions are repaired. System Bubblewrap
is not replaced. Root-owned ancestors,
file identity/digest, mode, absence of setuid/setgid/file capabilities and the
actual runner-invoked version are verified before PATH publication and the gate.

If the fixed isolated baseline fails, exactly one minimal isolated control is
available. A policy intervention requires a matching AppArmor denial from the
verified invocation's observed executable/PIDs and bounded time window. Missing
attribution, incompatible ABI, a foreign attachment or conflicting identity
blocks; EPERM or a restriction scalar alone is insufficient.

The separately licensed, digest-locked ABI-4 template attaches to that private
executable only. Unique owned parent/child names retain the upstream stacked
capability-denying child construction. No generic unconfined exception, foreign
local include, global sysctl change or disable/complain operation is used.
The exact full probe is retested once and the intended child label is measured.

Verify requires distinct user/mount/PID/IPC/UTS/network namespaces, only an up
addressed loopback with bounded internal communication, no usable default or
non-loopback route, denial of writes to an owned read-only bind, a writable
owned work area and hidden known synthetic host markers/process. All five
capability sets must be empty and NoNewPrivs must be one. Useful capability
recovery in the original sandbox must fail; descendant-local user namespaces
are not globally outlawed. The kernel's loopback RTF_REJECT sentinel is not a
usable forwarding route. The existing real offline/helper audit remains mandatory.

Owned child processes are reaped and proof fixtures disposed before proof
publication. A bounded structural aggregate (at most 4096 bytes), root-owned
receipts and nonce/inode ownership bind lifecycle stages. Raw command/audit
streams are not exported or uploaded. Always-run cleanup removes only owned
policy names/files, the private runtime/cache and the owned build workspace.
Failed cleanup is a failed job, not qualified isolation.
The schema3 aggregate includes finite diagnostic phase, stage, error and cleanup
codes. A primary failure is latched before internal or always-run cleanup can
replace the current stage; later cleanup cannot erase it. Only this validated
projection enters stdout, including on prepare failure. Arbitrary
exception text, command arguments/output, URLs, paths, environment and host/run
identifiers are excluded; unknown values map to fixed UNKNOWN codes. Old or
extended report schemas reject. This improves attribution, not runtime authority.
The operator-approved first-rejection diagnostic is nullable aptRejection with
exact keys kind, line and length. Kind is a closed structural enum; line is
one-based including blank lines (1..4096); character length excludes newline
(1..524288). Only APT_SIMULATION_UNRECOGNIZED can carry this detail. No line,
package identity or received-content hash is preserved, and no new form is
accepted. The old schema2 is rejected rather than silently extended.
The shared report path is explicitly bound in each lifecycle step's environment,
where GitHub makes runner context available; no job-level runtime expression or
successful earlier initialization is required by cleanup. The wiring contract
rejects absent, duplicate and divergent bindings and exercises the actual selected
run scripts with no pre-injected report variable.
Policy publication first retains a private inode and atomically records ownership
intent, then exclusively links that inode into the policy directory. Load intent
is recorded before parser execution. Cleanup checks the expected target even when
publication never completed; foreign or unprovable ownership blocks cleanup rather
than deleting data or reporting success. Package subprocesses receive fixed
non-interactive/list-only settings after elevation, not through sudo environment
preservation. Verified archive Architecture/Multi-Arch metadata determines dpkg
identities for new as well as existing packages.

## Trust, consequences and qualification
This trusts reviewed workflow/bootstrap code and the ephemeral hosted image,
including password-free sudo and signed configured package sources. It is not
a privilege boundary against a malicious workflow that can already invoke sudo.
Privileged real provisioning/policy tests are CI-only; local controls use external
synthetic tools and existing non-root namespace support, never host installation.

Conservative refusal can make a runner image unsupported. The approved stop
rule is to report the new platform failure, not broaden policy or retry repair
variants automatically. Generic local input audits do not depend on AppArmor.
The template has its own GPL-2.0 notice/license and is excluded from Nori delivery;
the upstream archive and built binary are not release artifacts.

Root 0.15.0 remains unreleased. The resumed review's browser/guard corrections
advance the browser component to 1.0.4 and command component to 1.2.1; the CI-only
diagnostics grant no additional production/native authority. ADR-010's blocked SDK shutdown boundary,
provider/browser/twelve-role acceptance, formal full-PR security qualification,
merge, release and definitive TODO completion remain separate gates.
See [validation notes](../../tests/validation-notes.md) for exact evidence and exclusions.

## Primary sources
- [APT action and ShortBreaks emission](https://github.com/Debian/apt/blob/2.8.1/apt-pkg/algorithms.cc#L110-L287).
- [Fixed source release](https://github.com/containers/bubblewrap/releases/tag/v0.12.0).
- [Upstream security advisory](https://github.com/containers/bubblewrap/security/advisories/GHSA-pxhw-h44j-8pfx).
- [APT transaction semantics](https://manpages.debian.org/bookworm/apt/apt-get.8.en.html).
- [AppArmor parser add/remove/cache semantics](https://manpages.ubuntu.com/manpages/noble/man8/apparmor_parser.8.html).
- [Immutable policy origin](https://gitlab.com/apparmor/apparmor/-/blob/72229df83059480f4e9fb1488624201bdbd61755/profiles/apparmor/profiles/extras/bwrap-userns-restrict).
- [Hosted-runner variable contract](https://docs.github.com/en/actions/reference/workflows-and-actions/variables).
- [Exact hosted image permission setup](https://github.com/actions/runner-images/blob/ubuntu24/20261012.334/images/ubuntu/scripts/build/configure-system.sh).
- [Native APT simulation messages](https://github.com/Debian/apt/blob/2.7.14/apt-private/private-install.cc).
- [dpkg binary package identities](https://manpages.debian.org/bookworm/dpkg/dpkg-query.1.en.html).
