# Documentation alignment review · Agentic Systems 2.1.9

## Changes

The current README, installation guide, documentation navigation, concepts, architecture, learning path, roadmap and release instructions now target 2.1.9. They introduce the core grammar progressively, explain the meaning of outputs, distinguish model-backed agent actors from graph-based agent actuators, and keep Runtime/Framework and Context/Memory separate.

Current notebook targets, example catalog metadata, SDK/optional-package version requirements and the canonical bundled authoring Skill target 2.1.9. The public download URL names the 2.1.9 Skill ZIP and explicitly becomes available after release finalization; before publication, export it from the installed candidate. The repository source update does not install or replace a personal ChatGPT Skill.

Explicit Agent contracts/policies remain advanced API references, with broader control-object validation planned for 2.1.10. They are not removed or presented as required first-run objects. Environment and Eval are independent additions, not mandatory consecutive layers.

Changed notebook source pins have old cell outputs cleared. The recorded-output viewer and underlying JSON retain their original 2.1.8 identities, including the separate failed Native rerun. Published release notes, historical campaigns, hashes and archived snapshots are not relabeled.

## Completed local checks

These checks used Python 3.12 in a reused environment. They are not a clean multi-Python release certification.

| Command / check | Observed result |
|---|---|
| `python scripts/check_learning_docs.py` | PASS: 77 pages and 35 notebook targets |
| `python scripts/check_catalog.py` | PASS: 52 entries |
| `python scripts/render_notebook_docs.py --check` | PASS: 35 notebook/Markdown pairs |
| `python scripts/validate_notebook_cells.py` | PASS: 35 notebooks, 258 executed cells, 12 tagged cells skipped; CPython processes, not Jupyter kernels |
| `AGENTIC_TEST_VERSION=2.1.9 python scripts/test_offline_214.py --source` | PASS: 895 tests; one runpy warning; blocked application effects 0 and real inference 0 |
| `python scripts/check_readme_examples.py` | PASS on installed 2.1.9 candidate: local outputs, stop/Memory, negative controls and two Native Tool choices through simulated Bedrock transport; 4 simulated calls, no live inference |
| `python scripts/validate_skill_distribution.py` | PASS on installed candidate: 9 CLI/install/export checks; no inference |
| `python scripts/check_secrets.py` | PASS |
| `git diff --check` | PASS |

## Initial failures and corrections

The initial build lacked setuptools; it passed after installing the declared build prerequisites. Notebook-view generation initially lacked nbconvert; it passed after installing the repository-pinned version. Initial full-suite collection lacked Streamlit. Further adapter checks lacked the Strands optional package and SOCKS support for the configured proxy. Dependencies were installed without changing network protections or weakening the tests.

The package README link check correctly rejected relative links; canonical absolute GitHub links were restored. The new recorded-output notebook is an evidence viewer, not a capability-construction lesson: a dedicated test now checks its preserved 2.1.8 records and absence of Agent execution, while construction lessons retain their declaration checks. The README transport fixture was updated to recognize the final synthesis phase, in which no Tool definitions are available.

Matplotlib's first font-cache initialization attempted a font-discovery subprocess under the notebook offline guard. Preparing its cache before the guarded run resolved this environment setup issue without relaxing the guard. Later checks passed with that cache and the completed optional dependencies.

## Pending release gates

Live model acceptance on the exact 2.1.9 wheel, final installed-wheel/multi-Python quality, mutation, the reviewed version-specific release policy, sealed artifact promotion and publication remain pending. The local build used the working tree and is not the sealed final release candidate. Ruff installation encountered a proxy timeout; no Ruff result is claimed in this report.

Historical Native/OpenAI Agents success on 2.1.8 is baseline evidence only. No new provider/framework certification, durable Memory, EMR or distributed Spark compatibility is asserted.
