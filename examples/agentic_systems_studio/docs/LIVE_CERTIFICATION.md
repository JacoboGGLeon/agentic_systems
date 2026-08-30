# Live certification baseline

Agentic Systems 2.1 was certified with the provider/framework contract matrix:

- OpenAI, Ollama, Bedrock and vLLM model providers;
- native, LangGraph, OpenAI Agents and Strands frameworks;
- Bedrock through both API-key and AWS credential-chain/IAM routes;
- vLLM with Unsloth Qwen3 4B Instruct 2507 on a Colab GPU.

Release evidence belongs to the top-level release bundle, not inside Studio. The
Studio application consumes the same public runtime, Agent, System and RunResult
contracts; it does not claim that every local ADA environment has the same network,
IAM, model-access or GPU configuration. Run the direct notebook in the target
environment before exposing the Streamlit entry point.
