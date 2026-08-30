"""Reference scaffolder for a portable Agentic Systems 2.1 application."""

from __future__ import annotations

import ast
from io import BytesIO
import json
import re
import sqlite3
import zipfile
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from agentic_systems import __version__ as AGENTIC_SYSTEMS_VERSION

from agentic_systems.registry import (
    FRAMEWORK_NAMES,
    PROVIDER_NAMES,
    provider_capability,
)

from .catalog import SystemSpec, get_system_spec


@dataclass(frozen=True)
class ScaffoldReport:
    root: Path
    package_name: str
    system_id: str
    files: tuple[Path, ...]

    @property
    def relative_files(self) -> tuple[str, ...]:
        return tuple(path.relative_to(self.root).as_posix() for path in self.files)

    @property
    def archive_name(self) -> str:
        return f"{self.package_name}.zip"

    def validate(self) -> dict:
        """Validate contract coherence without making a provider request."""

        required = {
            "manifest.json",
            "pyproject.toml",
            ".env.example",
            "README.md",
            "assets/system.mmd",
            "data/app.db",
            "notebooks/00_walkthrough.ipynb",
            "tests/test_contract.py",
            "tests/test_execution.py",
            f"src/{self.package_name}/__init__.py",
            f"src/{self.package_name}/__main__.py",
            f"src/{self.package_name}/tools.py",
            f"src/{self.package_name}/skills.py",
            f"src/{self.package_name}/agents.py",
            f"src/{self.package_name}/system.py",
            f"src/{self.package_name}/environment.py",
            f"src/{self.package_name}/evals.py",
            f"src/{self.package_name}/settings.py",
        }
        present = set(self.relative_files)
        checks: dict[str, bool] = {
            "required_assets": required <= present,
            "all_reported_files_exist": all(path.is_file() for path in self.files),
        }
        issues: list[dict[str, str]] = []

        try:
            manifest = json.loads(
                (self.root / "manifest.json").read_text(encoding="utf-8")
            )
            stages = manifest.get("stages") or []
            checks["manifest_identity"] = manifest.get("id") == self.system_id
            declared_assets = set(manifest.get("assets") or [])
            checks["manifest_assets_resolve"] = bool(declared_assets) and (
                declared_assets == present
            )
            checks["execution_plan_declared"] = (
                manifest.get("execution", {}).get("plan") == "sequential"
            )
            runtime_policy = manifest.get("runtime_policy") or {}
            checks["provider_framework_policy_declared"] = bool(
                runtime_policy.get("reasoning_providers")
            ) and bool(runtime_policy.get("frameworks"))
        except (OSError, json.JSONDecodeError) as exc:
            manifest = {}
            stages = []
            checks.update(
                {
                    "manifest_identity": False,
                    "manifest_assets_resolve": False,
                    "execution_plan_declared": False,
                    "provider_framework_policy_declared": False,
                }
            )
            issues.append(
                {"code": "invalid_manifest", "message": str(exc), "severity": "error"}
            )

        try:
            tools_path = self.root / "src" / self.package_name / "tools.py"
            tree = ast.parse(tools_path.read_text(encoding="utf-8"))
            implemented_tools = {
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and any(
                    (isinstance(decorator, ast.Attribute) and decorator.attr == "tool")
                    or (isinstance(decorator, ast.Name) and decorator.id == "tool")
                    for decorator in node.decorator_list
                )
            }
            stage_tools = {str(stage["tool_key"]) for stage in stages}
            checks["manifest_tools_resolve"] = bool(stage_tools) and (
                stage_tools <= implemented_tools
            )
            runtime_paths = sorted((self.root / "skills" / "runtime").glob("*.json"))
            if len(runtime_paths) != 1:
                raise ValueError("Expected exactly one runtime Skill declaration.")
            runtime_skill = json.loads(runtime_paths[0].read_text(encoding="utf-8"))
            runtime_tools = set(runtime_skill.get("stage_tools") or [])
            checks["runtime_skill_tools_resolve"] = runtime_tools == stage_tools and (
                runtime_tools <= implemented_tools
            )
        except (
            KeyError,
            OSError,
            SyntaxError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            checks["manifest_tools_resolve"] = False
            checks["runtime_skill_tools_resolve"] = False
            issues.append(
                {
                    "code": "invalid_tool_contract",
                    "message": str(exc),
                    "severity": "error",
                }
            )

        try:
            notebook = json.loads(
                (self.root / "notebooks" / "00_walkthrough.ipynb").read_text(
                    encoding="utf-8"
                )
            )
            cells = notebook.get("cells") or []
            code = "\n".join(
                "".join(cell.get("source") or [])
                for cell in cells
                if cell.get("cell_type") == "code"
            )
            checks["notebook_contract"] = (
                notebook.get("nbformat") == 4
                and bool(cells)
                and all(cell.get("id") for cell in cells)
                and "sys.path.insert" in code
                and "build_system" in code
                and "RUN_LIVE" in code
            )
        except (OSError, json.JSONDecodeError) as exc:
            checks["notebook_contract"] = False
            issues.append(
                {"code": "invalid_notebook", "message": str(exc), "severity": "error"}
            )

        try:
            mermaid = (self.root / "assets" / "system.mmd").read_text(encoding="utf-8")
            checks["mermaid_stage_identity"] = bool(stages) and all(
                f"stage_{index}_{str(stage['id']).replace('-', '_')}" in mermaid
                for index, stage in enumerate(stages)
            )
        except (KeyError, OSError, TypeError):
            checks["mermaid_stage_identity"] = False

        try:
            connection = sqlite3.connect(self.root / "data" / "app.db")
            try:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                database_stages = {
                    row[0] for row in connection.execute("SELECT id FROM stages")
                }
                database_tools = {
                    row[0] for row in connection.execute("SELECT id FROM tools")
                }
            finally:
                connection.close()
            manifest_stages = {str(stage["id"]) for stage in stages}
            manifest_tools = {str(stage["tool_key"]) for stage in stages}
            checks["sqlite_contract"] = (
                {
                    "app_metadata",
                    "stages",
                    "tools",
                    "runs",
                }
                <= tables
                and database_stages == manifest_stages
                and (database_tools == manifest_tools)
            )
        except (KeyError, sqlite3.Error) as exc:
            checks["sqlite_contract"] = False
            issues.append(
                {"code": "invalid_sqlite", "message": str(exc), "severity": "error"}
            )

        python_sources = sorted((self.root / "src").rglob("*.py"))
        try:
            for source in python_sources:
                compile(source.read_text(encoding="utf-8"), str(source), "exec")
            checks["python_sources_compile"] = bool(python_sources)
        except (OSError, SyntaxError) as exc:
            checks["python_sources_compile"] = False
            issues.append(
                {
                    "code": "invalid_python_source",
                    "message": str(exc),
                    "severity": "error",
                }
            )

        try:
            readme = (self.root / "README.md").read_text(encoding="utf-8")
            checks["readme_contract"] = (
                "pip install" in readme
                and f"python -m {self.package_name}" in readme
                and "pytest" in readme
            )
        except OSError:
            checks["readme_contract"] = False

        for name, passed in checks.items():
            if not passed:
                issues.append(
                    {
                        "code": name,
                        "message": f"Generated artifact check failed: {name}.",
                        "severity": "error",
                    }
                )
        return {"ok": all(checks.values()), "checks": checks, "issues": issues}

    def archive_bytes(self) -> bytes:
        """Return a portable ZIP containing exactly the generated files."""

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in self.files:
                archive.write(path, path.relative_to(self.root).as_posix())
        return buffer.getvalue()

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "package_name": self.package_name,
            "system_id": self.system_id,
            "file_count": len(self.files),
            "files": list(self.relative_files),
            "archive_name": self.archive_name,
            "validation": self.validate(),
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
            "id": "introduction",
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                f"# {spec.name}\n",
                "\n",
                "This notebook uses the same public constructor as the CLI and tests.\n",
            ],
        },
        {
            "id": "fresh-kernel-bootstrap",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from pathlib import Path\n",
                "import sys\n",
                "\n",
                "PROJECT_ROOT = next(\n",
                "    candidate for candidate in (Path.cwd(), *Path.cwd().parents)\n",
                f"    if (candidate / 'src' / '{package}').is_dir()\n",
                ")\n",
                "sys.path.insert(0, str(PROJECT_ROOT / 'src'))\n",
                f"from {package}.settings import AppSettings\n",
                f"from {package}.system import STAGES, build_system\n",
                f"from {package}.tools import TOOLS\n",
                "settings = AppSettings(provider='openai-runtime', framework='native')\n",
                "system = build_system(settings)\n",
                "system.inspect()\n",
            ],
        },
        {
            "id": "deterministic-tool-check",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "first_stage = STAGES[0]\n",
                f"tool_result = TOOLS[first_stage['tool_key']].run({{'text': {spec.sample_input!r}}})\n",
                "assert tool_result.ok and isinstance(tool_result.data, dict)\n",
                "tool_result.data\n",
            ],
        },
        {
            "id": "optional-live-run",
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "if os.getenv('RUN_LIVE') == '1':\n",
                f"    result = system.run({spec.sample_input!r})\n",
                "    assert result.ok, result.errors\n",
                "    print(result.text or result.data)\n",
                "else:\n",
                "    print('Offline checks passed. Set RUN_LIVE=1 for the configured provider.')\n",
            ],
        },
    ]
    return json.dumps(
        {
            "cells": cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.11"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
        indent=2,
        ensure_ascii=False,
    )


def _settings_source() -> str:
    return dedent(
        '''\
        """Provider and framework settings for the generated application."""

        from __future__ import annotations

        from dataclasses import dataclass
        import os

        import agentic_systems as toolkit
        from agentic_systems.registry import FRAMEWORK_NAMES, PROVIDER_NAMES, provider_capability

        REASONING_PROVIDERS = {"auto", *(name for name in PROVIDER_NAMES if provider_capability(name, "model_generation").status != "unsupported")}
        APPLICATION_FRAMEWORKS = set(FRAMEWORK_NAMES)


        @dataclass(frozen=True)
        class AppSettings:
            provider: str = "auto"
            framework: str = "native"
            model: str | None = None
            timeout_s: float = 120.0
            max_turns: int = 6
            max_tool_calls: int = 4
            max_tokens: int = 1024

            def __post_init__(self):
                if self.provider == "python-runtime":
                    raise ValueError(
                        "This system contains reasoning stages; python-runtime is only "
                        "valid for deterministic operator stages."
                    )
                if self.provider not in REASONING_PROVIDERS:
                    raise ValueError(f"Unsupported reasoning provider: {self.provider}")
                if self.framework not in APPLICATION_FRAMEWORKS:
                    raise ValueError(f"Unsupported framework: {self.framework}")

            @classmethod
            def from_env(cls):
                return cls(
                    provider=os.getenv("AGENTIC_SYSTEMS_PROVIDER", "auto"),
                    framework=os.getenv("AGENTIC_SYSTEMS_FRAMEWORK", "native"),
                    model=os.getenv("AGENTIC_SYSTEMS_MODEL") or None,
                )

            @property
            def framework_value(self):
                return None if self.framework == "native" else self.framework

            def reasoning_runtime(self):
                return toolkit.runtime(
                    provider=self.provider,
                    model=self.model,
                    scheduler=toolkit.scheduler(
                        timeout_s=self.timeout_s,
                        max_turns=self.max_turns,
                        max_tool_calls=self.max_tool_calls,
                    ),
                )

            def operator_runtime(self):
                return toolkit.runtime(
                    provider="python-runtime",
                    scheduler=toolkit.scheduler(
                        timeout_s=self.timeout_s,
                        max_turns=2,
                        max_tool_calls=1,
                    ),
                )
        '''
    )


def _skills_source() -> str:
    return dedent(
        '''\
        """Runtime Skill construction derived from the system declaration."""

        import agentic_systems as toolkit


        def build_stage_skill(system_id, runtime_skill, stage, tool):
            return toolkit.skill(
                name=f"{runtime_skill}-{stage['id']}",
                description=f"{stage['name']}: {stage['capability']}",
                tools=[tool],
                prompts={"instructions": stage["instructions"]},
                metadata={
                    "system_id": system_id,
                    "stage_id": stage["id"],
                    "stage_kind": stage["kind"],
                    "capability": stage["capability"],
                    "tool_key": stage["tool_key"],
                },
                version=toolkit.__version__,
            )
        '''
    )


def _agents_source() -> str:
    return dedent(
        '''\
        """Agent assembly derived from declared stages."""

        from .skills import build_stage_skill
        from .tools import TOOLS


        def add_stage_agent(system, system_id, system_name, runtime_skill, stage, settings, reasoning_runtime):
            tool = TOOLS[stage["tool_key"]]
            skill = build_stage_skill(system_id, runtime_skill, stage, tool)
            is_operator = stage["kind"] == "operator"
            instructions = (
                f"You are the {stage['name']} in {system_name}. {stage['instructions']} "
                "Use the supplied input as data. Do not fabricate unavailable evidence. "
                "Call your registered tool when it can establish or preserve deterministic evidence. "
                "Return a concise handoff for the next computation unit."
            )
            return system.agent(
                name=f"{system_id}.{stage['id']}",
                instructions=instructions,
                skills=[skill],
                engine="python-runtime" if is_operator else settings.provider,
                framework=None if is_operator else settings.framework_value,
                model=None if is_operator else settings.model,
                runtime=settings.operator_runtime() if is_operator else reasoning_runtime,
                policy={
                    "max_tool_calls": 1 if is_operator else settings.max_tool_calls,
                    "max_turns": 2 if is_operator else settings.max_turns,
                    "max_tokens": settings.max_tokens,
                },
            )
        '''
    )


def _system_source(spec: SystemSpec) -> str:
    stages = [stage.to_dict() for stage in spec.stages]
    return dedent(
        f'''\
        """Executable assembly for {spec.name}."""

        import agentic_systems as toolkit

        from .agents import add_stage_agent
        from .settings import AppSettings

        SYSTEM_ID = {spec.id!r}
        SYSTEM_NAME = {spec.name!r}
        RUNTIME_SKILL = {spec.runtime_skill!r}
        STAGES = {stages!r}


        def build_system(settings=None):
            selected = settings or AppSettings.from_env()
            reasoning_runtime = selected.reasoning_runtime()
            system = toolkit.system(runtime=reasoning_runtime, model=selected.model)
            for stage in STAGES:
                add_stage_agent(
                    system,
                    SYSTEM_ID,
                    SYSTEM_NAME,
                    RUNTIME_SKILL,
                    stage,
                    selected,
                    reasoning_runtime,
                )
            report = system.inspect()
            report.raise_if_errors()
            return system.compile(
                execution=toolkit.SequentialPlan(),
                name=SYSTEM_ID,
            )
        '''
    )


def _tools_source() -> str:
    """Copy the portable deterministic operator implementation into the app."""

    return Path(__file__).with_name("operators.py").read_text(encoding="utf-8")


def _files(spec: SystemSpec, package: str) -> dict[str, str]:
    generated_assets = (
        "pyproject.toml",
        "README.md",
        ".env.example",
        "manifest.json",
        f"src/{package}/__init__.py",
        f"src/{package}/__main__.py",
        f"src/{package}/tools.py",
        f"src/{package}/skills.py",
        f"src/{package}/agents.py",
        f"src/{package}/system.py",
        f"src/{package}/environment.py",
        f"src/{package}/evals.py",
        f"src/{package}/settings.py",
        "skills/codex-agentic-application/SKILL.md",
        f"skills/runtime/{spec.runtime_skill}.json",
        "assets/system.mmd",
        "notebooks/00_walkthrough.ipynb",
        "tests/test_contract.py",
        "tests/test_execution.py",
        "data/app.db",
    )
    manifest = {
        "schema_version": "agentic-systems.studio/v1",
        "id": spec.id,
        "name": spec.name,
        "agentic_systems_version": AGENTIC_SYSTEMS_VERSION,
        "size": spec.size,
        "stages": [stage.to_dict() for stage in spec.stages],
        "capabilities": list(spec.capabilities),
        "execution": {"plan": "sequential", "boundary": "system"},
        "runtime_policy": {
            "operator_provider": "python-runtime",
            "reasoning_providers": [
                "auto",
                *[
                    name
                    for name in PROVIDER_NAMES
                    if provider_capability(name, "model_generation").status
                    != "unsupported"
                ],
            ],
            "frameworks": list(FRAMEWORK_NAMES),
            "default_provider": "auto",
            "default_framework": "native",
        },
        "assets": list(generated_assets),
    }
    stage_tools = list(dict.fromkeys(stage.tool_key for stage in spec.stages))
    return {
        "pyproject.toml": dedent(
            f'''\
            [build-system]
            requires = ["hatchling>=1.24"]
            build-backend = "hatchling.build"

            [project]
            name = "{package.replace("_", "-")}"
            version = "0.1.0"
            requires-python = ">=3.11"
            dependencies = ["agentic-systems=={AGENTIC_SYSTEMS_VERSION}"]

            [project.optional-dependencies]
            test = ["pytest>=8", "nbclient>=0.10", "nbformat>=5.10", "ipykernel>=6"]

            [tool.pytest.ini_options]
            pythonpath = ["src"]

            [tool.hatch.build.targets.wheel]
            packages = ["src/{package}"]
            '''
        ),
        "README.md": dedent(
            f"""\
            # {spec.name}

            Portable Agentic Systems 2.1 application generated by Agentic Systems Studio.

            Architecture: {len(spec.stages)} computation units, {spec.size} size,
            deterministic operators on python-runtime and reasoning agents on the
            selected provider/framework.

            ## Install

                python -m pip install -e ".[test]"

            Copy `.env.example` to `.env`, configure one reasoning provider, then run:

                python -m {package}
                python -m pytest -q
                python -m nbconvert --to notebook --execute notebooks/00_walkthrough.ipynb --output executed.ipynb

            The notebook executes deterministic checks by default. Set `RUN_LIVE=1`
            only when you intentionally want to call the configured provider.
            """
        ),
        ".env.example": dedent(
            """\
            AGENTIC_SYSTEMS_PROVIDER=auto
            AGENTIC_SYSTEMS_FRAMEWORK=native
            AGENTIC_SYSTEMS_MODEL=
            AGENTIC_SYSTEMS_TIMEOUT_S=120
            AGENTIC_SYSTEMS_MAX_TURNS=6
            AGENTIC_SYSTEMS_MAX_TOOL_CALLS=4
            AGENTIC_SYSTEMS_MAX_TOKENS=1024

            OPENAI_API_KEY=
            OPENAI_MODEL=gpt-4.1-mini

            OLLAMA_BASE_URL=http://localhost:11434
            OLLAMA_MODEL=qwen3:4b-instruct-2507-q4_K_M

            AWS_BEARER_TOKEN_BEDROCK=
            AWS_REGION=us-east-2
            BEDROCK_MODEL_ID=

            VLLM_BASE_URL=http://localhost:8000/v1
            VLLM_API_KEY=
            VLLM_MODEL=
            """
        ),
        "manifest.json": json.dumps(manifest, indent=2, ensure_ascii=False),
        f"src/{package}/__init__.py": (
            "from .settings import AppSettings\n"
            "from .system import build_system\n\n"
            "__all__ = ['AppSettings', 'build_system']\n"
        ),
        f"src/{package}/__main__.py": dedent(
            """\
            import json

            from .system import build_system


            def main():
                result = build_system().run(input("Input: "))
                print(json.dumps(result.model_dump(mode="json"), indent=2, default=str))
                return 0 if result.ok else 1


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ),
        f"src/{package}/tools.py": _tools_source(),
        f"src/{package}/skills.py": _skills_source(),
        f"src/{package}/agents.py": _agents_source(),
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
        f"src/{package}/settings.py": _settings_source(),
        "skills/codex-agentic-application/SKILL.md": dedent(
            f"""\
            ---
            name: codex-agentic-application
            description: Build or modify the {spec.name} application while preserving its manifest, execution graph and public Agentic Systems 2.1 contracts.
            ---

            Use manifest.json as the source of truth. Keep source, notebook,
            tests, SQLite inventory and Mermaid derived from the same stage and
            Tool identities. Run both test files and the deterministic notebook
            before claiming the application is valid. Never place provider
            credentials in generated files.
            """
        ),
        f"skills/runtime/{spec.runtime_skill}.json": json.dumps(
            {
                "name": spec.runtime_skill,
                "version": AGENTIC_SYSTEMS_VERSION,
                "capabilities": list(spec.capabilities),
                "stage_tools": stage_tools,
                "stages": [
                    {
                        "id": stage.id,
                        "kind": stage.kind,
                        "capability": stage.capability,
                        "tool_key": stage.tool_key,
                    }
                    for stage in spec.stages
                ],
            },
            indent=2,
        ),
        "assets/system.mmd": spec.mermaid(),
        "notebooks/00_walkthrough.ipynb": _notebook(spec, package),
        "tests/test_contract.py": dedent(
            f"""\
            import json
            from pathlib import Path

            import pytest

            from {package}.settings import AppSettings
            from {package}.system import STAGES, build_system
            from {package}.tools import TOOLS

            PROJECT_ROOT = Path(__file__).resolve().parents[1]


            def test_manifest_source_skill_and_tools_are_one_to_one():
                manifest = json.loads((PROJECT_ROOT / "manifest.json").read_text(encoding="utf-8"))
                runtime_path = next((PROJECT_ROOT / "skills" / "runtime").glob("*.json"))
                runtime_skill = json.loads(runtime_path.read_text(encoding="utf-8"))
                manifest_tools = {{stage["tool_key"] for stage in manifest["stages"]}}
                assert manifest["stages"] == STAGES
                assert set(runtime_skill["stage_tools"]) == manifest_tools
                assert manifest_tools <= set(TOOLS)


            def test_system_builds_and_inspects():
                compiled = build_system(AppSettings(provider="openai-runtime"))
                assert compiled.inspect()["unit_count"] == len(STAGES)


            def test_python_runtime_is_rejected_for_reasoning_stages():
                with pytest.raises(ValueError, match="reasoning stages"):
                    AppSettings(provider="python-runtime")


            def test_mermaid_uses_declared_stage_identities():
                diagram = (PROJECT_ROOT / "assets" / "system.mmd").read_text(encoding="utf-8")
                for index, stage in enumerate(STAGES):
                    assert f"stage_{{index}}_{{stage['id'].replace('-', '_')}}" in diagram
            """
        ),
        "tests/test_execution.py": dedent(
            f"""\
            import os

            import pytest

            from {package}.settings import AppSettings
            from {package}.system import STAGES, build_system
            from {package}.tools import TOOLS

            SAMPLE_INPUT = {spec.sample_input!r}


            @pytest.mark.parametrize("tool_name", sorted({stage_tools!r}))
            def test_every_declared_tool_executes_and_returns_a_dictionary(tool_name):
                argument = (
                    "note" if tool_name == "record_reasoning_evidence"
                    else "answer" if tool_name == "validate_review_claim"
                    else "text"
                )
                result = TOOLS[tool_name].run({{argument: SAMPLE_INPUT}})
                assert result.ok, result.errors
                assert isinstance(result.data, dict)


            @pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="live provider opt-in")
            def test_configured_provider_live_returns_normalized_result():
                result = build_system(AppSettings.from_env()).run(SAMPLE_INPUT)
                assert result.ok, result.errors
                assert result.children
                assert all(child.ok for child in result.children)
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
    """Create a complete reference application without overwriting by default."""

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
        raise FileExistsError(
            f"Scaffolder will not overwrite existing database: {database}"
        )
    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS app_metadata(
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stages(
                id TEXT PRIMARY KEY,
                position INTEGER NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                capability TEXT NOT NULL,
                tool_key TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tools(
                id TEXT PRIMARY KEY
            );
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
        connection.execute("DELETE FROM stages")
        connection.execute("DELETE FROM tools")
        connection.executemany(
            """
            INSERT INTO stages(id, position, name, kind, capability, tool_key)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    stage.id,
                    position,
                    stage.name,
                    stage.kind,
                    stage.capability,
                    stage.tool_key,
                )
                for position, stage in enumerate(spec.stages)
            ],
        )
        connection.executemany(
            "INSERT INTO tools(id) VALUES (?)",
            [(tool_key,) for tool_key in dict.fromkeys(spec.tools)],
        )
        connection.commit()
    finally:
        connection.close()
    generated.append(database)
    report = ScaffoldReport(root, package, spec.id, tuple(generated))
    validation = report.validate()
    if not validation["ok"]:
        raise ValueError(
            f"Generated scaffold failed validation: {validation['issues']}"
        )
    return report


__all__ = ["ScaffoldReport", "scaffold_application"]
