import agentic_systems as lab


def test_compare_accepts_keys_for_compact_traces():
    rows = [
        {"run_ok": True, "engine": "python-runtime", "mode": "tool", "usage": {"requests": 1}},
        {"run_ok": True, "engine": "python-runtime", "mode": "tool", "usage": {"requests": 1}},
    ]

    compared = lab.compare(rows, keys=["run_ok", "engine", "mode", "usage"])

    assert compared["ok"] is True
    assert compared["count"] == 2
    assert compared["same"]["engine"] is True
    assert compared["runs"][0]["usage"] == {"requests": 1}


def test_direct_tool_usage_is_reported():
    @lab.tool
    def add_one(x: int) -> dict:
        return {"operation": "add_one", "result": x + 1}

    result = add_one.run({"x": 1})

    assert result.usage == {"requests": 1}
    assert result.trace("compact")["usage"] == {"requests": 1}
