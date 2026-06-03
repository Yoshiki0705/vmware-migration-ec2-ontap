🌐 [日本語](#日本語) | [English](#english)

---

# 日本語

# Shift Toolkit: VMware to EC2 / FSx for ONTAP 検証

> NetApp Shift Toolkit Early Preview — VMware ESXi から Amazon EC2 + FSx for ONTAP への移行検証

## 概要

このリポジトリは、NetApp Shift Toolkit の Early Preview 機能を使用して、VMware ESXi ワークロードを Amazon EC2 + Amazon FSx for NetApp ONTAP に移行する検証プロジェクトです。

### ポジショニング

この検証のポイントは、「VMware から AWS へ移行する」ことだけではありません。既存の VMware / ONTAP 運用で培ったストレージ運用モデルをできるだけ活かしながら、Amazon EC2 と FSx for ONTAP を組み合わせ、クラウドネイティブな運用・拡張性・コスト最適化へつなげられるかを確認することにあります。

### アーキテクチャ

```
[移行元: オンプレミス]              [移行先: AWS]
VMware ESXi                        Amazon EC2
  └── VM (VMDK)                      ├── Boot: EBS (gp3)
       └── on ONTAP NFS/iSCSI       └── Data: FSx for ONTAP (iSCSI)

        ┌─── Shift Toolkit ───┐
        │  FlexClone 変換     │
        │  VMDK → Raw/VHD    │
        │  SnapMirror 転送    │
        └─────────────────────┘
```

### 3者にとっての価値

| 観点 | 価値 |
|------|------|
| **AWS ユーザー** | VMware → EC2 への新しい移行パス + ONTAP データ管理機能 |
| **NetApp ユーザー** | ONTAP 運用モデル（Snapshot, FlexClone, SnapMirror）を AWS でも継続 |
| **VMware ユーザー** | 移行先選択肢の拡大（EC2/FSxN が加わる） |

## ディレクトリ構成

```
docs/           ドキュメント（バイリンガル）
verification/   検証エビデンス
scripts/        自動化スクリプト
templates/      CloudFormation / CDK テンプレート
```

## 注意事項

> **Note**: VMware ESXi → AWS EC2 の Shift Toolkit 対応は Early Preview です。
> 仕様・制約・サポート範囲は変更される可能性があります。利用には NetApp 側での有効化が必要です。

## ライセンス

MIT

---

# English

# Shift Toolkit: VMware to EC2 / FSx for ONTAP Verification

> NetApp Shift Toolkit Early Preview — Migrating VMware ESXi workloads to Amazon EC2 + FSx for ONTAP

## Overview

This repository is a verification project for migrating VMware ESXi workloads to Amazon EC2 + Amazon FSx for NetApp ONTAP using the NetApp Shift Toolkit Early Preview.

### Positioning

The key point of this verification is not just "migrating from VMware to AWS." It's about confirming whether we can leverage the storage operational model built with existing VMware/ONTAP environments and extend it to Amazon EC2 + FSx for ONTAP for cloud-native operations, scalability, and cost optimization.

### Architecture

```
[Source: On-Premises]              [Target: AWS]
VMware ESXi                        Amazon EC2
  └── VM (VMDK)                      ├── Boot: EBS (gp3)
       └── on ONTAP NFS/iSCSI       └── Data: FSx for ONTAP (iSCSI)

        ┌─── Shift Toolkit ───┐
        │  FlexClone convert  │
        │  VMDK → Raw/VHD    │
        │  SnapMirror xfer    │
        └─────────────────────┘
```

### Value for Three Audiences

| Perspective | Value |
|-------------|-------|
| **AWS Users** | New migration path from VMware to EC2 + ONTAP data management |
| **NetApp Users** | Continue ONTAP operational model (Snapshot, FlexClone, SnapMirror) on AWS |
| **VMware Users** | Expanded migration destination options (EC2/FSxN added) |

## Directory Structure

```
docs/           Documentation (bilingual)
verification/   Verification evidence
scripts/        Automation scripts
templates/      CloudFormation / CDK templates
```

## Disclaimer

> **Note**: The VMware ESXi to AWS EC2 migration path in Shift Toolkit is an Early Preview feature.
> Specifications, constraints, and support scope may change. Enablement requires contact with NetApp.

## License

MIT
