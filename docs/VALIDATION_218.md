# 2.1.8 candidate validation · 2026-11-11

Local candidate, not a published release or full release certification. Built from the working tree based on 43d3d8a9c33bfded59e2abfa55d626fc4d07b1ee. Python 3.12; dependencies reused from an existing environment, not freshly resolved.

| Check | Result | Evidence / reproduction |
|---|---|---|
| Canonical source suite | PASS: 892 tests | AGENTIC_TEST_VERSION=2.1.8 python scripts/test_offline_214.py --source |
| Installed final wheel suite | PASS: 892 tests | AGENTIC_TEST_VERSION=2.1.8 python scripts/test_offline_214.py |
| Five Eval recipes | PASS with five rejecting controls | python examples/eval_recipes.py |
| Current documentation | PASS: 72 pages, 33 notebook targets | python scripts/check_learning_docs.py |
| Generated reading views | PASS: 33 | python scripts/render_notebook_docs.py --check |
| Offline examples | PASS: 58 executed; 1 skipped | scripts/validate_learning_offline_214.py with installed-site/version/evidence environment |
| Notebook cells in separate CPython processes | PASS: 33 notebooks, 237 code cells; 12 tagged cells skipped | python scripts/validate_notebook_cells.py |
| Fresh Jupyter kernels | BLOCKED | OS rejects socket/interface operations; CPython checks are not kernel acceptance |
| CLI / installed skill | PASS: 9 command checks | scripts/validate_skill_distribution.py |
| Wheel/source/installed/RECORD | PASS: 122 package files | scripts/verify_candidate.py WHEEL |
| Skill ZIP versus wheel | PASS: all 14 files byte-identical | Compare exported root agentic-systems/ against wheel bundled skill |
| Ruff, Pyright, import contracts, secret gate, twine | PASS | Existing project commands; Pyright 0 errors/warnings; 3 import contracts kept |
| Multi-Python CI / mutation | NOT RUN for this branch | Required before release certification |
| Live providers/models / EMR / Spark | NOT RUN for 2.1.8 | Historical campaigns are not transferred to new artifacts |

An example initially still pinned 2.1.7; corrected its active target, then all 58 examples passed (one service-profile example skipped).

Initial local export tests failed because the method edit affected the wrong class; corrected before the passing source/installed runs. Earlier invocations also selected the old SDK, omitted version configuration, or omitted EXPECTED_VERSION for smoke. Those attempts are retained in local logs. No SDK checks or business requirements were weakened.

Wheel SHA-256: `debfc22393199cf26de26c11856205afb9a3a606f91f98fbdf92abee14d94f2b`.

Standalone skill ZIP SHA-256: `d0d58e6c4536df4fadabd33e922daf13dd8dcab61bfc5f805f6fc68fdf91cdcd`.

Logs and detailed JSON/XML are in .tmp/218-* plus /tmp/*218*.log in the task workspace. The scripts above reproduce the checks; this report does not claim fresh dependency installation, successful Jupyter kernels or live inference.
