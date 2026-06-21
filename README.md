🌐 [日本語](#日本語) | [English](#english)

---

# 日本語

# VMware to EC2 + FSx for ONTAP 移行パス検証

> NetApp Shift Toolkit (Early Preview) と AWS Transform (Public Preview) による VMware ESXi → Amazon EC2 + Amazon FSx for NetApp ONTAP 移行の実機検証

## 概要

このリポジトリは、VMware ESXi ワークロードを Amazon EC2 + Amazon FSx for NetApp ONTAP に移行する複数パス（NetApp Shift Toolkit / AWS Transform）の検証プロジェクトです。

### ポジショニング

この検証のポイントは、「VMware から AWS へ移行する」ことだけではありません。既存の VMware / ONTAP 運用で培ったストレージ運用モデルをできるだけ活かしながら、Amazon EC2 と FSx for ONTAP を組み合わせ、クラウドネイティブな運用・拡張性・コスト最適化へつなげられるかを確認することにあります。

### アーキテクチャ

```text
[移行元: オンプレミス]              [移行先: AWS]
VMware ESXi                        Amazon EC2 (Nitro)
  └── VM (VMDK)                      ├── Boot: EBS gp3
       └── on ONTAP NFS              └── Data: FSx for ONTAP (iSCSI LUN)

移行パス A: NetApp Shift Toolkit (Early Preview)
┌──────────────────────────────────────────────────┐
│ 1. FlexClone で VMDK → iSCSI LUN 変換（秒〜分）   │
│ 2. SnapMirror でオンプレ ONTAP → FSx for ONTAP    │
│ 3. OS ディスク → EBS snapshot → AMI               │
│ 4. EC2 起動 + FSx for ONTAP iSCSI アタッチ        │
└──────────────────────────────────────────────────┘

移行パス B: AWS Transform (Public Preview)
┌──────────────────────────────────────────────────┐
│ 1. Discovery (RVTools / OVA / NetApp DII)         │
│ 2. AI ベースのウェーブ計画                         │
│ 3. MGN レプリケーション（継続同期）                │
│ 4. カットオーバー: OS → EBS / Data → FSx for ONTAP│
└──────────────────────────────────────────────────┘
```

### 3者にとっての価値

| 観点 | 価値 |
|------|------|
| **AWS ユーザー** | VMware → EC2 への新しい移行パス。FSx for ONTAP の thin provisioning / dedup / compression でコスト最適化 |
| **NetApp ユーザー** | ONTAP 運用モデル（Snapshot, FlexClone, SnapMirror, Storage Efficiency）を AWS でも継続 |
| **VMware ユーザー** | 移行先選択肢の拡大。段階的移行が可能でソース VM は非破壊 |

### ツール選択ガイド

| 条件 | 推奨ツール |
|------|----------|
| ONTAP 未使用 or EBS のみで十分 | AWS MGN |
| ONTAP 使用中 + FSx for ONTAP にデータ配置 + 中小規模 | **Shift Toolkit** (Early Preview) |
| ONTAP 使用中 + 大規模 (100+ VM) + ゼロダウンタイム | Cirrus Migrate Cloud (CMC) |
| AWS ネイティブで一気通貫（計画〜コンピュート〜ストレージ）/ ソース混在 | AWS Transform（VMware 移行は無料・FSx for ONTAP 宛先は Public Preview） |
| 移行計画・サイジングのみ | BlueXP Migration Advisor | <!-- allow:naming -->

## 検証フェーズ

| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 0 | 調査・計画策定 | ✅ 完了 |
| Phase 1 | AWS 環境準備（VPC, FSx for ONTAP, EC2） | 📋 計画済 |
| Phase 2a | AWS Transform 検証（Discovery → 計画 → 移行） | 📋 Spec 作成済 |
| Phase 2b | Shift Toolkit 検証（FlexClone 変換 → EC2 起動） | ⏳ NetApp Q&A 待ち |
| Phase 3 | 検証・ベンチマーク（パフォーマンス / コスト / ONTAP 機能） | ⏳ 未着手 |
| Phase 4 | ドキュメント・ブログ記事化 | ⏳ 未着手 |

## 検証の成功指標

| 指標 | 目標 |
|------|------|
| データディスク変換時間 | 100GB あたり 5分以内（FlexClone） |
| カットオーバー停止 | 30分以内（小規模 VM） |
| データ整合性 | 100%（sha256sum 一致） |
| FSx for ONTAP iSCSI パフォーマンス | ベースライン比較レポート作成 |
| コスト比較 | EBS のみ vs EBS + FSx for ONTAP のハイブリッド構成 |

## ディレクトリ構成

```text
docs/
  ├── ja/              日本語ドキュメント
  │   └── research.md  調査レポート（完了）
  ├── en/              英語ドキュメント
  └── images/          アーキテクチャ図
scripts/               自動化スクリプト（Python 3.12 / Bash）
templates/             CloudFormation テンプレート
  └── poc-environment.yaml  PoC 環境構築テンプレート
verification/
  ├── evidence/        検証エビデンス（YAML 形式）
  └── screenshots/     スクリーンショット（マスキング済み）
```

## クイックスタート

```bash
# リポジトリクローン
git clone https://github.com/Yoshiki0705/vmware-migration-ec2-ontap.git
cd vmware-migration-ec2-ontap

# Git hooks 設定
git config core.hooksPath .githooks

# Python 依存関係
pip install -r requirements.txt

# PoC 環境デプロイ（Phase 1 — VPC + FSx for ONTAP）
aws cloudformation deploy \
  --template-file templates/poc-environment.yaml \
  --stack-name vmware-migration-poc \
  --parameter-overrides \
    VpcCidr=10.0.0.0/16 \
    FsxnThroughput=512 \
    FsxnStorageCapacity=1024 \
  --capabilities CAPABILITY_IAM
```

## 前提条件

### オンプレミス側

- VMware vCenter 7.0.3 以降（ESXi ホスト + NFS データストア）
- ONTAP 9.14.1 以降
- NetApp Shift Toolkit（Windows Server 上にインストール — Shift Toolkit 検証の場合）
- NetApp Support アカウント（Early Preview 有効化用）

### AWS 側

- AWS アカウント + 適切な IAM 権限
- AWS Organizations + IAM Identity Center（AWS Transform の前提）
- VPN or Direct Connect（オンプレ ↔ AWS 間接続）
- 東京リージョン (ap-northeast-1) 推奨

## 注意事項

> ⚠️ **Preview ステータス（2026-06 時点）**:
>
> - **Shift Toolkit**: VMware ESXi → AWS EC2 の対応は **Early Preview**。
>   OS ディスク → EBS + データディスク → FSx for ONTAP の構成。利用には NetApp 側での有効化が必要。
> - **AWS Transform**: FSx for ONTAP を移行先ストレージとする機能は **Public Preview**。
>   VMware 移行エージェントは無料。対応リージョン・UI・制約は変更されうる。
>
> いずれも仕様・制約・サポート範囲は変更される可能性があります。GA 仕様としては扱わないでください。

## 参考リンク

### NetApp

- [NetApp Shift Toolkit Overview](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/shift-toolkit-overview.html)
- [Migrate VMs to Amazon EC2 (NetApp)](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/migrate-vms-to-ec2-fsxn-overview.html)
- [What's New in Shift v8.0](https://community.netapp.com/t5/Tech-ONTAP-Blogs/What-s-New-in-Shift-v8-0-File-to-LUN-EC2-FSx-for-ONTAP-Trident-Integration-amp/ba-p/467669)

### AWS

- [AWS Transform: VMware to FSx for ONTAP (What's New)](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/)
- [Accelerating VMware migration: AWS Transform](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migration-aws-transforms-new-experience/)
- [AWS Storage Blog: Seamless VMware Migration](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)
- [AWS Transform Pricing](https://aws.amazon.com/transform/pricing/)

## ライセンス

MIT

---

# English

# VMware to EC2 + FSx for ONTAP Migration Path Verification

> Hands-on verification of VMware ESXi → Amazon EC2 + Amazon FSx for NetApp ONTAP migration using NetApp Shift Toolkit (Early Preview) and AWS Transform (Public Preview)

## Overview

This repository is a verification project for migrating VMware ESXi workloads to Amazon EC2 + Amazon FSx for NetApp ONTAP, evaluating multiple migration paths (NetApp Shift Toolkit / AWS Transform).

### Positioning

The key point of this verification is not just "migrating from VMware to AWS." It's about confirming whether we can leverage the storage operational model built with existing VMware/ONTAP environments and extend it to Amazon EC2 + FSx for ONTAP for cloud-native operations, scalability, and cost optimization.

### Architecture

```text
[Source: On-Premises]              [Target: AWS]
VMware ESXi                        Amazon EC2 (Nitro)
  └── VM (VMDK)                      ├── Boot: EBS gp3
       └── on ONTAP NFS              └── Data: FSx for ONTAP (iSCSI LUN)

Path A: NetApp Shift Toolkit (Early Preview)
┌──────────────────────────────────────────────────┐
│ 1. FlexClone VMDK → iSCSI LUN conversion (secs)  │
│ 2. SnapMirror: on-prem ONTAP → FSx for ONTAP     │
│ 3. OS disk → EBS snapshot → AMI                   │
│ 4. EC2 launch + FSx for ONTAP iSCSI attach        │
└──────────────────────────────────────────────────┘

Path B: AWS Transform (Public Preview)
┌──────────────────────────────────────────────────┐
│ 1. Discovery (RVTools / OVA / NetApp DII)         │
│ 2. AI-based wave planning                         │
│ 3. MGN replication (continuous sync)              │
│ 4. Cutover: OS → EBS / Data → FSx for ONTAP      │
└──────────────────────────────────────────────────┘
```

### Value for Three Audiences

| Perspective | Value |
|-------------|-------|
| **AWS Users** | New VMware → EC2 migration path. FSx for ONTAP thin provisioning / dedup / compression for cost optimization |
| **NetApp Users** | Continue ONTAP operational model (Snapshot, FlexClone, SnapMirror, Storage Efficiency) on AWS |
| **VMware Users** | Expanded migration destinations. Phased migration possible with non-destructive source VMs |

### Tool Selection Guide

| Condition | Recommended Tool |
|-----------|-----------------|
| No ONTAP or EBS-only sufficient | AWS MGN |
| ONTAP in use + FSx for ONTAP data placement + small/mid-scale | **Shift Toolkit** (Early Preview) |
| ONTAP in use + large scale (100+ VMs) + near-zero downtime | Cirrus Migrate Cloud (CMC) |
| AWS-native end-to-end (plan → compute → storage) / mixed sources | AWS Transform (VMware migration free; FSx for ONTAP destination Public Preview) |
| Migration planning & sizing only | BlueXP Migration Advisor | <!-- allow:naming -->

## Verification Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Research & planning | ✅ Complete |
| Phase 1 | AWS environment setup (VPC, FSx for ONTAP, EC2) | 📋 Planned |
| Phase 2a | AWS Transform verification (Discovery → Plan → Migrate) | 📋 Spec ready |
| Phase 2b | Shift Toolkit verification (FlexClone conversion → EC2 launch) | ⏳ Awaiting NetApp Q&A |
| Phase 3 | Validation & benchmarking (performance / cost / ONTAP features) | ⏳ Not started |
| Phase 4 | Documentation & blog articles | ⏳ Not started |

## Success Criteria

| Metric | Target |
|--------|--------|
| Data disk conversion time | Under 5 min per 100GB (FlexClone) |
| Cutover downtime | Under 30 min (small VMs) |
| Data integrity | 100% (sha256sum match) |
| FSx for ONTAP iSCSI performance | Baseline comparison report |
| Cost comparison | EBS-only vs EBS + FSx for ONTAP hybrid |

## Directory Structure

```text
docs/
  ├── ja/              Japanese documentation
  │   └── research.md  Research report (complete)
  ├── en/              English documentation
  └── images/          Architecture diagrams
scripts/               Automation scripts (Python 3.12 / Bash)
templates/             CloudFormation templates
  └── poc-environment.yaml  PoC environment template
verification/
  ├── evidence/        Verification evidence (YAML)
  └── screenshots/     Screenshots (masked)
```

## Quick Start

```bash
# Clone repository
git clone https://github.com/Yoshiki0705/vmware-migration-ec2-ontap.git
cd vmware-migration-ec2-ontap

# Set up git hooks
git config core.hooksPath .githooks

# Install Python dependencies
pip install -r requirements.txt

# Deploy PoC environment (Phase 1 — VPC + FSx for ONTAP)
aws cloudformation deploy \
  --template-file templates/poc-environment.yaml \
  --stack-name vmware-migration-poc \
  --parameter-overrides \
    VpcCidr=10.0.0.0/16 \
    FsxnThroughput=512 \
    FsxnStorageCapacity=1024 \
  --capabilities CAPABILITY_IAM
```

## Prerequisites

### On-Premises

- VMware vCenter 7.0.3+ (ESXi hosts + NFS datastore)
- ONTAP 9.14.1+
- NetApp Shift Toolkit (installed on Windows Server — for Shift Toolkit verification)
- NetApp Support account (for Early Preview enablement)

### AWS

- AWS account with appropriate IAM permissions
- AWS Organizations + IAM Identity Center (required for AWS Transform)
- VPN or Direct Connect (on-prem ↔ AWS connectivity)
- Tokyo Region (ap-northeast-1) recommended

## Disclaimer

> ⚠️ **Preview Status (as of 2026-06)**:
>
> - **Shift Toolkit**: VMware ESXi → AWS EC2 support is **Early Preview**.
>   OS disk → EBS + Data disk → FSx for ONTAP configuration. Requires enablement by NetApp.
> - **AWS Transform**: FSx for ONTAP as migration destination is **Public Preview**.
>   VMware migration agent is free. Supported regions, UI, and constraints may change.
>
> Specifications, constraints, and support scope may change for both tools. Do not treat as GA.

## References

### NetApp

- [NetApp Shift Toolkit Overview](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/shift-toolkit-overview.html)
- [Migrate VMs to Amazon EC2 (NetApp)](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/migrate-vms-to-ec2-fsxn-overview.html)
- [What's New in Shift v8.0](https://community.netapp.com/t5/Tech-ONTAP-Blogs/What-s-New-in-Shift-v8-0-File-to-LUN-EC2-FSx-for-ONTAP-Trident-Integration-amp/ba-p/467669)

### AWS

- [AWS Transform: VMware to FSx for ONTAP (What's New)](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/)
- [Accelerating VMware migration: AWS Transform](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migration-aws-transforms-new-experience/)
- [AWS Storage Blog: Seamless VMware Migration](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)
- [AWS Transform Pricing](https://aws.amazon.com/transform/pricing/)

## License

MIT
