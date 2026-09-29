"""Generate every synthetic dataset in this repo (seeded, so output is reproducible).

Nothing here is client data. Names, IDs, emails and volumes are invented; volumes are
shaped to match the scale of the real programmes described in each project README.
Run:  python tools/generate_datasets.py
"""
import csv, json, random, uuid
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)
ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 1)  # fixed "as of" date so reports are reproducible

APPS = ["HR Portal", "Payroll", "Expense Tool", "Travel Booking", "CRM", "Service Desk", "Wiki", "Code Review",
        "Data Lake Console", "BI Dashboards", "Learning Portal", "Benefits", "Procurement", "Contract Vault",
        "Marketing Suite", "Survey Tool", "Design Studio", "Chat Archive", "Vendor Portal", "Asset Tracker",
        "Timesheets", "Recruiting", "Board Portal", "Legal Hold", "Treasury", "Audit Workbench", "Field Service",
        "Partner Hub", "Status Page", "Password Vault", "Ticket Analytics", "Customer Community", "E-Signature",
        "Event Booking", "Knowledge Base", "Store Admin", "Loyalty Console", "Warehouse Mgmt", "Fleet Tracker",
        "Print Management", "Visitor Mgmt", "Floor Planner", "Lab Scheduler", "Grant Tracker", "Claims Portal",
        "Tax Engine", "Risk Register", "Policy Library", "Mobile MDM Console", "API Gateway Admin", "Log Search",
        "Backup Console", "Firewall Manager", "Certificate Portal", "Research Wiki", "Store Locator Admin",
        "Pricing Engine", "Returns Portal", "Supplier Scorecard", "Onboarding Hub"]


def saml():
    out = []
    for i, name in enumerate(APPS):
        days = random.choice([-3, 0, 1, 2, 5, 6, 12, 18, 25, 29, 40, 44, 55, 58, 75, 88] + [random.randint(91, 700) for _ in range(20)])
        owner = None if random.random() < 0.18 else f"owner{i:02d}@contoso.example"
        out.append({
            "appId": str(uuid.UUID(int=random.getrandbits(128))),
            "displayName": name,
            "owner": owner,
            "criticality": random.choices(["P1", "P2", "P3"], [0.25, 0.4, 0.35])[0],
            "certThumbprint": "%040X" % random.getrandbits(160),
            "certExpiry": (TODAY + timedelta(days=days)).isoformat(),
            "metadataUrlConsumed": random.random() < 0.45,  # SP re-reads federation metadata automatically
            "signInsLast30d": 0 if random.random() < 0.12 else random.randint(20, 40000),
        })
    p = ROOT / "saml-cert-lifecycle/data/enterprise_apps.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"asOf": TODAY.isoformat(), "value": out}, indent=2))


def secrets():
    rules = [("Azure storage account key", "critical", 9), ("AWS access key", "critical", 7), ("Client secret in config", "critical", 14),
             ("Connection string with password", "serious", 16), ("Private key (PEM)", "critical", 5), ("Generic high-entropy token", "warning", 12),
             ("Personal access token", "serious", 8), ("Slack/Teams webhook URL", "warning", 6)]
    repos = [f"repo-{n:02d}" for n in range(1, 38)]
    rows, fid = [], 1
    random.shuffle(repos)
    for rule, sev, count in rules:
        for _ in range(count):
            rows.append({"finding_id": f"F{fid:03d}", "repo": random.choice(repos), "file": random.choice(
                ["appsettings.json", "config/dev.yaml", ".env", "scripts/deploy.ps1", "notebooks/etl.ipynb", "terraform/main.tf", "src/client.py", "docker-compose.yml"]),
                "line": random.randint(3, 400), "rule": rule, "severity": sev,
                "stage_caught": random.choices(["pre-commit", "pull request", "nightly full scan"], [0.45, 0.4, 0.15])[0],
                "status": random.choices(["rotated & removed", "removed (test value)", "false positive"], [0.78, 0.14, 0.08])[0]})
            fid += 1
    # make sure all 37 repos appear at least once, matching the real 77 findings / 37 repos scale
    for i, r in enumerate(repos):
        rows[i % len(rows)]["repo"] = r
    p = ROOT / "secrets-scanner/data/findings_sample.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)


