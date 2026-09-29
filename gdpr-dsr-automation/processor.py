"""GDPR data subject request (DSR) pipeline: validate, de-duplicate, route, fulfil, evidence.

In production, OneTrust publishes each verified request to Azure Event Hub; a Python consumer
(first AWS Lambda, now a GitHub Actions job) runs the steps below and calls back to OneTrust.
Here the same steps run over data/dsr_requests_sample.json (synthetic).

    python processor.py
"""
import csv, hashlib, json, sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import svgchart as sc  # noqa: E402

SLA_DAYS = 30  # GDPR Art. 12(3): one month, extendable in complex cases
SYSTEMS = {    # where each request type has to act
    "access": ["Azure AD B2C profile", "Commerce orders", "Marketing platform", "Support tickets"],
    "erasure": ["Azure AD B2C profile", "Commerce orders (anonymise)", "Marketing platform", "Support tickets", "Log platforms (masked)"],
    "rectification": ["Azure AD B2C profile", "Commerce orders"],
    "marketing opt-out": ["Marketing platform"],
}


def pseudonym(email):  # audit log never stores the raw email
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def process(req):
    if req["duplicate_of"]:
        return {"status": "merged", "note": f"duplicate of {req['duplicate_of']}", "systems": []}
    if not req["identity_verified"]:
        return {"status": "on hold", "note": "identity not verified; OneTrust asks the requester again", "systems": []}
    due = datetime.fromisoformat(req["received_at"]) + timedelta(days=SLA_DAYS)
    return {"status": "fulfilled", "note": f"due {due.date()}", "systems": SYSTEMS[req["type"]]}


def main():
    reqs = json.loads((HERE / "data/dsr_requests_sample.json").read_text())
    audit, outcome = [], Counter()
    for r in reqs:
        res = process(r)
        outcome[res["status"]] += 1
        audit.append({"request_id": r["request_id"], "subject": pseudonym(r["subject_email"]), "type": r["type"],
                      "market": r["market"], **res})
    (HERE / "audit_log.json").write_text(json.dumps(audit, indent=2))
    print(f"{len(reqs)} requests processed: {dict(outcome)}")
    print(f"System actions executed: {sum(len(a['systems']) for a in audit)}")

    rows = list(csv.DictReader((HERE / "data/dsr_monthly_volume.csv").open()))
    labels = [datetime.strptime(r["month"], "%Y-%m").strftime("%b") for r in rows]
    vals = [int(r["total"]) for r in rows]
    peak = max(vals)
    sc.bars(str(HERE / "docs/monthly_volume.svg"), "Data subject requests handled each month",
            "Synthetic 12-month volume at real-world scale; the December bar is the holiday peak",
            labels, vals, [sc.ORANGE if v == peak else sc.BLUE for v in vals])
    mix = Counter()
    for r in rows:
        for k in SYSTEMS:
            mix[k] += int(r[k])
    top = mix.most_common()
    sc.hbars(str(HERE / "docs/request_mix.svg"), "What people ask for",
             "Requests by type over 12 months (synthetic)", [k.capitalize() for k, _ in top], [v for _, v in top], color=sc.AQUA)


if __name__ == "__main__":
    main()
