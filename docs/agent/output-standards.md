# Output standards

Mirror of the user-level Kiro global steering, kept here so the rules hold even
when steering is not loaded. Enforced by
`.github/workflows/agent-output-audit.yml` (naming, neutrality, leak, parity) and
`.github/workflows/gitleaks.yml` (secrets).

## Naming (NetApp / AWS)

- First mention: **Amazon FSx for NetApp ONTAP**; thereafter **FSx for ONTAP**.
  `FSxN`, bare `FSx`, and `FSx ONTAP` are forbidden.
- Access Points: **FSx for ONTAP S3 AP** — not "FSx S3 AP", and not a bare
  "S3 AP" where the FSx for ONTAP context matters.
- Do not propose NetApp Workload Factory, NetApp Console, or BlueXP. Reframe to
  the native equivalent: Amazon CloudWatch, ONTAP REST API, FabricPool,
  AWS DataSync, Snapshot / FlexClone / SnapMirror.
- Exception: a verbatim external citation title. Annotate the line with
  `<!-- allow:naming -->`.

## Vendor neutrality

Present alternatives as options suited to different contexts. Superiority
claims ("best", "beats X", "より優れている", "競合ツール", "優位性",
"game-changer") are forbidden. State trade-offs symmetrically, including the
constraints of the option being recommended.

## Public-output safety

Never commit personal or persona names, email addresses, AWS account IDs,
internal IP addresses or hostnames, support case numbers, or vendor-internal
ticket IDs. Use role-based references instead: "Storage Specialist lens",
"Partner SA feedback", "an internal product request (tracked)".

Inline review notes use a neutral topic label (`> **Security note**:`,
`> **コストに関する補足**:`), never a job-title label, which would imply a real
person in that role reviewed the document.

No process metadata in published docs: review rounds, dates, or lens counts
belong in `.private/` (gitignored).

> **Leak-check degradation note**: the leak step builds its pattern from the
> `PROJECT_CONTEXT_NAMES` repository secret. If that secret is unset the pattern
> falls back to internal ticket IDs only, and name detection silently stops
> without failing the job. Confirm the secret is present when relying on this
> check.

## Bilingual docs

JA is primary, EN must match section structure and count with equivalent inline
notes. Change both in the same commit.

## Before committing docs

```bash
make drift            # 設定の到達性 + 常時ロード予算
gitleaks detect --config .gitleaks.toml --no-git --source .
```
