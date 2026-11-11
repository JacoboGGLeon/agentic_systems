# Application structure
Verify agentic_systems.__version__ == "2.1.7" and installed wheel identity.
Start with assets/first_tool.py or assets/minimal.py, or adapt a repository example.
The CLI does not generate projects: `new` was removed in 2.1.7. Create application
files explicitly and never overwrite existing user work.

Keep application.py as the declaration, Tools and local Skill resources beside
it, tests with business assertions and negative controls, and evidence separate
from notebooks. Validate positive, negative and failure cases against the same
wheel; creating files alone does not validate an application.
