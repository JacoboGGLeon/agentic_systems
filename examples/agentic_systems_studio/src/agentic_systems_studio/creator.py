"""Agentic Systems Creator orchestration and artifact evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import agentic_systems as toolkit

from .scaffolder import ScaffoldReport, scaffold_application
from .systems import StudioConfig, build_system


def _artifact_payload(report: ScaffoldReport) -> dict[str, Any]:
    manifest_path = report.root / "manifest.json"
    mermaid_path = report.root / "assets" / "system.mmd"
    payload = report.to_dict()
    payload.update(
        {
            "manifest": json.loads(manifest_path.read_text(encoding="utf-8")),
            "mermaid": mermaid_path.read_text(encoding="utf-8"),
            "run_command": f"python -m {report.package_name}",
        }
    )
    return payload


def create_application(
    request: str,
    target: str | Path,
    *,
    name: str,
    template_system_id: str = "incident-response",
    config: StudioConfig | None = None,
    overwrite: bool = False,
) -> toolkit.RunResult:
    """Reason about a request, materialize it and return one normalized result.

    The reasoning boundary produces the blueprint. A deterministic scaffolding
    boundary then creates and validates the portable application. Success means
    both boundaries succeeded and the generated artifact passed its contract.
    """

    selected = config or StudioConfig()
    creator = build_system("agentic-systems-creator", selected)
    blueprint = creator.run(request, mode="prod")
    if not blueprint.ok:
        return toolkit.RunResult(
            text="The Creator blueprint failed; no files were generated.",
            data={"generated": False, "request": request},
            ok=False,
            engine="agentic-system",
            model=blueprint.model,
            mode="create",
            errors=list(blueprint.errors),
            usage=dict(blueprint.usage),
            meta={
                "studio_system_id": "agentic-systems-creator",
                "provider": selected.provider,
                "framework": selected.framework,
            },
            children=[blueprint],
        )

    report = scaffold_application(
        target,
        name=name,
        system_id=template_system_id,
        overwrite=overwrite,
    )
    artifact = _artifact_payload(report)
    validation = artifact["validation"]
    generated = toolkit.RunResult(
        text=(
            f"Generated {artifact['file_count']} files in {artifact['root']}."
            if validation["ok"]
            else f"Generated files in {artifact['root']}, but validation failed."
        ),
        data={"generated": True, "artifact": artifact},
        ok=bool(validation["ok"]),
        engine="python-runtime",
        model="deterministic-scaffolder",
        mode="create",
        validation=validation,
        meta={
            "boundary": "artifact-materialization",
            "template_system_id": template_system_id,
        },
    )
    text = (
        f"Agentic System generated successfully: {artifact['root']} "
        f"({artifact['file_count']} files, validation passed)."
        if generated.ok
        else f"Agentic System generation failed validation: {artifact['root']}."
    )
    result = toolkit.RunResult(
        text=text,
        final={"final_output": text, "artifact": artifact},
        data={
            "generated": generated.ok,
            "artifact": artifact,
            "blueprint": blueprint.final or {"text": blueprint.text},
        },
        ok=blueprint.ok and generated.ok,
        engine="agentic-system",
        model=blueprint.model,
        mode="create",
        usage=dict(blueprint.usage),
        validation=validation,
        meta={
            "studio_system_id": "agentic-systems-creator",
            "provider": selected.provider,
            "framework": selected.framework,
            "template_system_id": template_system_id,
            "artifact_root": str(report.root),
        },
        children=[blueprint, generated],
    )
    return result.raise_if_inconsistent()


__all__ = ["create_application"]
