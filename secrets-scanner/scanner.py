"""Secrets scanner: regex rules + Shannon entropy, built to run as a pre-commit hook and a CI gate.

    python scanner.py <path>              # scan a folder, print findings, exit 1 if any critical/serious
    python scanner.py --report            # build charts from data/findings_sample.csv (synthetic)
"""
import argparse, csv, json, math, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import svgchart as sc  # noqa: E402

RULES = [  # (name, severity, regex)
    ("AWS access key", "critical", r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    ("Azure storage account key", "critical", r"AccountKey=[A-Za-z0-9+/]{86}=="),
    ("Private key (PEM)", "critical", r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ("Client secret in config", "critical", r"(?i)(client_?secret|app_?secret)\s*[:=]\s*[\"']?[A-Za-z0-9~._\-]{30,}"),
    ("Personal access token", "serious", r"\b(ghp_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9\-_]{20})\b"),
    ("Connection string with password", "serious", r"(?i)(password|pwd)=[^;\s\"']{6,}"),
    ("Slack/Teams webhook URL", "warning", r"https://(hooks\.slack\.com/services|[a-z0-9-]+\.webhook\.office\.com)/\S+"),
]
ENTROPY_MIN, TOKEN_MIN_LEN = 4.3, 32
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__"}
ALLOW_MARK = "secrets-scanner:allow"  # inline allow-list for documented test values


def entropy(s):
    c = Counter(s)
    return -sum(n / len(s) * math.log2(n / len(s)) for n in c.values())


def scan_text(text, path):
    out = []
    for no, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARK in line:
            continue
        hit = False
        for name, sev, rx in RULES:
            if re.search(rx, line):
                out.append({"file": str(path), "line": no, "rule": name, "severity": sev}); hit = True
        if not hit:
            for tok in re.findall(r"[A-Za-z0-9+/=_\-]{%d,}" % TOKEN_MIN_LEN, line):
                if entropy(tok) >= ENTROPY_MIN:
                    out.append({"file": str(path), "line": no, "rule": "Generic high-entropy token", "severity": "warning"}); break
    return out


def scan_path(root):
    findings = []
    for p in Path(root).rglob("*"):
        if p.is_file() and not SKIP_DIRS.intersection(p.parts) and p.stat().st_size < 2_000_000:
            try:
                findings += scan_text(p.read_text(errors="ignore"), p)
            except OSError:
                pass
    return findings


def report():
    rows = list(csv.DictReader((HERE / "data/findings_sample.csv").open()))
    by_rule = Counter(r["rule"] for r in rows).most_common()
    sc.hbars(str(HERE / "docs/findings_by_type.svg"), "What the scanner catches",
             f"{len(rows)} findings across {len({r['repo'] for r in rows})} repositories (synthetic dataset at real-world scale)",
             [k for k, _ in by_rule], [v for _, v in by_rule])
    stage = Counter(r["stage_caught"] for r in rows)
    order = ["pre-commit", "pull request", "nightly full scan"]
    sc.bars(str(HERE / "docs/caught_by_stage.svg"), "Caught before production, at every stage",
            "Where each finding was stopped (synthetic)", ["Pre-commit hook", "Pull request gate", "Nightly full scan"],
            [stage[s] for s in order], [sc.AQUA, sc.BLUE, sc.STATUS["neutral"]], h=320)
    status = Counter(r["status"] for r in rows)
    print(json.dumps({"findings": len(rows), "by_rule": dict(by_rule), "by_stage": dict(stage), "outcome": dict(status)}, indent=2))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("path", nargs="?"); ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report or not a.path:
        return report()
    f = scan_path(a.path)
    for x in f:
        print(f"[{x['severity'].upper():8}] {x['file']}:{x['line']}  {x['rule']}")
    blocking = [x for x in f if x["severity"] in ("critical", "serious")]
    print(f"\n{len(f)} finding(s), {len(blocking)} blocking")
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
