"""Run one repository example offline using the installed SDK."""
import argparse
import importlib
import json
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', help='Repository-relative example.py or application.py')
    args = parser.parse_args(argv)
    path = (ROOT / args.path).resolve()
    if not path.is_relative_to(ROOT / 'examples') or path.suffix != '.py' or not path.is_file():
        parser.error('Choose a Python example inside this repository')
    if 'history' in path.parts or 'strands_protocol_graph' in path.parts:
        parser.error('Historical and local-service examples need their own documented profile')
    sys.path[:0] = [str(ROOT), str(ROOT / 'tutorials'),
                   str(ROOT / 'examples/agentic_systems_studio/src')]
    from _offline import enforce_offline, blocked_attempts
    import agentic_systems as toolkit
    if toolkit.__version__ != '2.1.9':
        parser.error('Install agentic-systems==2.1.9 in this Python environment')
    platform.platform()  # Prewarm stdlib OS discovery before the application guard.
    enforce_offline()
    module = importlib.import_module('.'.join(path.relative_to(ROOT).with_suffix('').parts))
    entry = getattr(module, 'run', None) or getattr(module, 'demonstrate', None)
    if not callable(entry):
        parser.error('This file has no run()/demonstrate() entrypoint')
    output = entry()
    if blocked_attempts():
        raise RuntimeError('Example attempted networking or subprocess execution')
    if isinstance(output, toolkit.RunResult):
        if not output.check_invariants().ok:
            raise AssertionError('RunResult invariants failed')
        output = output.to_dict()
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
