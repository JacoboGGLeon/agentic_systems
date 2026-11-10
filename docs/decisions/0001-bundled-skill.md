# Bundle the authoring skill with the SDK

Status: proposed for the next release.

The SDK and its authoring skill have been separate downloads, with stale 2.1.5 guards blocking a verified 2.1.6 installation. Users need a local, versioned installation/export path without network access.

Keep `skills/agentic-systems` as the canonical source. A setuptools build hook copies that directory into the wheel as private package resources. Include the canonical source and hook in the sdist. Editable/source installs read the canonical directory when the bundled directory is absent. The CLI exposes `skill info`, `skill install [destination]`, and `skill export destination.zip`; none performs network calls or executes skill code. Existing destinations are rejected. Export/import is distinct from the runtime `toolkit.skill` capability declaration.

A second hand-maintained copy would drift. Installing from GitHub would require network access and could mismatch the installed SDK. Moving the source would break existing repository/release paths. The build hook preserves those paths with one source of truth; candidate builders must include it and check resource bytes too.

Validate wheel and sdist contents, source-to-wheel parity, installation outside a checkout, CLI paths with spaces, existing-path protection, ZIP layout and executable examples. Roll back by removing the additive command/resource hook; runtime execution contracts remain unchanged. Published 2.1.6 artifacts must never be replaced: promotion requires a new version and the normal release gates.
