# CLI · Agentic Systems 2.1.7

The SDK installs `agentic-systems`. Run it in the environment containing the SDK.

| Command | Result | Boundary |
| --- | --- | --- |
| `version` | Installed SDK version | Does not inspect a checkout |
| `api` | JSON version and public names | Does not list signatures |
| `doctor` | Installed optional-dependency flags | Does not verify compatibility, credentials or services |
| `skill info` | SDK version and SHA-256 of bundled authoring files | Does not certify models/services |
| `skill install [destination]` | New skill folder; defaults to `.agents/skills/agentic-systems` | Refuses existing files, directories and symlinks |
| `skill export skill.zip` | ZIP with `agentic-systems/SKILL.md` and resources | Refuses existing paths; manual import required |

```bash
agentic-systems version
agentic-systems api
agentic-systems doctor
agentic-systems skill info
agentic-systems skill install
agentic-systems skill export skill.zip
```

Use `python -m agentic_systems.cli` if the executable is not on PATH. General
`--help` and `skill --help` describe available commands. Errors exit with code 2.
The authoring skill helps coding assistants build applications; it is separate
from runtime `toolkit.skill(...)` and `load_skill(...)`. Copy/export is offline,
does not execute the skill, and does not register it in a personal ChatGPT account.
Choose a fresh destination when updating a modified local skill.

## Migration from 2.1.6

**Breaking CLI change:** `agentic-systems new` and its bundled scaffolder are
removed. Start from [your first Tool](ONBOARDING_FIRST_RUN.md), the skill's
`assets/minimal.py`, or [repository examples](EXAMPLES_GUIDE.md). Existing generated
applications remain ordinary Python applications; this removal does not delete them.
Studio and the separate ADA diagnostic command remain optional distributions.
