# AGENTS.md

> VMware ESXi → Amazon EC2 + FSx for ONTAP migration path verification (NetApp Shift Toolkit / AWS Transform)

## Project Overview

Verification and documentation project evaluating multiple VMware ESXi → AWS EC2 + FSx for ONTAP migration paths (NetApp Shift Toolkit, AWS Transform). Produces blog articles, automation scripts, and architecture guidance.

## Build & Test Commands

```bash
# Python scripts
pip install -r requirements.txt
pytest

# CloudFormation lint
cfn-lint templates/*.yaml
```

## Coding Conventions

- Python 3.12 for automation scripts
- Bash for setup scripts
- CloudFormation YAML for AWS infrastructure
- Structured evidence in YAML format

## Supply-Chain Security

- All third-party Actions pinned to SHA
- gitleaks for secret detection
- zizmor for workflow security
- `.githooks/pre-commit` for local checks
- VMware/ONTAP credentials NEVER in repository

## Common Pitfalls

| Pitfall | Root Cause | Solution |
|---------|-----------|----------|
| AgentCore Gateway assumed us-east-1 only | Workshop examples default to us-east-1 | **ap-northeast-1 で利用可能（検証済み 2026-07）**。Gateway + Lambda を同一リージョンに配置 |
| `create-gateway-target` で Lambda not found | Gateway と Lambda のリージョン不一致 | 同一リージョン配置必須。クロスリージョン Lambda 呼び出しは不可 |

## Agent Output Standards

> User-level Kiro global steering mirror. Ensures compliance even when steering is not loaded.

> CI: `.github/workflows/agent-output-audit.yml` (naming/neutrality/leak/parity) and `gitleaks.yml` (secrets).

### Naming (NetApp / AWS)

- First mention: **Amazon FSx for NetApp ONTAP**; thereafter **FSx for ONTAP**. `FSxN` / bare `FSx` / `FSx ONTAP` are forbidden.
- Access Points: **FSx for ONTAP S3 AP** (not "FSx S3 AP", not bare "S3 AP" when FSx for ONTAP context matters).
- NetApp Workload Factory / NetApp Console / BlueXP — do NOT propose. Reframe to native equivalents (CloudWatch, ONTAP REST API, FabricPool, AWS DataSync, Snapshot/FlexClone/SnapMirror).
- Exception: verbatim external citation titles (annotate with `<!-- allow:naming -->` on the same line).

### Vendor neutrality (right-tool-for-the-job)

- Vendor-versus / superiority expressions are forbidden ("best", "beats X", "X より優れている", "競合ツール", "優位性", "game-changer").
- Present alternatives as options suited to different contexts. Include trade-offs symmetrically (recommended option's constraints included).

### Public-output safety

- NEVER commit: personal names / persona names, emails, AWS account IDs, internal IPs/hostnames, support case numbers, vendor-internal ticket IDs.
- Use role-based references: "Storage Specialist lens", "Partner SA feedback", "an internal product request (tracked)".
- No process-metadata noise in public docs (review rounds, dates, lens counts). Weave findings inline as `> **Topic** (Role lens): ...`; relocate provenance to `.private/` (gitignored).

### Bilingual docs (JA primary + EN)

- Maintain JA/EN parity: matching section structure/count and equivalent inline notes.
- When changing one language version, reflect the same change in the other in the same commit.

### Before committing docs

```bash
gitleaks detect --config .gitleaks.toml --no-git --source .
# CI mirrors agent-output checks: .github/workflows/agent-output-audit.yml
```
