"""Reference scaffolder for a portable Agentic Systems 2.0 application."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from .catalog import SystemSpec, get_system_spec


@dataclass(frozen=True)
class ScaffoldReport:
    root: Path
    package_name: str
    system_id: str
    files: tuple[Path, ...]

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "package_name": self.package_name,
            "system_id": self.system_id,
            "files": [str(path.relative_to(self.root)) for path in self.files],
        }


def _package_name(name: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip()).strip("_").lower()
    if not value or value[0].isdigit():
        value = f"agentic_{value or 'application'}"
    return value


def _write(path: Path, content: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Scaffolder will not overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8")


def _notebook(spec: SystemSpec, package: str) -> str:
    cells = [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# {spec.name}\n",
                "\n",
                "This notebook uses the same public constructor as the application and CLI.\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                f"from {package}.system import build_system\n",
                "system = build_system()\n",
                "system.inspect()\n",
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "if os.getenv('RUN_LIVE') == '1':\n",
                f"    result = system.run({spec.sample_input!r})\n",
                "    print(result.text or result.data)\n",
                "else:\n",
                "    print('Set RUN_LIVE=1 to execute the configured provider.')\n",
            ],
        },
    ]
    return json.dumps(
        {
            "cells": cells,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.11"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
        indent=2,
        ensure_ascii=False,
    )


def _system_source(spec: SystemSpec) -> str:
    stages = [
        {
            "id": stage.id,
            "name": stage.name,
            "kind": stage.kind,
            "instructions": stage.instructions,
        }
        for stage in spec.stages
    ]
    return dedent(
        f'''\
        """Executable assembly for {spec.name}."""

        import os
        import agentic_systems as toolkit
        from .tools import normalize_input, record_note

        STAGES = {stages!r}


        def build_system():
            provider = os.getenv("AGENTIC_PROVIDER", "openai-runtime")
            framework = os.getenv("AGENTIC_FRAMEWORK", "agentic-systems")
            model = os.getenv("AGENTIC_MODEL") or None
            runtime = toolkit.runtime(provider=provider, model=model)
            system = toolkit.system(runtime=runtime, model=model)

            for stage in STAGES:
                operator = stage["kind"] == "operator"
                tool = normalize_input if operator else record_note
                skill = toolkit.skill(
                    name=f"{spec.runtime_skill}-{{stage['id']}}",
                    description=stage["instructions"],
                    tools=[tool],
                    version="2.0.0",
                )
                system.agent(
                    name=f"{spec.id}.{{stage['id']}}",
                    instructions=stage["instructions"],
                    skills=[skill],
                    engine="python-runtime" if operator else provider,
                    framework=None if operator or framework == "agentic-systems" else framework,
                    model=None if operator else model,
                    runtime=toolkit.runtime(provider="python-runtime") if operator else runtime,
                    policy={{"max_tokens": 1024, "max_turns": 6, "max_tool_calls": 4}},
                )

            report = system.inspect()
            report.raise_if_errors()
            return system.compile(execution=toolkit.SequentialPlan(), name="{spec.id}")
        '''
    )


def _files(spec: SystemSpec, package: str) -> dict[str, str]:
    manifest = {
        "schema_version": "agentic-systems.studio/v1",
        "id": spec.id,
        "name": spec.name,
        "agentic_systems_version": "2.0.0",
        "size": spec.size,
        "stages": [stage.to_dict() for stage in spec.stages],
        "capabilities": list(spec.capabilities),
        "assets": list(spec.assets),
    }
    return {
        "pyproject.toml": dedent(
            f"""\
            [build-system]
            requires = ["hatchling>=1.24"]
            build-backend = "hatchling.build"

            [project]
            name = "{package.replace('_', '-')}"
            version = "0.1.0"
            requires-python = ">=3.11"
            dependencies = ["agentic-systems==2.0.0"]

            [tool.hatch.build.targets.wheel]
            packages = ["src/{package}"]
            """
        ),
        "README.md": dedent(
            f"""\
            # {spec.name}

            Portable Agentic Systems 2.0 application generated by Agentic Systems Studio.

            Architecture: {len(spec.stages)} computation units, {spec.size} size,
            deterministic operators on python-runtime and reasoning agents on the
            selected provider/framework.

            Run python -m {package} after configuring .env.
            """
        ),
        ".env.example": dedent(
            """\
            AGENTIC_PROVIDER=openai-runtime
            AGENTIC_FRAMEWORK=agentic-systems
            AGENTIC_MODEL=
            # Provider credentials stay in the environment; never put them in manifests.
            """
        ),
        "manifest.json": json.dumps(manifest, indent=2, ensure_ascii=False),
        f"src/{package}/__init__.py": "from .system import build_system\n\n__all__ = ['build_system']\n",
        f"src/{package}/__main__.py": dedent(
            f"""\
            from .system import build_system

            if __name__ == "__main__":
                result = build_system().run(input("Input: "))
                print(result.text or result.data)
            """
        ),
        f"src/{package}/tools.py": dedent(
            """\
            import agentic_systems as toolkit

            @toolkit.tool
            def normalize_input(text: str) -> dict:
                \"\"\"Normalize the external input at a deterministic boundary.\"\"\"
                return {"text": str(text).strip(), "length": len(str(text).strip())}

            @toolkit.tool
            def record_note(note: str) -> dict:
                \"\"\"Preserve an evidence note emitted by a reasoning agent.\"\"\"
                return {"note": note.strip()}
            """
        ),
        f"src/{package}/system.py": _system_source(spec),
        f"src/{package}/environment.py": dedent(
            """\
            def build_environment(records, graph):
                import agentic_systems as toolkit
                return toolkit.environment(records, graph=graph)
            """
        ),
        f"src/{package}/evals.py": dedent(
            """\
            def evaluate(target, cases):
                import agentic_systems as toolkit
                return toolkit.eval(target=target, cases=cases)
            """
        ),
        "skills/codex-agentic-application/SKILL.md": dedent(
            f"""\
            ---
            name: codex-agentic-application
            description: Build or modify the {spec.name} application while preserving its manifest, execution graph and public Agentic Systems 2.0 contracts.
            ---

            Use manifest.json as the application contract. Keep source, notebook,
            tests and Mermaid derived from the same stage identities. Preserve the
            deterministic boundary before reasoning stages. Never place provider
            credentials in generated files.
            """
        ),
        f"skills/runtime/{spec.runtime_skill}.json": json.dumps(
            {
                "name": spec.runtime_skill,
                "version": "2.0.0",
                "capabilities": list(spec.capabilities),
                "stage_tools": list(spec.tools),
            },
            indent=2,
        ),
        "assets/system.mmd": spec.mermaid(),
        "notebooks/00_walkthrough.ipynb": _notebook(spec, package),
        "tests/test_contract.py": dedent(
            f"""\
            from {package}.system import STAGES, build_system

            def test_declared_stage_count():
                assert len(STAGES) == {len(spec.stages)}

            def test_system_builds_and_inspects():
                compiled = build_system()
                assert compiled.inspect()["unit_count"] == len(STAGES)
            """
        ),
    }


def scaffold_application(
    target: str | Path,
    *,
    name: str,
    system_id: str = "agentic-systems-creator",
    overwrite: bool = False,
) -> ScaffoldReport:
    """Create a complete reference application without overwriting files by default."""

    root = Path(target).resolve()
    spec = get_system_spec(system_id)
    package = _package_name(name)
    generated: list[Path] = []

    for relative, content in _files(spec, package).items():
        path = root / relative
        _write(path, content, overwrite=overwrite)
        generated.append(path)

    database = root / "data" / "app.db"
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists() and not overwrite:
        raise FileExistsError(f"Scaffolder will not overwrite existing database: {database}")
    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                input_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT OR REPLACE INTO app_metadata(key, value) VALUES ('system_id', ?)",
            (spec.id,),
        )
        connection.commit()
    finally:
        connection.close()
    generated.append(database)
    return ScaffoldReport(root, package, spec.id, tuple(generated))


__all__ = ["ScaffoldReport", "scaffold_application"]
