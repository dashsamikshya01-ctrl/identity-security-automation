"""SAML signing-certificate lifecycle: find, notify, ticket, renew.

Offline by default: reads data/enterprise_apps.json (synthetic) and prints the plan it would execute.
With --live it reads the same fields from Microsoft Graph (needs an app registration with
Application.ReadWrite.All; credentials come from environment variables, never from code).

    python lifecycle.py            # dry run on synthetic data, writes docs/*.svg and report.json
    python lifecycle.py --live     # real tenant (dry run unless --apply is also given)
"""
import argparse, json, os, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import svgchart as sc  # noqa: E402

NOTIFY_DAYS = (90, 60, 30, 7)      # owner reminders
RENEW_AT_DAYS = 1                   # create + activate new cert 24h before expiry
GRAPH = "https://graph.microsoft.com/v1.0"


def load_offline():
    d = json.loads((HERE / "data/enterprise_apps.json").read_text())
    return date.fromisoformat(d["asOf"]), d["value"]


def load_live():  # pragma: no cover - needs a tenant
    import requests
    tok = requests.post(f"https://login.microsoftonline.com/{os.environ['TENANT_ID']}/oauth2/v2.0/token", data={
        "client_id": os.environ["CLIENT_ID"], "client_secret": os.environ["CLIENT_SECRET"],
        "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    url = f"{GRAPH}/servicePrincipals?$filter=preferredSingleSignOnMode eq 'saml'&$select=id,appId,displayName,keyCredentials,notes&$expand=owners($select=mail)"
    apps = []
    while url:
        page = requests.get(url, headers=h).json()
        for sp in page["value"]:
            signing = [k for k in sp.get("keyCredentials", []) if k.get("usage") == "Verify"]
            if not signing:
                continue
            cur = max(signing, key=lambda k: k["endDateTime"])
            apps.append({"appId": sp["appId"], "spId": sp["id"], "displayName": sp["displayName"],
                         "owner": (sp.get("owners") or [{}])[0].get("mail"), "criticality": "P2",
                         "certExpiry": cur["endDateTime"][:10], "metadataUrlConsumed": False, "signInsLast30d": None})
        url = page.get("@odata.nextLink")
    return date.today(), apps


def classify(app, today):
    days = (date.fromisoformat(app["certExpiry"]) - today).days
    if app.get("signInsLast30d") == 0:
        return days, "stale", "Flag for decommission review (no sign-ins in 30 days)"
    if days < 0:
        return days, "expired", "Incident: renew now and page owner"
    if days <= RENEW_AT_DAYS:
        return days, "renew", "Create new signing cert and make it active"
    if not app.get("owner"):
        return days, "ownerless", "Open ServiceNow ticket to assign an owner"
    for d in sorted(NOTIFY_DAYS):
        if days <= d:
            return days, f"notify-{d}", f"Email owner: certificate expires in {days} days"
    return days, "healthy", "No action"


def plan(apps, today):
    rows = []
    for a in apps:
        days, bucket, action = classify(a, today)
        rows.append({**a, "daysLeft": days, "bucket": bucket, "action": action})
    return sorted(rows, key=lambda r: r["daysLeft"])


def servicenow_payload(app):
    return {"short_description": f"SAML app '{app['displayName']}' has no owner; signing cert expires {app['certExpiry']}",
            "assignment_group": "Identity Operations", "category": "Identity", "urgency": 1 if app["criticality"] == "P1" else 2,
            "u_app_id": app["appId"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true"); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    today, apps = load_live() if a.live else load_offline()
    rows = plan(apps, today)

    order = ["expired", "renew", "notify-7", "notify-30", "notify-60", "notify-90", "ownerless", "stale", "healthy"]
    counts = {b: sum(r["bucket"] == b for r in rows) for b in order}
    print(f"As of {today}: {len(rows)} SAML apps scanned\n")
    for r in rows:
        if r["bucket"] != "healthy":
            print(f"  {r['daysLeft']:>4}d  {r['criticality']}  {r['displayName']:<22} -> {r['action']}")
    tickets = [servicenow_payload(r) for r in rows if r["bucket"] == "ownerless"]
    (HERE / "report.json").write_text(json.dumps({"asOf": today.isoformat(), "summary": counts, "servicenowTickets": tickets,
                                                  "actions": [r for r in rows if r["bucket"] != "healthy"]}, indent=2))
    if a.live and a.apply:
        print("\n--apply given: renewals would call POST /servicePrincipals/{id}/addTokenSigningCertificate "
              "then PATCH preferredTokenSigningKeyThumbprint (see README, 'Safe rollover').")

    labels = ["Expired", "≤1 day", "≤7 d", "≤30 d", "≤60 d", "≤90 d", "No owner", "Stale", "Healthy"]
    cols = [sc.STATUS[s] for s in ["critical", "critical", "serious", "serious", "warning", "warning", "serious", "neutral", "good"]]
    sc.bars(str(HERE / "docs/expiry_buckets.svg"), "Where every SAML app stands today",
            f"{len(rows)} apps in the synthetic tenant, bucketed by days to signing-cert expiry and ownership",
            labels, [counts[b] for b in order], cols)
    print(f"\nWrote report.json with {len(tickets)} ServiceNow ticket payloads, and docs/expiry_buckets.svg")


if __name__ == "__main__":
    main()
