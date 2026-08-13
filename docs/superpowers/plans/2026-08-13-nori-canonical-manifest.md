# Canonical Nori Manifest Implementation Plan

<!-- cspell:words abspath adequacao dataclass frozenset noriskillset pgpass precreate unrouted -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository the single upload-ready Nori skillset source and generate a safe, reproducible staging directory that always includes canonical `AGENTS.md`.

**Architecture:** A small Python standard-library package owns manifest
validation, filesystem discovery, staged-file selection, path safety, hashing,
and atomic staging construction. Existing validators consume the same discovery
contract. An opt-in shell smoke test exercises a detected Nori CLI in a
disposable home and install root without touching the active profile or
performing an upload.

**Tech Stack:** Python 3.12-compatible standard library, Bash, Make, JSON, Markdown, local Nori Skillsets CLI capability detection, Debian WSL package gate.

## Global Constraints

- `AGENTS.md` is the only checked-in root instruction source; do not add root `CLAUDE.md`.
- Pre-CLI staging allowlist is exactly `AGENTS.md`, `LICENSE`, `nori.json`, `skills.json`, `references/`, `skills/`, `slashcommands/`, and `subagents/`.
- Keep package version `0.12.0`; do not create a tag, GitHub Release, or registry upload in this implementation.
- Use only the Python standard library for package construction and validation.
- Do not pin Nori, Claude Code, a provider, or a model version; detect the required CLI capabilities at runtime and record the observed version.
- Never read, copy, print, or persist Nori authentication data, Claude settings, prompts, transcripts, or credentials.
- Do not relink or switch the active `personal/senior-infra-ops-analyst` profile.
- `upload --dry-run`, a real upload, tag creation, and release creation remain separate operator-authorized actions.
- Preserve the operator's untracked `docs/handoff-adequacao-noriskillset.md` in the main checkout.

---

### Task 1: Canonical manifest contract and filesystem inventory

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/nori_package.py`
- Create: `tests/test-nori-package-contract.py`
- Modify: `tests/validate-schema.py:1-205`
- Modify: `tests/test-schema-validation.py:1-116`
- Modify: `nori.json:1-246`

**Interfaces:**
- Produces: `load_json(path: Path) -> object`
- Produces: `discover_skill_ids(root: Path) -> tuple[str, ...]`
- Produces: `discover_reference_paths(root: Path) -> tuple[str, ...]`
- Produces: `discover_subagent_ids(root: Path) -> tuple[str, ...]`
- Produces: `validate_manifest(root: Path) -> list[str]`
- Produces: `validate_repository_inventory(root: Path) -> list[str]`
- Consumes: root `nori.json`, `.nori-version`, `skills.json`, and filesystem package assets.

- [ ] **Step 1: Add failing canonical-manifest tests**

Create mutation tests that copy the repository to a temporary sandbox and assert these exact outcomes:

```python
def test_canonical_manifest_has_only_selected_fields(self):
    manifest = json.loads((self.sandbox / "nori.json").read_text())
    self.assertEqual(
        set(manifest),
        {
            "name", "version", "description", "author", "license",
            "repository", "keywords", "dependencies",
        },
    )

def test_legacy_tags_are_rejected(self):
    manifest = self.read_manifest()
    manifest["tags"] = manifest.pop("keywords")
    self.write_manifest(manifest)
    result = self.run_validator()
    self.assertIn("legacy field is not allowed: tags", result.stdout)

def test_array_skill_dependencies_are_rejected(self):
    manifest = self.read_manifest()
    manifest["dependencies"]["skills"] = ["read-the-damn-docs"]
    self.write_manifest(manifest)
    result = self.run_validator()
    self.assertIn("dependencies.skills must be an object", result.stdout)

def test_skill_catalog_is_discovered_without_manifest_skills(self):
    result = self.run_validator()
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    self.assertIn("context-continuity", discover_skill_ids(self.sandbox))
```

Also cover duplicate/empty/non-string keywords, an absent or wrong dependency version, unexpected top-level fields, missing `AGENTS.md`, empty `AGENTS.md`, missing skill metadata, and both directions of `skills.json` drift.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
python3 tests/test-nori-package-contract.py
python3 tests/test-schema-validation.py
```

