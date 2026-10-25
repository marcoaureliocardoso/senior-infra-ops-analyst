# CI isolation third-party policy notice
`bwrap.apparmor.in` is separately licensed GPL-2.0-only, not MIT. It adapts
AppArmor's `profiles/apparmor/profiles/extras/bwrap-userns-restrict` at revision
`72229df83059480f4e9fb1488624201bdbd61755`. The upstream root LICENSE applies
unless a subdirectory says otherwise; no exception was present for this profile.
The full upstream license is retained in `COPYING.AppArmor`.

Changes made on 2026-10-25: exact CI-private executable attachment, unique owned
parent/child names and removal of optional foreign local includes. The original
capability-stripping stacked-child construction is retained. This is CI-only
source policy data, not a Nori deliverable or a generic host exception. It comes
without warranty. The other project files retain their existing license.

Origin: https://gitlab.com/apparmor/apparmor/-/blob/72229df83059480f4e9fb1488624201bdbd61755/profiles/apparmor/profiles/extras/bwrap-userns-restrict

Bubblewrap is built unmodified from the separately pinned upstream archive.
Its COPYING is LGPL-2.1; neither the archive nor the resulting binary is shipped
in this repository, a Nori component or a release artifact. They are temporary
CI dependencies only. No upstream code is copied into the Python bootstrap.
