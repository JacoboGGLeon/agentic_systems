# Runtime, actor and orchestrator
LangGraph is the sole orchestrator. Actor frameworks: native, openai-agents,
strands. Provider identifiers: python-runtime, openai-runtime, bedrock-runtime,
ollama-runtime, vllm-runtime. Ollama cloud and GPU are endpoints of one runtime.
AWS Strands uses the identifier strands, not aws-strands.

runtime owns the actor's scheduler controls. run(timeout_s=...) is inherited
from the root; graph branching differs from runtime max_concurrency. runtime,
framework and internal scheduler settings use Pydantic. Agent policy
also validates before effects; leave omitted options omitted. Do not generate
extra scheduler/policy constructors. SDK option mappings are shallowly frozen;
live clients/sessions/callbacks remain objects, not reconstructable JSON data.

Use explicit model, region/endpoint and environment credentials. Provider model
preferences are task-specific; preserve the user's chosen models. Never silently
fallback. SDK-specific handoffs, sessions/guardrails, MCP and A2A enter through
framework agent_kwargs/run_kwargs and require separate evidence.

Check installed, configured, supported and live-verified separately. A GPU
server declaration is not GPU inference proof. Bedrock API key/bearer and IAM
are distinct authentication profiles; an API-key test does not certify IAM.

Prefer flat typed Tool parameters with closed Pydantic models for nested data.
OpenAI Agents strict function schemas reject unconstrained dict inputs. The dev7 Quantity contract checks a single BaseModel parameter with explicit
input_schema in all three Python SDK actor paths. Other shapes need their own
evidence; do not generalize that test to every Pydantic feature or live provider. The dev3 learning cases validate flat signatures
against all three Python actor paths and selected real-provider projections.
Tool-event output may retain a provider evidence envelope; validate its tool
identity, success and exact business data before passing it to the next node.

Graph, START, END, Command and Send are original LangGraph objects reexported by toolkit. Pydantic is imported directly. Typed node callbacks receive models and return partial updates; do not generate show helpers. Use result.human_results() for a bounded human view of the same RunResult. State includes finite JSON channels; validators are retained at input, node and output boundaries.
