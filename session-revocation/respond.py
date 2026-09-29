"""Compromised-session response, as run by the Logic Apps playbook, plus a latency report.

Playbook steps (each one is a Logic Apps action; shown here as the Graph calls it makes):
  1. POST /users/{id}/revokeSignInSessions          -> invalidates refresh tokens and session cookies
  2. POST /identityProtection/riskyUsers/confirmCompromised -> raises user risk so Conditional Access
                                                         forces a secure password change on next sign-in
  3. Comment on the Sentinel incident with what was done and when

    python respond.py        # latency report over data/risk_alerts_sample.csv (synthetic)
"""
import csv, statistics, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import svgchart as sc  # noqa: E402

GRAPH = "https://graph.microsoft.com/v1.0"


def playbook_calls(user_id):
    return [("POST", f"{GRAPH}/users/{user_id}/revokeSignInSessions", None),
            ("POST", f"{GRAPH}/identityProtection/riskyUsers/confirmCompromised", {"userIds": [user_id]})]


def main():
    rows = list(csv.DictReader((HERE / "data/risk_alerts_sample.csv").open()))
    total = [int(r["trigger_ms"]) + int(r["playbook_ms"]) + int(r["graph_ms"]) for r in rows]
    q = statistics.quantiles(total, n=100)
    under2 = sum(t < 2000 for t in total) / len(total)
    print(f"{len(rows)} alerts. Median {statistics.median(total)/1000:.2f}s, p95 {q[94]/1000:.2f}s, "
          f"under 2s: {under2:.1%}")
    edges = [0, 500, 750, 1000, 1250, 1500, 1750, 2000, 10_000]
    labels = ["<0.5s", "0.5–0.75", "0.75–1", "1–1.25", "1.25–1.5", "1.5–1.75", "1.75–2", "2s+"]
    counts = [sum(lo <= t < hi for t in total) for lo, hi in zip(edges, edges[1:])]
    sc.bars(str(HERE / "docs/latency.svg"), "Seconds from detection to sessions revoked",
            f"{len(rows)} synthetic alerts · median {statistics.median(total)/1000:.1f}s · p95 {q[94]/1000:.1f}s · "
            f"{under2:.0%} under 2 seconds", labels, counts,
            [sc.BLUE] * 7 + [sc.STATUS["serious"]])
    print("Example playbook calls:", *playbook_calls("00000000-0000-0000-0000-000000000000"), sep="\n  ")


if __name__ == "__main__":
    main()
