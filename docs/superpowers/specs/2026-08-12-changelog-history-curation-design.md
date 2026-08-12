# Changelog History Curation Design

## Context

`CHANGELOG.md` currently presents every heading as a released version even
though repository evidence distinguishes three different cases:

- package states 0.8.0, 0.9.0, 0.9.1, 0.11.0, 0.11.1, and 0.12.0 were
  declared in version metadata but were never tagged;
- 0.3.0 and 0.3.3 were neither package versions nor Git tags;
- 0.2.1 is a real historical package version and Git tag but is absent from
  the changelog.

The 0.12.0 section is dated 2026-08-08 even though several of its entries were
added through 2026-08-12. The 0.10.0 section uses the version-bump date
2026-07-24 rather than the Git tag date 2026-07-27. The README calls the file
release history without explaining these distinctions.

## Decision

Use a curated two-tier changelog:

1. `## Unreleased package states` records version values that existed in
   package metadata but were not tagged. Each `###` heading states that it is
   unpublished and distinguishes the declaration date from any later update
   date.
2. `## Tagged versions` contains only versions represented by repository Git
   tags. Dates in these headings use the tag creator date recorded by Git.

The changelog remains the canonical detailed history, but it no longer implies
that every internal package state was published as a tag or GitHub Release.
The README will call the section `Version history` and describe the distinction
in its canonical link text.

No tag, GitHub Release, or package-version change is part of this work. The
current package version remains 0.12.0.

## Historical Reconciliation

- Retain the complete 0.12.0, 0.11.1, 0.11.0, 0.9.1, 0.9.0, and 0.8.0
  content under unpublished package-state headings. Record 0.12.0 as declared
  on 2026-08-08 and updated through 2026-08-12.
- Start the tagged-version section with 0.10.0 and correct its date to the Git
  tag creator date, 2026-07-27.
- Add 0.2.1 from the tagged manifest and tag evidence. Its entry summarizes
  the original nine-skill operational package without inventing later scope.
- Fold the 0.3.0 bullets into 0.3.1 because 0.3.1 is the first tagged and
  manifested version containing that cloud, observability, RCA, risk, command,
  template, and helper-script work.
- Fold the 0.3.3 bullets into 0.3.4 because 0.3.4 is the next actual package
  version and tag, and its tagged manifest explicitly includes project hygiene,
  canonical diagnostics, incident severity, validation, templates, live link
  validation, and refreshed external references.
- Preserve the existing 0.3.1 and 0.3.4 facts while removing the fictional
  0.3.0 and 0.3.3 version headings.

## Validation Contract

Expand `tests/test-release-history.py` and `tests/validate-content.py` so the
repository fails closed when changelog semantics drift:

- require the two-tier headings and their order;
- require the current `nori.json` version to match the first unpublished
  package-state heading;
- require unpublished package states to use explicit parseable headings;
- require the audited unpublished package-state set so 0.8.0, 0.9.0, and
  0.9.1 cannot be silently misrepresented as tagged versions;
- require tagged-version headings to be unique and in strict reverse semantic
  version order;
- reject 0.3.0 and 0.3.3 as version headings and require 0.2.1;
- require the corrected 0.10.0 tag date;
- retain mutation tests for README duplication and canonical changelog linkage;
- add mutations proving that a misclassified current version, a fictional
  tagged version, an omitted historical tag, and an incorrect tag date fail.

The deterministic package gate must run these tests without requiring network
access or a `.git` directory. Repository Git evidence is used to curate the
contract, while the checked-in validator protects the resulting facts in
packaged copies.

## Failure Handling

The validator reports a specific documentation error and exits nonzero. It
does not rewrite the changelog, create tags, query GitHub, or infer publication
from a version string. Historical changes require deliberate edits to both the
changelog and its regression contract.

## Acceptance Criteria

- Readers can distinguish unpublished package states from tagged versions.
- 0.12.0 remains the current package version and is explicitly unpublished.
- 0.10.0 uses the 2026-07-27 tag date.
- 0.2.1 appears as a tagged historical version.
- No version heading claims 0.3.0 or 0.3.3 existed.
- All existing accurate change facts remain represented after folding.
- README terminology and link text match the two-tier changelog.
- Mutation tests and the complete package validation gate pass.
- No tag, GitHub Release, or unrelated version metadata is changed.
