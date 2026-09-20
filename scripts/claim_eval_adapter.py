"""Connect application claim review to the existing toolkit Eval interface."""

import json
import agentic_systems as toolkit
from scripts.claim_evaluator import build
from agentic_systems.usage import merge_usage


def make_claim_judge(provider, framework, model):
    evaluator = build(provider, framework, model)

    class Judge:
        def __init__(self):
            self.runs = []

        def run(self, request, **kwargs):
            case = request["case"]["input"]
            answer = request["candidate"]["answer"]["text"]
            report = evaluator.evaluate(answer, case["evidence"])
            self.runs.append(report)
            usage = merge_usage(
                *(item["result"]["usage"] for item in report.get("runs", []))
            )
            if not report["execution_ok"]:
                return toolkit.RunResult(
                    ok=False,
                    text=report["failure"],
                    data={},
                    usage=usage,
                    engine=provider,
                    model=model,
                    meta={"claim_review": report, "framework_adapter": framework},
                )
            verdict = report["verdict"]
            criteria = {
                "grounding": float(verdict["grounding"] == "pass"),
                "clarity": float(verdict["clarity"]),
            }
            # Render records, not model-authored explanations. Their relevance is
            # still a semantic judgment, and unknown never becomes a pass.
            rationale = json.dumps(
                {"grounding": verdict["grounding"], "records": verdict["records"]},
                ensure_ascii=False,
            )
            findings = [
                {
                    "criterion": name,
                    "evidence": f"Claim review reports {verdict['grounding']} grounding."
                    if name == "grounding"
                    else "Separate clarity review did not pass.",
                }
                for name, score in criteria.items()
                if not score
            ]
            return toolkit.RunResult(
                ok=True,
                data={
                    "criteria": criteria,
                    "score": sum(criteria.values()) / len(criteria),
                    "findings": findings,
                    "rationale": rationale,
                },
                usage=usage,
                engine=provider,
                model=model,
                meta={"claim_review": report, "framework_adapter": framework},
            )

    return Judge()