Expected: failures proving that the current validator requires `type`, `skills`, `references`, and `subagents`, accepts `tags`, and reads inventory from `nori.json`.

- [ ] **Step 3: Implement shared discovery and manifest validation**

Implement deterministic sorted discovery in `scripts/nori_package.py`:

```python
CANONICAL_MANIFEST_FIELDS = frozenset({
    "name", "version", "description", "author", "license",
    "repository", "keywords", "dependencies",
})

def discover_skill_ids(root: Path) -> tuple[str, ...]:
    return tuple(sorted(
        path.parent.name
        for path in (root / "skills").glob("*/SKILL.md")
        if path.is_file()
    ))

def discover_reference_paths(root: Path) -> tuple[str, ...]:
    return tuple(sorted(
        path.relative_to(root).as_posix()
        for path in (root / "references").glob("*.md")
        if path.is_file()
    ))

def discover_subagent_ids(root: Path) -> tuple[str, ...]:
    return tuple(sorted(
        path.stem
        for path in (root / "subagents").glob("*.md")
        if path.is_file()
    ))
```

`validate_manifest()` must require the exact selected field set, valid `X.Y.Z`, unique non-empty string keywords, and this dependency:

```json
"dependencies": {
  "skills": {
    "read-the-damn-docs": "latest"
  }
}
```

`validate_repository_inventory()` must cross-check discovered skills with `skills.json`, validate each `skills/<id>/nori.json`, and keep `.nori-version` equal to the root version without using removed root inventories.

- [ ] **Step 4: Migrate the canonical source manifest**

Rewrite root `nori.json` to:

- retain `name`, `version`, `description`, `author`, `license`, and `repository`;
- rename the existing 102 `tags` values to `keywords` byte-for-byte and in the same order;
- replace the dependency array with the exact object above;
- remove `type`, `skills`, `references`, `subagents`, `homepage`, and `bugs`.

Do not modify per-skill `nori.json` files; their `type: skill` contract remains unchanged.

- [ ] **Step 5: Route the existing schema validator through the shared contract**

Replace root-manifest inventory logic in `tests/validate-schema.py` with:

```python
sys.path.insert(0, str(ROOT))
from scripts.nori_package import validate_manifest, validate_repository_inventory

for message in validate_manifest(ROOT):
    err(message)
for message in validate_repository_inventory(ROOT):
    err(message)
```

Keep `profile.json`, `.nori-version`, per-skill metadata, and placeholder checks that remain repository release controls. Remove only checks whose source was a deleted root inventory field.

Update `tests/test-schema-validation.py` to reject reintroduced root `type` instead of requiring it, preserve version synchronization tests, and assert `context-continuity` through filesystem discovery plus `skills.json`.

- [ ] **Step 6: Run focused GREEN validation**

Run:

```bash
python3 tests/test-nori-package-contract.py
python3 tests/test-schema-validation.py
python3 tests/validate-schema.py
python3 -m json.tool nori.json >/dev/null
```

Expected: all tests pass and the validator prints `schema validation passed`.

- [ ] **Step 7: Commit the manifest contract**

```bash
git add nori.json scripts/__init__.py scripts/nori_package.py \
  tests/validate-schema.py tests/test-schema-validation.py \
  tests/test-nori-package-contract.py
git commit -m "refactor: align the canonical Nori manifest"
```

---

### Task 2: Content validation from filesystem sources

**Files:**
- Create: `tests/test-content-discovery.py`
- Modify: `tests/validate-content.py:1-535`
- Reuse: `scripts/nori_package.py`

**Interfaces:**
- Consumes: `discover_skill_ids`, `discover_reference_paths`, and `discover_subagent_ids` from Task 1.
- Produces: content validation independent of removed root manifest inventories.

- [ ] **Step 1: Add failing discovery mutation tests**

Add a temporary-repository test harness and these cases:

```python
def test_unknown_preloaded_skill_is_rejected_from_filesystem_catalog(self):
    self.replace_in_subagent("skills:\n  - command-driven-operations",
                             "skills:\n  - absent-skill")
    result = self.run_content_validator()
    self.assertIn("preloads skills absent from packaged skills", result.stdout)

def test_reference_file_not_listed_by_agents_is_rejected(self):
    (self.sandbox / "references" / "unrouted-reference.md").write_text("# X\n")
    result = self.run_content_validator()
    self.assertIn("AGENTS.md missing required reference", result.stdout)

def test_slash_command_unknown_subagent_is_rejected(self):
    self.replace_in_command("diagnostic-operator", "absent-operator")
    result = self.run_content_validator()
    self.assertIn("references unknown subagent", result.stdout)
```

