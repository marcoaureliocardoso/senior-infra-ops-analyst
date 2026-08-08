# Stable Toolchain Upgrade Design

## Goal

Modernize the repository-managed CI toolchain and the operator workstation to
the stable releases verified on 2026-08-08, without changing or constraining
Claude Code, Nori Skillsets, or the configured DeepSeek model.

## Scope

The repository change covers GitHub Actions, the Python compatibility lane,
ShellCheck provisioning, workflow policy tests, documentation, and package
version metadata. Operator workstation updates cover Node.js LTS, Python,
PowerShell, Bubblewrap, and GitHub CLI, but remain external observations rather
than package compatibility constraints.

Claude Code, Nori Skillsets, DeepSeek, `model: inherit`, and live AI-provider
configuration are explicitly out of scope.

## Repository Targets

| Component | Target |
|---|---|
| `actions/checkout` | `v7.0.1` commit `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python` | `v7.0.0` commit `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| `github/codeql-action` | `v4` commit `24c7eb380a2dc368f2d129e4c65e51d172983a1e` |
| `actions/upload-artifact` | `v7.0.1` commit `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |
| `softprops/action-gh-release` | `v3.0.2` commit `3d0d9888cb7fd7b750713d6e236d1fcb99157228` |
| `DavidAnson/markdownlint-cli2-action` | `v24.2.0` commit `21c1be1b93ad9ed58fa840aacc3f279cde2a72ff` |
| `streetsidesoftware/cspell-action` | `v8.4.0` commit `de2a73e963e7443969755b648a1008f77033c5b2` |
| Python CI | compatibility matrix `3.12` and `3.14` |
| ShellCheck | `v0.11.0`, downloaded from the official release and checksum-verified |
| Ubuntu runner | retain `ubuntu-24.04` |

All non-local GitHub Actions references use immutable 40-character commit
SHAs with the corresponding release tag in an adjacent comment. Dependabot
continues to update those references and moves from monthly to weekly checks.

## Architecture

Workflow policy remains fail-closed. `tests/validate-ci-workflows.sh` rejects
any external `uses:` reference that is not a full commit SHA and verifies the
expected stable release comments. CodeQL keeps its exact two-language matrix,
but both `init` and `analyze` move to the same immutable v4 commit. Existing
structural mutation tests are updated so they still prove that decoy YAML,
conditional execution, aliases, explicit mappings, and ineffective matrix
forms cannot bypass validation.

The schema job runs independently on Python 3.12 and 3.14. Python 3.12 remains
a compatibility floor during this change; Python 3.14 becomes the current
stable lane. No Python version is declared as a runtime requirement for the
skillset.

ShellCheck is not delegated to whatever version happens to exist in the runner
image. A small installer downloads the official Linux x86_64 release archive,
verifies a fixed SHA-256 digest, installs it under the runner temporary
directory, and reports the version before analysis. The installer itself is
covered by static policy tests and a live version assertion in CI.

## Operator Workstation Targets

After the repository PR is published, update and verify these tools outside the
repository:

- Node.js `24.19.0` LTS; do not move to Node.js 26 Current.
- Python `3.14.7` while retaining Python 3.13 only if another local workload
  requires it.
- PowerShell `7.6.4`.
- Bubblewrap `0.11.2`.
- GitHub CLI `2.97.0`.

These installed versions are evidence in the handoff only. They are not written
into Nori metadata, agent instructions, or model-facing compatibility rules.

## Failure Handling

- A missing or mismatched ShellCheck checksum stops the security job.
- Any mutable external Action reference stops package validation.
- A failed Python matrix member fails the schema job.
- Major Action migrations are not merged unless the ordinary CI, security
  workflow, scheduled artifact path, and release workflow validation all pass.
- If a local package manager cannot safely provide a target release, leave the
  current tool installed and report the blocked component instead of replacing
  it through an untrusted installer.

## Testing and Release

Changes follow RED/GREEN workflow-policy tests before workflow edits. The final
gate is `bash tests/validate-package.sh` on Windows Git Bash or WSL, including
the command-guard suite, coverage threshold, mutation score, Python tests, and
workflow validators. GitHub-hosted CI and security checks must then pass on the
published branch.

This maintenance change increments the package from `0.11.0` to `0.11.1`.
`CHANGELOG.md` must both document the new release and correct the historical
entry that claimed `setup-python` and CodeQL upgrades which were not present in
the corresponding workflows.
