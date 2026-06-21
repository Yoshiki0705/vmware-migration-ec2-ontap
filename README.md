# VMware to EC2 + FSx for ONTAP 移行パス検証

🌐 **Language / 言語**: 日本語 (このページ) | [English](README.en.md)

> NetApp Shift Toolkit (Early Preview) と AWS Transform (Public Preview) による VMware ESXi → Amazon EC2 + Amazon FSx for NetApp ONTAP 移行の実機検証

## 概要

このリポジトリは、VMware ESXi ワークロードを Amazon EC2 + Amazon FSx for NetApp ONTAP に移行する複数パス（NetApp Shift Toolkit / AWS Transform）の検証プロジェクトです。

### ポジショニング

この検証のポイントは、「VMware から AWS へ移行する」ことだけではありません。既存の VMware / ONTAP 運用で培ったストレージ運用モデルをできるだけ活かしながら、Amazon EC2 と FSx for ONTAP を組み合わせ、クラウドネイティブな運用・拡張性・コスト最適化へつなげられるかを確認することにあります。

### アーキテクチャ

```text
[移行元: オンプレミス]                [移行先: AWS]
VMware ESXi                          Amazon EC2 (Nitro)
  └── VM (VMDK)                        ├── Boot: EBS gp3
       └── on ONTAP NFS                └── Data: FSx for ONTAP (iSCSI LUN)

移行パス A: NetApp Shift Toolkit (Early Preview)
┌────────────────────────────────────────────────────────┐
│ 1. FlexClone で VMDK → iSCSI LUN 変換（数秒〜1分）        │
│ 2. SnapMirror 同期: オンプレ ONTAP → FSx for ONTAP       │
│ 3. OS ディスク → EBS スナップショット → AMI                │
│ 4. EC2 起動 + FSx for ONTAP iSCSI アタッチ               │
└────────────────────────────────────────────────────────┘

移行パス B: AWS Transform (Public Preview)
┌────────────────────────────────────────────────────────┐
│ 1. Discovery (RVTools / OVA / NetApp DII)              │
│ 2. AI ベースのウェーブプランニング              　          │
│ 3. MGN レプリケーション（継続同期）             　          │
│ 4. カットオーバー:　OS → EBS / Data → FSx for ONTAP  　   │
└────────────────────────────────────────────────────────┘
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
| AWS ネイティブで一気通貫（計画〜コンピュート〜ストレージ）/ ソース混在 | **AWS Transform**（VMware 移行は無料・FSx for ONTAP 宛先は Public Preview） |
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
  ├── ja/                日本語ドキュメント
  │   ├── research.md    調査レポート
  │   └── aws-transform-migration-procedure.md
  ├── en/                英語ドキュメント
  │   └── research-summary.md
  └── images/            アーキテクチャ図
scripts/                 自動化スクリプト（Python 3.12 / Bash）
templates/               CloudFormation テンプレート
  └── poc-environment.yaml
verification/
  ├── evidence/          検証エビデンス（YAML 形式）
  └── screenshots/       スクリーンショット（マスキング済み）
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

- [NetApp Shift Toolkit Overview](https://docs.netapp.com/us-en/netapp-solutions/vm-migrate/migrate-overview.html)
- [Migrate VMs to Amazon EC2 using FSx for ONTAP](https://docs.netapp.com/us-en/netapp-solutions/vmware/migrate-vms-to-ec2-fsxn-deploy.html)
- [Shift Toolkit Supported Versions](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/shift-toolkit-supported-versions.html)

### AWS

- [AWS Transform: VMware to FSx for ONTAP (What's New)](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/)
- [Accelerating VMware migration: AWS Transform](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migration-aws-transforms-new-experience/)
- [AWS Storage Blog: Seamless VMware Migration](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)
- [AWS Transform Pricing](https://aws.amazon.com/transform/pricing/)

## ライセンス

MIT