def incidents():
    cats = {  # category: (weight, minutes if manual, has runbook)
        "Account lockout": (0.28, 12, True), "Group sync failure": (0.14, 35, True), "License assignment error": (0.13, 15, True),
        "MFA re-registration": (0.16, 10, True), "Stale device object": (0.09, 8, True), "Password expiry for service account": (0.07, 40, True),
        "Conditional Access block (unknown cause)": (0.06, 45, False), "Other / novel issue": (0.04, 60, False)}
    months = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
    rows, n = [], 1
    for mi, m in enumerate(months):
        agent_live = mi >= 2  # agent went live in May; Mar-Apr are the manual baseline
        for _ in range(random.randint(230, 250)):
            c = random.choices(list(cats), [v[0] for v in cats.values()])[0]
            w, mins, rb = cats[c]
            auto = agent_live and rb and random.random() < 0.95
            rows.append({"incident_id": f"INC{n:05d}", "month": m, "category": c, "handled_by": "agent" if auto else "engineer",
                         "agent_confidence": round(random.uniform(0.86, 0.99), 2) if auto else (round(random.uniform(0.3, 0.84), 2) if agent_live else ""),
                         "engineer_minutes": 2 if auto else mins + random.randint(-3, 8)})
            n += 1
    p = ROOT / "self-healing-ops/data/incidents.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)


def dsr():
    monthly = {"2025-09": 4120, "2025-10": 4380, "2025-11": 5060, "2025-12": 6010, "2026-01": 4870, "2026-02": 4210,
               "2026-03": 4330, "2026-04": 4450, "2026-05": 4290, "2026-06": 4520, "2026-07": 4610, "2026-08": 4480}
    mix = {"access": 0.34, "erasure": 0.41, "rectification": 0.1, "marketing opt-out": 0.15}
    rows = []
    for m, total in monthly.items():
        row = {"month": m, "total": total}
        left = total
        for i, (k, share) in enumerate(mix.items()):
            v = left if i == len(mix) - 1 else round(total * share * random.uniform(0.95, 1.05))
            row[k] = v; left -= v
        rows.append(row)
    p = ROOT / "gdpr-dsr-automation/data/dsr_monthly_volume.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    # 250 individual requests for the processing demo
    reqs, start = [], datetime(2026, 8, 1, 8)
    for i in range(250):
        t = random.choices(list(mix), list(mix.values()))[0]
        reqs.append({"request_id": f"DSR-{20260800+i}", "type": t, "received_at": (start + timedelta(minutes=random.randint(0, 60*24*30))).isoformat(timespec="minutes"),
                     "market": random.choice(["US", "CA", "UK", "DE", "LU", "AU", "NZ", "JP", "CN"]),
                     "subject_email": f"user{random.randint(1000, 999999)}@example.com",
                     "identity_verified": random.random() > 0.06,
                     "duplicate_of": ""})
    for i in random.sample(range(20, 250), 9):
        reqs[i]["duplicate_of"] = reqs[i - random.randint(1, 15)]["request_id"]
    p = ROOT / "gdpr-dsr-automation/data/dsr_requests_sample.json"
    p.write_text(json.dumps(reqs, indent=2))


def signins():
    rows, t = [], datetime(2026, 8, 3, 0, 0)
    detections = ["Impossible travel", "Token replay", "Sign-in from anonymising proxy", "MFA fatigue (repeated denials)", "Leaked credentials match"]
    for i in range(400):
        t += timedelta(minutes=random.randint(20, 160))
        # latency breakdown in ms: alert -> playbook trigger, playbook -> Graph revoke call, Graph response
        trig = max(120, int(random.gauss(420, 140)))
        call = max(80, int(random.gauss(260, 90)))
        graph = max(90, int(random.gauss(380, 160)))
        if random.random() < 0.02:  # the odd throttled call
            graph += random.randint(900, 1500)
        rows.append({"alert_id": f"AL{i:04d}", "detected_at": t.isoformat(timespec="seconds"), "detection": random.choice(detections),
                     "user": f"u{random.randint(10000, 99999)}@contoso.example", "risk": random.choices(["high", "medium"], [0.6, 0.4])[0],
                     "trigger_ms": trig, "playbook_ms": call, "graph_ms": graph})
    p = ROOT / "session-revocation/data/risk_alerts_sample.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    saml(); secrets(); incidents(); dsr(); signins()
    print("Synthetic datasets written.")
