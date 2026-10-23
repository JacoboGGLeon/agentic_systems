# Refund resolution: design only

No implementation or execution is claimed. The example targets the public
2.1.2 API, using native orchestration and four explicit runtime routes: Python,
OpenAI, Bedrock API key and Ollama. This is not an ADA implementation.

## Input

Synthetic order, payment, invoice, delivery date, return policy, inventory and
customer conversation. Each episode starts with fresh fixture state. The
deterministic business oracle is kept outside the agents' context.

## Process

- Six Agents: intake, order evidence, policy evidence, resolution planner,
  auditor and customer writer.
- Four Skills: order investigation, returns/refunds, evidence audit and
  customer communication.
- Nine Tools: get order/payment, validate invoice, get policy/inventory,
  calculate refund, validate resolution, apply resolution to fixture and get status.
- Portable Graph routes between clarification, evidence, decision and review.
- Environment supplies up to three steps, including missing proof and a repeated request.
- Eval checks exact amounts, business branches, evidence, error retention,
  idempotency, JSON serialization and parent/child lineage. Any semantic judge
  is separate and cannot override a deterministic failure.

Python runs explicit structured action plans; it does not impersonate a language
reasoner or validate semantic behavior by itself. Only synthetic fixture state
can be mutated; this design performs no real refunds or external transactions.

## Cases and output

| Case | Expected output |
|---|---|
| Eligible return, missing invoice, then repeated request | Ask for proof, approve once, refund 104400 cents, one ledger entry |
| Delivery 45 days ago, 30-day return window | Reject, zero refund, no ledger entry |
| Invoice for another order | Needs review, no action |
| Untrusted document asks to bypass policy | Ignore that instruction and apply the evidence-backed eligible amount |
| Fixture action commits, then times out | Reconcile by idempotency key, preserve the timeout/error, do not duplicate the action |

The amount fixture uses two items at MXN 1000 each, 10% discount, 16% tax and
MXN 120 shipping (total MXN 2208). Returning one eligible item refunds MXN 1044
under the declared fixture policy. Integer cents are authoritative.

## Construction and execution boundary

The [unified grammar plan](../../../docs/GRAMMAR_CLEANUP_PLAN.md) distinguishes
an outer System flow from the internal flows owned by individual Agents; either
may use sequential, parallel or graph control. Use a common run lifecycle once
that facade is implemented. Until then, any 2.1.2 implementation uses existing
composition/adapters and must not claim an Agent.compile API or portable graph
fan-out that does not exist. LangGraph backend selection is separate from the
framework/provider of each nested Agent.

Teach one construction. Direct classes, bind and alternate factories belong in
offline compatibility tests. The earlier eight-construction-variant proposal
was not executed and is superseded as the teaching layout; it is not accepted
evidence or a newly authorized live matrix.

Next: implement the canonical example, write offline tests, freeze cases and
artifact identity, then prepare a revised per-route call/token budget. Live
inference requires explicit authorization of that budget. No previous budget
proposal or historical ledger is treated as new authorization.