Also prove that deleting a discovered subagent, duplicating a subagent
frontmatter name, or adding a malformed skill fails without any root manifest
inventory.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
python3 tests/test-content-discovery.py
python3 tests/validate-content.py
```

Expected: mutation tests expose reads of `manifest.get('skills')`,
`manifest.get('references')`, and `manifest.get('subagents')`.

- [ ] **Step 3: Replace manifest-derived collections**

At the top of `tests/validate-content.py`, import the shared discovery helpers
and set:

```python
skills = discover_skill_ids(root)
refs = discover_reference_paths(root)
subagent_ids = set(discover_subagent_ids(root))
```

Iterate subagent files by discovered ID and derive name and description from
their existing frontmatter. Keep all runtime-control, hook, tool, model,
primary-skill, minimum-content, and slash-command routing checks. Change error
messages that mention `nori.json` to name the packaged filesystem catalog.

- [ ] **Step 4: Run focused GREEN validation**

Run:

```bash
python3 tests/test-content-discovery.py
python3 tests/validate-content.py
python3 tests/test-subagent-frontmatter.py
python3 tests/test-installed-subagents.py
```

Expected: all pass with no root inventory fields.

- [ ] **Step 5: Commit filesystem-backed content validation**

```bash
git add tests/validate-content.py tests/test-content-discovery.py
git commit -m "test: derive package content from filesystem sources"
```

---

### Task 3: Safe reproducible staging builder

**Files:**
- Modify: `scripts/nori_package.py`
- Create: `scripts/build_nori_staging.py`
- Create: `tests/test-nori-staging.py`

**Interfaces:**
- Produces: `InventoryEntry(path: str, size: int, sha256: str)` frozen dataclass.
- Produces: `validate_destination(source: Path, destination: Path) -> list[str]`.
- Produces: `validate_staging(source: Path, destination: Path) -> tuple[list[str], tuple[InventoryEntry, ...]]`.
- Produces: `build_staging(source: Path, destination: Path, replace: bool) -> tuple[InventoryEntry, ...]`.
- CLI: `python3 scripts/build_nori_staging.py --source PATH --destination PATH [--replace] [--check] [--json]`.

- [ ] **Step 1: Add failing staging safety tests**

Cover the exact allowlist, deterministic path ordering and hashes, `.env` and
private-key exclusion, unexpected destination files, missing `AGENTS.md`, root
`CLAUDE.md`, source/staging byte drift, destination equal to or containing the
source, destination at a filesystem or home root, and safe replacement only
when the existing tree itself satisfies the managed package boundary.

Add a platform-conditional symlink/reparse test:

```python
def test_symlink_inside_allowed_tree_is_rejected(self):
    link = self.source / "references" / "escape.md"
    try:
        link.symlink_to(self.outside / "secret.md")
    except OSError:
        self.skipTest("symlink creation is unavailable")
    result = self.run_builder()
    self.assertIn("symlink or reparse point", result.stderr)
