import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from unified_grammar.offline import enforce_offline  # noqa: E402

enforce_offline()
