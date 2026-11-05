# Lineage and Memory that change decisions · 2.1.5

**Input → process → output:** payment PAY-001 arrives with 5000 MXN cents. One Agent computes a fee of 50; another checks its evidence and decides. The first run approves. The second receives exactly the same input and requests duplicate review because Memory retained the previous episode.

Everything uses deterministic Python coordinated by LangGraph: no models, keys or inference. Install local SDK **2.1.5** and its dependencies first. The notebook installs nothing. Run cells in order from a clean kernel.

| Channel | Contents | Decision role |
|---|---|---|
| State | payment_id, amount, fee, decision | Current payment data |
| Context.data / sources | Policy and provenance | Fee and limit |
| Context.lineage | Preceding Agent evidence | Require and verify computation |
| Context.episodes | Prior execution with compact lineage | Detect prior approval of the same payment |

Context captures are separate inspection records, never Graph state. Lineage records observations, not private thoughts.

## 1. Small state and explicit Tools

strict=True rejects type coercion; extra="forbid" rejects unexpected fields. Optional fields are outputs not yet computed. The reviewer does not trust a fee solely because it appears in state: successful fees lineage and consistency with current policy are required. It then checks structured evidence of previous approvals in Memory.

## 2. One Graph per Agent and one for the System

fees organizes computation; reviewer organizes the decision. The System connects them in that order. There is no manual global-trace lookup or history attached to Payment. Context is delivered when each Tool executes.

## 3. Policy and shared Memory from the System

Memory retains up to two local episodes. Entry snapshots of prior episodes are inherited by Agents. The System remembers its result on completion. compile() prepares the harness without executing Tools or writing Memory.

## 4. First execution: current evidence, no history yet

fees receives empty lineage and episodes. reviewer receives current fees evidence but no previous episode, so PAY-001 can be approved.

### Exact Context received in the first execution

The complete object is shown: policy, sources, current lineage and episodes.

## 5. Second execution: identical input changes the decision through Memory

The same harness and Memory are reused. Fee and limit remain unchanged. reviewer finds previous approval of PAY-001 in episode lineage and returns review_duplicate. Execution succeeds: requesting review is a business decision, not a runtime failure.

### Exact Context received in the second execution

Both Tools receive the first episode in episodes. Only reviewer also receives current fees evidence in lineage. The first Agent does not confuse previous-run history with work already performed in this run.

## 6. Controls demonstrating causal dependence

1. Same input and Graph without Memory: approve again.
2. fee=50 in state without preceding fees lineage: fail.
3. fees records fee=51: lineage exists but contradicts policy, so fail.

Controls use independent Systems and do not write this example’s Memory.

## 7. Verified summary: four Context objects, four business fields

## 8. Environment: Memory evolves between episodes

Process PAY-002 twice through the same System. observe supplies only payment fields; expected_decision stays outside System input as an Environment oracle. update records an explicit reward and captures Memory separately. Capacity is two: episode count stops growing but IDs change. No additional Memory is attached to Environment; we observe the System’s Memory.

### Exact Context objects during Environment

The second Tool pair receives the first PAY-002 episode. The observation list is not added to state.

## 9. Eval: live episodes within a case, isolated Memory between cases

Evaluate the same Environment twice, each case repeating PAY-003. Each starts with the same production Memory containing PAY-002. Within each case, first approval of PAY-003 feeds the second episode and changes its decision. The next case returns to production baseline and approves its first PAY-003.

The check reads Memory captured by closure and also receives the private case view. After Eval, exact equality of production Memory is required. Audit lists still accumulate observations: Eval does not isolate files, arbitrary variables, SDK clients or external effects.

### Exact Context objects during Eval

Eight Context objects are shown: two cases × two episodes × two Agents. Both cases start with the same production IDs; writes from one case do not reach the other.

## Scope and limits

Agent/System lineage can provide context to another unit. Context may also contain policy and external sources; lineage alone is only a projection. We inspect complete objects, but decisions read structured fields rather than human_results text.

Memory is local, bounded and summarized. Absence of an approval in retained episodes does **not prove** it never happened. This demonstration is not a persistent idempotency ledger and does not prevent concurrent duplicates. The four business fields contain no Context, episodes or RunResult trees; internally the graph uses bounded evidence references.

Validation covers this deterministic scenario and its controls. It does not certify external providers or new versions and publishes no artifact.

[Base two-Agent program](example.py); Environment and Eval are declared directly in this notebook. [Explanation and evidence](README.md).

[Executable notebook](01_lineage_memory_decisions.ipynb) · [Complete reading view](01_lineage_memory_decisions.md) · [Program](example.py).

Historical validation: [report](../../revisions/2.1.4/grammar-dev7/lineage-memory/REPORT.md), [serialized evidence](../../revisions/2.1.4/grammar-dev7/lineage-memory/evidence.json), [fresh-kernel records](../../revisions/2.1.4/grammar-dev7/lineage-memory/notebook-validation/). Historical results retain their original wheel identity.
