# Recorded issues and verification limits · 2.1.5

## Ollama native endpoint coexistence

[The connection correction](../revisions/2.1.4/ollama-connection-fix/01/REPORT.md) resolves connection settings per actor and closes owned clients without changing global environment variables. Its [live recheck](../revisions/2.1.4/ollama-connection-fix/01/live/REPORT.md) passed pilots, two sync runs, two arun runs and the original local/native financial notebook. Those results apply to the recorded artifact hashes.

Earlier mixed-profile execution failed because native Ollama used global endpoint/key settings rather than explicit connection data; the budget counter rejected the incompatible route before transport. That failure remains recorded. Switching to Strands/local and OpenAI Agents/cloud was a workaround, not proof that native was fixed. The subsequent SDK correction and live recheck cover that route separately. [Provider fixes](../revisions/2.1.4/problem-fixes/01/REPORT.md) distinguish newer verification from historical failures.

## Ollama Cloud interoperability

The historical three-framework-interop case uses Gemma4:31b and three actors in one System. Input value=42/trail=[] should produce value=45/trail=[native, openai-agents, strands]. In the recorded failed cloud attempt, native invoked mark_native and recorded value=43, then returned an empty model output. The System retained the failure. Successful Tool evidence is not acceptance of the complete run; the interaction between final response, loop completion and tool contract needs its own analysis.

Cloud successes in basic notebooks, refunds, Studio or MCP/A2A do not substitute for this exact case. See the [historical attempt summary](../revisions/2.1.4/contracts-dev5/REPORT.md).

## Bedrock credentials and nullable business input

Early notebooks failed with expired credentials. A later attempt recorded 14 failed requests after the service rejected the credential format. Initial local checks recognized only long ABSK keys, not short bedrock-api-key keys; eight offline regressions corrected support for both. A short-key pilot subsequently restored authentication. Credentials are never printed or saved in evidence.

Basic matrix/refund/MCP cases passed, but the required nullable-amount business case failed across native, OpenAI Agents and Strands: Pydantic received a missing amount instead of the required amount:null field. Missing data was not repaired with a computed value and authentication was not silently changed to IAM.

A historical Studio campaign stopped at 148/150 requests because two remaining requests could not cover its observed three-request protocol. [Recheck evidence](../revisions/2.1.4/contracts-dev5/bedrock-recheck.md) records that budget boundary. Later campaigns must be assessed by their own report, not this old balance.

Investigation confirmed the prompt/schema contained the null but the service response omitted the field before validation. [Build 03](../revisions/2.1.4/contracts-dev5/bedrock-null-fix/REPORT.md) enabled strict tool use for the selected Qwen and compatible schemas without changing the business contract. Offline regressions still reject missing fields before effects. This corrects request construction but does not itself prove live null preservation.

## Current acceptance boundary

The current SDK is 2.1.5. The [2026-11-08 report](VALIDATION_215_20261108.md)
records scoped Bedrock IAM and GPU vLLM campaigns, with ADA separately labeled
operator-reported. These do not close the historical nullable-input or Ollama
cloud-interoperability cases above. Memory and continuations remain process-local.
CI and mutation acceptance remain commit-specific. See [status](STATUS_214.md).