```

- [ ] **Step 2: Run the staging suite and verify RED**

Run:

```bash
python3 tests/test-nori-staging.py
```

Expected: import or missing-command failures because the staging builder does
not exist.

- [ ] **Step 3: Implement the package boundary**

Define:

```python
STAGING_ROOT_FILES = ("AGENTS.md", "LICENSE", "nori.json", "skills.json")
STAGING_ROOT_DIRS = ("references", "skills", "slashcommands", "subagents")
SENSITIVE_NAMES = (
    ".env", ".pem", ".key", ".p12", ".pfx", ".kubeconfig",
    ".token", ".pgpass", "credentials", "service-account",
)
```

Walk without following links. Reject symlinks/reparse points and sensitive path
fragments anywhere under allowed directories. Validate the source contract
before copying. Copy into a temporary sibling, validate every relative path,
size, and SHA-256, then rename it into place.

Without `--replace`, an existing destination is an error. With `--replace`,
preserve the unresolved caller path and require complete path/size/SHA-256
identity with the current canonical source. Atomically move the directory
aside, revalidate that moved object, install the new tree, and restore the old
tree if validation or installation fails. This closes the scan-to-delete race
and refuses stale, partial, special, linked, or unexpected content. Never
accept `/`, a drive root, home, workspace root, repository root, or an ancestor
of the source as destination.

`--check-source` is a read-only validation of the actual source projection and
is part of the package gate. `--check` is read-only and compares an existing destination with the source.
`--json` prints the sorted inventory to stdout. The inventory is not written
inside staging.

- [ ] **Step 4: Run focused GREEN staging tests**

Run:

```bash
python3 tests/test-nori-staging.py
python3 scripts/build_nori_staging.py --help
```

Expected: all tests pass and help lists all five options.

- [ ] **Step 5: Build and check a disposable real staging tree**

Run from the worktree:

```bash
stage_dir="$(mktemp -d)/senior-infra-ops-analyst"
python3 scripts/build_nori_staging.py --source . --destination "$stage_dir" --json
python3 scripts/build_nori_staging.py --source . --destination "$stage_dir" --check
```

Expected: exactly the allowlist is present, `AGENTS.md` is included, hashes
match, and `--check` exits zero without changing timestamps or content.

- [ ] **Step 6: Commit the staging builder**

```bash
git add scripts/nori_package.py scripts/build_nori_staging.py \
  tests/test-nori-staging.py
git commit -m "feat: build reproducible Nori upload staging"
```

---

### Task 4: Package and CI entrypoint integration

**Files:**
- Create: `scripts/build_nori_archive.py`
- Create: `tests/test-nori-archive.py`
- Modify: `Makefile:1-11`
- Modify: `tests/validate-package.sh:1-67`
- Modify: `tests/test-ci-workflows.py`

**Interfaces:**
- Produces: `make stage STAGING_DIR=<absolute-path>`.
- Produces: `make package STAGING_DIR=<absolute-path>` creating a zip from the staged allowlist only.
- Consumes: tests and CLI from Tasks 1-3.

- [ ] **Step 1: Add failing entrypoint policy tests**

Extend `tests/test-ci-workflows.py` to require `tests/validate-package.sh` to
invoke, in order:

```text
python3 tests/test-nori-package-contract.py
python3 tests/test-content-discovery.py
python3 tests/test-nori-staging.py
python3 tests/test-nori-archive.py
python3 scripts/build_nori_staging.py --source . --check-source
python3 tests/validate-schema.py
```

Add Makefile assertions that `package` depends on `stage`, uses
`scripts/build_nori_staging.py`, and never archives the repository directory.

- [ ] **Step 2: Run the policy test and verify RED**

Run:

```bash
python3 tests/test-ci-workflows.py
```

Expected: failure naming missing Nori package tests and the unsafe legacy zip
source.

- [ ] **Step 3: Wire deterministic validation and packaging**

Add the three new Python suites before `validate-schema.py` in
`tests/validate-package.sh`.

Replace the Makefile package flow with:

<!-- markdownlint-disable MD010 -->

```make
STAGING_DIR ?= ../senior-infra-ops-analyst-nori-staging
PACKAGE_ZIP ?= ../senior-infra-ops-analyst-skillset-v$(shell python3 -c 'import json; print(json.load(open("nori.json"))["version"])').zip

stage: validate-local
	python3 scripts/build_nori_staging.py --source . --destination "$(STAGING_DIR)" --replace

package: stage
	python3 scripts/build_nori_archive.py --source . --staging "$(STAGING_DIR)" --output "$(abspath $(PACKAGE_ZIP))"
