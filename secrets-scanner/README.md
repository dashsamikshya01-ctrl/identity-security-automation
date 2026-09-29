# Secrets scanner

> **Result in production:** **77 leaked secrets** caught across **37 repositories** before they reached production.
> The findings dataset here is synthetic, shaped to that same scale.

## The problem

Developers under deadline paste a connection string into `appsettings.json` or leave a client secret in a notebook "just for testing". Once that's pushed, the secret is in Git history for good, and rotating it becomes an incident.

The goal was to catch secrets **as early as possible**, while keeping false positives low enough that developers don't start ignoring the tool.

## Three layers, one rule set

```mermaid
flowchart LR
    Dev([Developer]) --> PC{Pre-commit hook}
    PC -- secret found --> X1[Commit blocked<br/>fix locally, nothing pushed]
    PC -- clean --> PR{Pull request gate<br/>CI pipeline}
    PR -- secret found --> X2[PR fails<br/>rotate before merge]
    PR -- clean --> M([Merged])
    M --> N{Nightly full scan<br/>all repos + history}
    N -- secret found --> X3[Ticket to repo owner<br/>rotate and purge]

    classDef stop fill:#5c2e14,stroke:#d95926,color:#fff;
    classDef ok fill:#0f4032,stroke:#199e70,color:#fff;
    class X1,X2,X3 stop; class M ok;
```

The pre-commit hook is the cheapest place to stop a secret because nothing has left the laptop. The PR gate catches anyone who skipped the hook. The nightly scan catches old secrets already sitting in history.

## How detection works

[`scanner.py`](scanner.py) combines two methods:

1. **Known patterns.** Regular expressions for secret formats that are easy to recognise: AWS keys, Azure storage keys, PEM private keys, GitHub and GitLab tokens, connection strings, webhook URLs.
2. **Entropy.** Any token of 32+ characters with Shannon entropy ≥ 4.3 bits per character looks random, and random-looking strings in code are usually keys. This catches secrets with no known format.

Documented test values can be allow-listed inline with `# secrets-scanner:allow`, so the tool never becomes an obstacle for legitimate fixtures.

**Severity decides what blocks.** Critical and serious findings fail the commit or build; warnings are reported but don't block.

## What happens after a finding

```mermaid
flowchart LR
    F([Finding]) --> T{Real secret?}
    T -- no --> A[Allow-list with reason]
    T -- yes --> R[Rotate in Key Vault<br/>or the issuing service]
    R --> P[Remove from code<br/>reference Key Vault instead]
    P --> H[Purge from Git history]
    H --> C([Closed with evidence])
```

**Rotate first, then remove.** Deleting a leaked secret from the code doesn't make it safe; anyone who cloned the repo still has it.

## Try it

```bash
python secrets-scanner/scanner.py --report      # charts from the synthetic findings
python secrets-scanner/scanner.py path/to/code  # scan a folder; exit code 1 blocks CI
python -m pytest secrets-scanner/tests          # unit tests
```

![Findings by type](docs/findings_by_type.svg)

![Findings by stage](docs/caught_by_stage.svg)

The test fixtures build their fake secrets at runtime, so this repository never contains anything that looks like a live credential.

**Built with:** Python · regex and Shannon entropy · pre-commit · Azure DevOps and GitHub Actions
