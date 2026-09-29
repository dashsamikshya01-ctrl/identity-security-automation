"""Replays six months of synthetic incidents through the triage logic used by the n8n agent.

The real workflow runs in n8n: ServiceNow webhook -> LLM classification -> this decision logic ->
Graph/PowerShell action -> verification -> ticket update. This script reproduces the decision and
the savings maths so the design can be reviewed and tested without a tenant.

    python triage.py
"""
import csv, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import svgchart as sc  # noqa: E402

CONFIDENCE_FLOOR = 0.85   # below this, the agent drafts a diagnosis but a human acts


def decide(category, confidence, has_runbook, requires_approval=False):
    if not has_runbook:
        return "escalate: no approved runbook"
    if confidence < CONFIDENCE_FLOOR:
        return "escalate: low confidence, diagnosis attached"
    if requires_approval:
        return "auto-fix after one-click approval"
    return "auto-fix and verify"


def main():
    rows = list(csv.DictReader((HERE / "data/incidents.csv").open()))
    months = sorted({r["month"] for r in rows})
    eng = defaultdict(float); agent = defaultdict(int); total = defaultdict(int)
    for r in rows:
        total[r["month"]] += 1
        eng[r["month"]] += float(r["engineer_minutes"]) / 60
        agent[r["month"]] += r["handled_by"] == "agent"
    base = sum(eng[m] for m in months[:2]) / 2
    after = sum(eng[m] for m in months[2:]) / len(months[2:])
    print(f"{'Month':8} {'Incidents':>9} {'By agent':>9} {'Engineer hrs':>13}")
    for m in months:
        print(f"{m:8} {total[m]:>9} {agent[m]:>9} {eng[m]:>13.0f}")
    print(f"\nBaseline {base:.0f} h/month -> {after:.0f} h/month after go-live: "
          f"{base-after:.0f} h saved a month ({(base-after)/base:.0%} less)")
    labels = ["Mar", "Apr", "May", "Jun", "Jul", "Aug"]
    sc.bars(str(HERE / "docs/engineer_hours.svg"), "Engineer hours spent on recurring incidents",
            "Synthetic replay. Agent goes live in May; March and April are the manual baseline",
            labels, [round(eng[m]) for m in months],
            [sc.STATUS["neutral"]] * 2 + [sc.AQUA] * 4, unit=" h")
    sc.grouped(str(HERE / "docs/who_handled.svg"), "Who closed each incident",
               "Synthetic replay, incidents per month", labels,
               [("Engineer", sc.BLUE, [total[m] - agent[m] for m in months]), ("Agent", sc.ORANGE, [agent[m] for m in months])])
    for c, conf, rb in [("Account lockout", 0.93, True), ("Account lockout", 0.62, True), ("Other / novel issue", 0.97, False)]:
        print(f"  decide({c!r}, {conf}) -> {decide(c, conf, rb)}")


if __name__ == "__main__":
    main()
