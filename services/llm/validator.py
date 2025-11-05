from apps.api.schemas_llm import TradeAnalysisV2


def _add_warning(ta: TradeAnalysisV2, msg: str):
    r = ta.risk or {}
    warnings = set(r.get("warnings", []))
    warnings.add(msg)
    r["warnings"] = sorted(list(warnings))
    ta.risk = r


def enforce_policy_and_sanity(ta: TradeAnalysisV2, facts: dict) -> TradeAnalysisV2:
    # 1) Spread override
    max_cents = facts["policy_limits"]["spread_cents_max"]
    max_bps = facts["price"] * facts["policy_limits"]["spread_bps_max"]
    if facts["spread"] > min(max_cents, max_bps):
        ta.verdict_intraday = "SKIP"
        ta.verdict_swing_1to5d = "SKIP"
        _add_warning(ta, "Policy override: spread too wide")

    # 2) Pattern gating (no inference allowed when detector is null)
    pd = facts.get("pattern_detected")
    state = (ta.pattern or {}).get("state")
    if pd is None and state in ("BREAKOUT", "PULLBACK"):
        ta.verdict_swing_1to5d = "SKIP"
        _add_warning(ta, "Pattern inference not allowed")

    # 3) Feasibility checks (basic)
    try:
        entry = float(ta.plan["entry_price"])
        stop = float(ta.plan["stop_price"])
        tick = float(facts.get("tick_size", 0.01))
        if stop >= entry or (entry - stop) < tick:
            ta.verdict_intraday = "SKIP"
            _add_warning(ta, "Invalid stop/entry distance")
    except Exception:
        pass

    # 4) Evidence consistency auto-downgrade
    # If CAR non-sig + participation=LOW + pattern=CANDIDATE => swing SKIP
    try:
        car_sig = bool(facts.get("evidence", {}).get("event_study", {}).get("significant", False))
        part_q = (ta.participation or {}).get("quality", "LOW")
        patt = (ta.pattern or {}).get("state", "CANDIDATE")
        if (not car_sig) and part_q == "LOW" and patt in ("CANDIDATE",):
            ta.verdict_swing_1to5d = "SKIP"
            _add_warning(ta, "Evidence rule: weak CAR & participation & pattern candidate")
    except Exception:
        pass

    return ta