```

<!-- markdownlint-enable MD010 -->

Update `.PHONY` and `clean` without making `clean` delete an arbitrary
operator-supplied `STAGING_DIR`. Generated staging cleanup remains an explicit,
validated builder operation.

- [ ] **Step 4: Run GREEN entrypoint tests**

Run:

```bash
python3 tests/test-ci-workflows.py
bash -n tests/validate-package.sh
make -n stage STAGING_DIR=/tmp/senior-infra-ops-analyst-stage
make -n package STAGING_DIR=/tmp/senior-infra-ops-analyst-stage
```

Expected: tests pass, shell syntax is valid, and dry output shows staging as the
only zip input.

- [ ] **Step 5: Commit entrypoint integration**

```bash
git add Makefile tests/validate-package.sh tests/test-ci-workflows.py
git commit -m "build: package only the canonical Nori staging tree"
```

---

### Task 5: Isolated real Nori installation smoke

**Files:**
- Create: `tests/live-nori-package-smoke.sh`
- Create: `tests/test-live-nori-package-safety.py`
- Modify: `tests/validate-package.sh`
- Modify: `tests/validation-notes.md`

**Interfaces:**
- CLI: `bash tests/live-nori-package-smoke.sh --self-test`.
- CLI: `bash tests/live-nori-package-smoke.sh --run-live --nori-bin ABSOLUTE_PATH`.
- Consumes: staging builder and a capability-compatible detected Nori CLI.
- Produces: sanitized stdout containing CLI version, discovered counts, managed-block count, canonical-content result, and cleanup result only.

- [ ] **Step 1: Add failing safety tests**

Require the live runner to:

- reject relative or missing `--nori-bin` paths;
- require `--run-live` before executing the real CLI;
- create and export disposable `HOME`, `XDG_CONFIG_HOME`, and install roots;
- pass only the bare name `senior-infra-ops-analyst-package-smoke` to `link
  --name`, then address the resulting temporary profile by its canonical
  `personal/senior-infra-ops-analyst-package-smoke` identity;
- reject `login`, `logout`, `upload`, `upload-skill`, `--force`, and the active
  profile name as standalone command arguments;
- install for `claude-code` only inside the disposable home;
- clean all temporary paths through a trap;
- emit no file content, environment dump, token, credential, or auth path.

- [ ] **Step 2: Run the safety test and verify RED**

Run:

```bash
python3 tests/test-live-nori-package-safety.py
```

Expected: failure because the live runner does not exist.

- [ ] **Step 3: Implement capability detection and isolated install**

The live runner must inspect `--version`, top-level `--help`, `link --help`, and
`switch --help`. It proceeds only when the observed CLI exposes `link --name`,
`switch --agent`, global `--install-dir`, and `claude-code`; it does not compare
against a fixed version number.

For `--run-live`:

1. create a temporary root;
2. set `HOME` and `XDG_CONFIG_HOME` beneath it;
3. build staging beneath it;
4. precreate the expected Claude instructions destination with a non-secret
   `operator-content-sentinel` outside any managed block;
5. link the staged directory with the temporary profile name;
6. switch that temporary profile for `claude-code` using the disposable home as
   install root;
7. locate exactly one installed `CLAUDE.md` beneath the disposable root;
8. require one begin marker and one end marker;
9. require normalized staged `AGENTS.md` as the exact prefix of managed content;
10. require one generated `# Nori Skills System` section after the source;
11. require the unmanaged sentinel outside the managed block;
12. remove the temporary root and report `cleanup=passed`.

`--self-test` uses a generated fake CLI that implements only the required help,
link, and switch responses, proving argument and environment handling without a
real Nori installation.

- [ ] **Step 4: Add deterministic gates**

Append to `tests/validate-package.sh`:

```bash
python3 tests/test-live-nori-package-safety.py
bash -n tests/live-nori-package-smoke.sh
bash tests/live-nori-package-smoke.sh --self-test
```

- [ ] **Step 5: Run deterministic GREEN tests**

Run:

```bash
python3 tests/test-live-nori-package-safety.py
bash -n tests/live-nori-package-smoke.sh
bash tests/live-nori-package-smoke.sh --self-test
```

Expected: safety tests and self-test pass without reading the real Nori home.

- [ ] **Step 6: Run the real local isolated smoke**

On the approved Debian WSL route, run:

```bash
bash tests/live-nori-package-smoke.sh \
  --run-live \
  --nori-bin /home/marco/.nvm/versions/node/v24.19.0/bin/nori-skillsets
```

Expected: capability checks pass, the installed managed block contains the
canonical source plus generated skills, the sentinel survives, and cleanup
passes. Record the observed CLI version and sanitized result in
`tests/validation-notes.md`; do not make that path a package compatibility pin.

