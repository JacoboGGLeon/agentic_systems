# Borrowed AWS session and ADA add-on · 2.1.5

Input: a prepared boto3 session, model and region. Process: validate runtime, compile the Agent and inspect configuration. Output: a credential-free configuration-only report. [Notebook](01_aws_session.ipynb) · [English reading view](01_aws_session.md) · [Code](example.py).

Explicit fixture credentials prevent credential or metadata lookup. No client or model is invoked. In ADA, pass the same platform-prepared session to runtime; Agent/System grammar is unchanged.

Install the matching SDK and separate agentic-systems-ada package plus boto3. The add-on is not included in all. Diagnostics do not repair environment variables or certify identity/access. Adapter regressions use simulated transport; real AWS IAM/ADA access requires separate verification.

Toolkit invocations sharing a session are serialized. Its owner coordinates external concurrent use and lifetime. The toolkit does not close the session or store it in Context, Memory, state or evidence.
