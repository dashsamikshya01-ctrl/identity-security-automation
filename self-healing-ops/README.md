# Self-healing identity operations with agentic AI

> **Result in production:** operations effort on recurring incidents down **67%**, about **60 hours a month**.
> The incident history here is synthetic; replaying it through the same decision logic gives a similar result (about 68%).

## The problem

Most of the identity queue was the same handful of tickets: locked accounts, failed group syncs, licence errors, users who changed phones and lost MFA. Each needed an engineer for 10 to 40 minutes, and none of them needed judgement.

The risk with automating them is obvious: an agent that acts on the wrong account, or on 5,000 accounts at once, is worse than a slow queue. So the design question was not "can an agent fix this?" but **"when is it safe to let it?"**

## How it works

The workflow runs in **n8n**. An LLM classifies each ticket, but it **never chooses the fix**. It can only pick from a catalogue of approved runbooks, and code checks the guardrails before anything runs.

```mermaid
flowchart TD
    T([New ServiceNow ticket]) --> C[LLM classifies the ticket<br/>and extracts the user or object]
    C --> K{Matches an approved<br/>runbook?}
    K -- no --> H1[Engineer<br/>with the agent's notes attached]
    K -- yes --> Q{Confidence ≥ 0.85?}
    Q -- no --> H1
    Q -- yes --> G{Guardrails pass?<br/>object count · privileged account · recent risk}
    G -- no --> H1
    G -- yes --> AP{Runbook needs<br/>approval?}
    AP -- yes --> OK[One-click approval<br/>in Teams]
    AP -- no --> F
    OK --> F[Run the fix<br/>Graph API or PowerShell]
    F --> V{Verified?}
    V -- yes --> Z([Resolve ticket with evidence])
    V -- no --> RB[Roll back] --> H1

    classDef ai fill:#3b2a6b,stroke:#9085e9,color:#fff;
    classDef act fill:#14325c,stroke:#63b3ed,color:#fff;
    classDef human fill:#5c2e14,stroke:#d95926,color:#fff;
    classDef ok fill:#0f4032,stroke:#199e70,color:#fff;
    class C ai; class F,OK,V act; class H1,RB human; class Z ok;
```

### The guardrails

Each runbook in [`runbooks.yaml`](runbooks.yaml) carries its own limits:

| Runbook | Max objects | Skip privileged accounts | Needs approval |
|---|---|---|---|
| Account lockout | 1 | ✅ | — |
| Group sync failure | 500 | ✅ | — |
| Licence assignment error | 50 | — | — |
| MFA re-registration | 1 | ✅ | ✅ manager |
| Stale device object | 200 | — | — |
| Service account password expiry | 1 | — | ✅ |

MFA resets and service-account rotations always need a human click. They're exactly what an attacker would try to trigger through a fake ticket.

## Try it

```bash
python self-healing-ops/triage.py
```

It replays six months of synthetic tickets from [`data/incidents.csv`](data/incidents.csv): two months of manual baseline, then four with the agent live.

![Engineer hours per month](docs/engineer_hours.svg)

![Who closed each incident](docs/who_handled.svg)

Novel issues and unexplained Conditional Access blocks still go to engineers, by design. The agent's job is the repetitive tickets, so engineers have time for those.

**Built with:** n8n · LLM classification · Microsoft Graph API · PowerShell · ServiceNow · Microsoft Teams approvals