- [ ] **Step 7: Commit isolated integration validation**

```bash
git add tests/live-nori-package-smoke.sh \
  tests/test-live-nori-package-safety.py tests/validate-package.sh \
  tests/validation-notes.md
git commit -m "test: verify isolated Nori instruction installation"
```

---

### Task 6: Architecture and operator documentation

**Files:**
- Create: `docs/architecture/ADR-006-canonical-nori-package.md`
- Modify: `docs/architecture/README.md:1-12`
- Modify: `tests/test-architecture-docs.py:1-94`
- Modify: `README.md:350-365`
- Modify: `docs.md:88-113,220-230`
- Modify: `CONTRIBUTING.md:12-24`
- Modify: `CHANGELOG.md:8-26`

**Interfaces:**
- Consumes: finalized commands and behavior from Tasks 1-5.
- Produces: versioned decision, operator staging procedure, rollback, and validation contract.

- [ ] **Step 1: Add a failing ADR regression**

Extend `tests/test-architecture-docs.py` to require index entry `ADR-006` and
these fragments in the record:

```python
REQUIRED_ADR_006 = (
    "AGENTS.md",
    "Canonical manifest",
    "Filesystem discovery",
    "Staging allowlist",
    "Symlinks and reparse points",
    "Isolated Nori validation",
    "External side effects",
    "Rollback",
)
```

- [ ] **Step 2: Run the ADR test and verify RED**

Run:

```bash
python3 tests/test-architecture-docs.py
```

Expected: failure naming the missing ADR-006 record or index entry.

- [ ] **Step 3: Write and index ADR-006**

Document the accepted decision, exact manifest fields, filesystem-derived
inventories, allowlist, destination safety, Nori normalization boundary,
isolated install test, consequences, external-side-effect gates, and rollback.
Set status to `Accepted` only because implementation and tests in prior tasks
already enforce the decision.

- [ ] **Step 4: Update operator and contributor documentation**

Add to `README.md` a short `Building Nori upload staging` section containing:

```bash
python3 scripts/build_nori_staging.py \
  --source . \
  --destination /absolute/path/to/staging
python3 scripts/build_nori_staging.py \
  --source . \
  --destination /absolute/path/to/staging \
  --check
```

Explain that staging is disposable, root `CLAUDE.md` is not a source artifact,
`--replace` requires exact current inventory and recoverable move-aside
replacement, fresh archives cannot retain stale entries, and upload commands
are not run by the builder.

Update `docs.md` so `nori.json` is described as registry identity/search/
dependency metadata, while skills, references, commands, and subagents are
filesystem-discovered. Add `scripts/` to the repository tree.

Update `CONTRIBUTING.md` with focused package-contract and staging tests.

Under the existing unreleased `0.12.0` heading in `CHANGELOG.md`, change
`updated through 2026-08-12` to `updated through 2026-08-13` and add one bullet
covering the canonical manifest, mandatory `AGENTS.md`, reproducible allowlist,
and isolated Nori installation proof. Do not create a new version heading.

- [ ] **Step 5: Run documentation GREEN tests**

Run:

```bash
python3 tests/test-architecture-docs.py
python3 tests/validate-content.py
python3 tests/test-release-history.py
git diff --check
```

Expected: all pass.

- [ ] **Step 6: Commit architecture and documentation**

```bash
git add docs/architecture/ADR-006-canonical-nori-package.md \
  docs/architecture/README.md tests/test-architecture-docs.py \
  README.md docs.md CONTRIBUTING.md CHANGELOG.md
git commit -m "docs: define the canonical Nori package boundary"
```

---

### Task 7: Complete validation and independent review

**Files:**
- Modify only if verification or review identifies a concrete defect.
- Preserve: `docs/handoff-adequacao-noriskillset.md` in the main checkout.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: final test evidence and a reviewable branch; no upload, tag, release, or merge.

- [ ] **Step 1: Run all focused suites from a clean worktree**

```bash
python3 tests/test-nori-package-contract.py
python3 tests/test-content-discovery.py
python3 tests/test-nori-staging.py
python3 tests/test-nori-archive.py
python3 tests/test-live-nori-package-safety.py
python3 tests/test-schema-validation.py
python3 tests/test-architecture-docs.py
python3 tests/validate-schema.py
python3 tests/validate-content.py
python3 tests/test-release-history.py
python3 tests/test-ci-workflows.py
git diff --check
```

