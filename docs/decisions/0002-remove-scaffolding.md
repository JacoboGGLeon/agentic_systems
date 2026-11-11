# Remove project generation from the SDK CLI

Status: accepted for the 2.1.7 candidate; supersedes the project-generation assumptions of ADR 0001.

The single refund scaffold imposes a business domain and duplicates learning examples. Configurable generation adds a second graph-design surface. Keep the CLI focused on version/API/dependency inspection and distributing the coding-assistant skill.

Remove `new`, `_scaffolding`, all bundled project templates and the authoring skill's scaffolding script. Existing generated applications are not touched. Users start from repository examples/notebooks or bundled first_tool/minimal assets and edit ordinary Graph definitions. This is an explicit breaking CLI change despite the patch release number selected by the maintainer; migration is documented.

Preserve the installed authoring bundle and runtime `toolkit.skill` API. Replace the scaffold CI smoke with installed skill install/export, destination protection and executable asset checks. Copy canonical skill resources into the mutation workspace so its baseline tests see the same inputs; do not weaken coverage/mutation thresholds.

Rollback requires reverting the removal commit in a new release; never replace published 2.1.6 artifacts. Acceptance requires absence of removed files in wheel/sdist, rejection of `new` without filesystem writes, full contracts and unchanged agent execution code.
