# Project conventions

VMware ESXi workloads migrated to Amazon EC2 with Amazon FSx for NetApp ONTAP.
The repository verifies and documents several migration paths (NetApp Shift
Toolkit, AWS Transform, VM Import/Export, Veeam Restore to EC2) and publishes the
results as articles, automation scripts, and architecture guidance.

## Directory layout

```
docs/ja/     日本語ドキュメント（主）
docs/en/     英語ドキュメント
docs/agent/  エージェント向け（この階層）
scripts/     Python / Bash 自動化
scripts/tests/ pytest（Makefile の TEST_DIRS が指す唯一の場所）
templates/   CloudFormation
params/       テンプレートのパラメータ例
```

## Language and style

- Python 3.12+ for automation scripts, Bash for setup and benchmark scripts,
  CloudFormation YAML for infrastructure, YAML for structured evidence.
- Lint configuration is `ruff.toml`; line length 100.
- Documentation is bilingual: JA is primary, EN must match section structure and
  count. Change both in the same commit.

> **JA/EN parity note**: the CI parity check derives the EN path by replacing
> `docs/ja/` with `docs/en/`. `docs/ja/research.md` has no `docs/en/research.md`
> (the English file is named `research-summary.md`), so that pair reports a
> warning that cannot be cleared without renaming one side. Unresolved.

## Verification phases

| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 0 | 調査・計画策定 | 完了 |
| Phase 1 | AWS 環境準備（VPC, FSx for ONTAP, EC2） | 完了。Shift Toolkit / Transform 双方で利用中 |
| Phase 2a | AWS Transform 検証 | 進行中。Workspace 作成済、VMware Migration ジョブ開始待ち |
| Phase 2b | Shift Toolkit 検証 | 進行中。boot disk / 複数ディスク構成とも成功、実測データ取得済 |
| Phase 2c | VM Import/Export 検証 | 手順書作成済、実機検証予定 |
| Phase 2d | Veeam Restore to EC2 検証 | 計画中 |
| Phase 3 | 移行方式比較・ベンチマーク | 比較表作成中 |
| Phase 4 | ドキュメント・記事化 | 一部ドラフト |

## Phase 1 entry gate

Do not deploy Phase 1 until all of these hold:

- `aws sts get-caller-identity` succeeds
- FSx for ONTAP is available in the target region
- AWS Organizations and IAM Identity Center are set up (required for AWS Transform)
- Shift Toolkit Early Preview enablement status confirmed
- VPN or AWS Direct Connect design complete, if on-premises connectivity is needed
- `scripts/verify-setup.sh` passes

## Credentials

VMware and ONTAP credentials never enter the repository. `params/*.example.json`
carries the shape; real values stay outside version control.