Expected: all pass.

- [ ] **Step 2: Run the complete Debian WSL gate**

From the Windows host, use the proven Debian route and compatible Node runtime:

```powershell
wsl.exe -d Debian -- bash -lc "cd /mnt/c/projects/senior-infra-ops-analyst/senior-infra-ops-analyst/.worktrees/nori-canonical-manifest && export PATH=/home/marco/.local/opt/node-v24.17.0-linux-x64/bin:\$PATH && bash tests/validate-package.sh"
```

Expected final line: `package validation passed`.

- [ ] **Step 3: Rebuild the named external staging directory**

After preserving and confirming the exact unresolved target
`C:\projects\ops-analyst-upload`, run the builder with `--replace` only if its
complete current inventory matches the canonical source. If it is stale,
partial, linked, special, or unexpected, stop and report it instead of deleting
anything.

Then run `--check --json` and retain the sanitized inventory in the validation
report, not inside staging.

- [ ] **Step 4: Run real isolated Nori installation again against final HEAD**

Use Task 5's live command. Expected: canonical content, generated skills,
unmanaged sentinel, and cleanup all pass on final HEAD.

- [ ] **Step 5: Request independent review**

Provide the reviewer with the approved design, this plan, full diff, focused
test results, WSL gate result, real isolated Nori smoke result, and staging
inventory. Require explicit review of destructive path safety, symlink/reparse
handling, manifest/schema alignment, operator-state isolation, secret leakage,
and documentation truthfulness.

- [ ] **Step 6: Resolve review findings with focused RED/GREEN cycles**

For each accepted defect, first add or tighten a regression, observe failure,
make the smallest fix, and rerun its focused suite. Do not bundle unrelated
cleanup.

- [ ] **Step 7: Re-run final evidence after the last code change**

Repeat Steps 1, 2, and 4 on the exact final commit candidate. Confirm:

```bash
git status --short
git diff --check
git log -1 --oneline
```

Expected: clean worktree and no uncommitted file.

- [ ] **Step 8: Commit review fixes if any**

Use a narrowly scoped commit message describing the actual correction. If no
fix was required, create no empty commit.

---

### Task 8: Operator-authorized dry-run and delivery handoff

**Files:**
- Update: `tests/validation-notes.md` only with sanitized observed results.
- Do not modify: manifest version, `.nori-version`, tags, releases, or active profile.

**Interfaces:**
- Consumes: independently approved final branch and regenerated staging.
- Produces: authenticated dry-run evidence and PR-ready handoff.

- [ ] **Step 1: Obtain explicit authorization for authenticated Nori access**

State that `upload --dry-run` requires existing authentication, may emit
analytics or perform local migrations, and is not a side-effect-free anonymous
validation. Do not continue without operator authorization.

- [ ] **Step 2: Check registry version state without exposing credentials**

Use the detected CLI's `upload --list-versions` for the intended namespace. If
`0.12.0` already exists, stop and request a new version decision. Do not bump
automatically.

- [ ] **Step 3: Link only a temporary release profile name**

Link the final staging directory under
`personal/senior-infra-ops-analyst-release-validation`. Confirm with `current`
and `list` that the active development profile was not replaced or switched.

- [ ] **Step 4: Execute dry-run and inspect mutations**

Hash staging immediately before and after:

```bash
nori-skillsets upload \
  personal/senior-infra-ops-analyst-release-validation \
  --dry-run
```

Record only package identity, version, registry endpoint class, exit status,
and sanitized before/after hash differences. Do not record tokens, headers, or
configuration content.

- [ ] **Step 5: Remove the temporary link and recheck operator state**

Unlink only `personal/senior-infra-ops-analyst-release-validation`. Confirm the
development link still resolves to the repository and the active agent profile
is unchanged.

- [ ] **Step 6: Prepare commit, push, and PR handoff**

Include scope, architecture decision, manifest migration, staging contract,
tests, real isolated Nori result, dry-run result, remaining publication gate,
and rollback. Push and open the PR only when authorized. Do not merge or perform
a real registry upload without a separate explicit request.
