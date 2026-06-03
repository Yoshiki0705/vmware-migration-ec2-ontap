# VMware 移行の選択肢を整理する — なぜ EC2 + FSx for ONTAP なのか

<!-- dev.to front matter
---
title: "VMware 移行の選択肢を整理する — なぜ EC2 + FSx for ONTAP なのか"
published: false
description: "VMware から AWS への移行ツールを比較し、EC2 + FSx for ONTAP の組み合わせを選ぶ理由を整理します"
tags: aws, vmware, netapp, migration
series: "NetApp Shift Toolkit × VMware to EC2 / FSx for ONTAP"
---
-->

## はじめに

VMware ワークロードの「次」を検討する声が、ここ1〜2年で急速に増えています。

Broadcom による VMware 買収後のライセンス変更をきっかけに、多くの組織が仮想化戦略を見直しています。AWS Storage Blog でも、この動きは単なるライセンス回避ではなく、クラウドのコスト効率、柔軟性、信頼性を活用するインフラモダナイゼーションの機会として紹介されています。[（参考）](https://aws.amazon.com/blogs/storage/expedite-vmware-migration-to-amazon-ec2-and-amazon-fsx-for-netapp-ontap-using-bluexp-workload-factory-for-aws-migration-advisor/)

私は Amazon FSx for NetApp ONTAP を担当する立場から、この移行において**ストレージ運用モデルの継続性**が見落とされがちだと感じています。

「VMware を辞める」ことがゴールではなく、VMware / ONTAP 環境で培ったストレージ運用（Snapshot、Clone、Replication、Storage Efficiency）を AWS でも活かしながら、クラウドネイティブな拡張性へつなげることが本質的なゴールだと考えています。

## 移行先の選択肢を整理する

VMware ワークロードの移行先は、大きく3つのカテゴリに分かれます。

### 1. VMware を AWS で継続する（Amazon EVS）

Amazon Elastic VMware Service (EVS) を使えば、VPC 内で VMware Cloud Foundation を直接動かせます。既存の vSphere スキルセットをそのまま活かせる反面、VMware ライセンスは引き続き必要です。

**適するケース:** VMware 依存のアプリケーション資産が大量にあり、短期間での脱 VMware が困難な場合。

### 2. EC2 へリホスト（EBS のみ）

AWS Application Migration Service (MGN) を使って、VM を EC2 インスタンスとして移行するアプローチです。AWS 標準の移行パスで、幅広い OS をサポートします。

**適するケース:** ストレージに特別な要件がなく、EBS (gp3/io2) で十分な場合。ONTAP を使っていない環境。

### 3. EC2 + FSx for ONTAP へリホスト（ハイブリッドストレージ）

OS ディスクは EBS、データディスクは FSx for ONTAP の iSCSI LUN に配置するハイブリッド構成です。

**適するケース:** ONTAP ストレージを使用中で、Snapshot/Clone/SnapMirror/Storage Efficiency を AWS でも継続したい場合。

## なぜ「EC2 + FSx for ONTAP」なのか

3番目の選択肢に注目する理由を整理します。

### ONTAP の価値は「容量」ではなく「機能」

FSx for ONTAP を単なる「大容量ストレージ」として見ると、EBS との比較で割高に見えることがあります。しかし、ONTAP が提供する価値の本質は容量ではありません。

| ONTAP 機能 | AWS での活用 |
|-----------|------------|
| **Snapshot** | 数秒でのポイントインタイムコピー。テスト環境の即時作成 |
| **FlexClone** | データコピーなしのクローン。開発/テストのコスト削減 |
| **SnapMirror** | ブロックレベルレプリケーション。クロスリージョン DR |
| **Compression / Dedup** | 実効容量の削減。特にデータベースやログで効果大 |
| **Thin Provisioning** | 使用分のみ課金。過剰プロビジョニングの回避 |
| **マルチプロトコル** | 同一ボリュームに NFS/SMB/iSCSI でアクセス |

### FSx for ONTAP の EC2 連携パターン

```
┌──────────────────────────────┐
│      Amazon EC2 (Nitro)       │
│  ┌─────────┐  ┌───────────┐  │
│  │ OS: EBS │  │ Data: iSCSI│ │
│  │  (gp3)  │  │  (FSxN)   │  │
│  └─────────┘  └─────┬─────┘  │
└──────────────────────┼────────┘
                       │
           ┌───────────▼──────────┐
           │  FSx for NetApp ONTAP │
           │  • Multi-AZ HA        │
           │  • iSCSI LUN          │
           │  • NVMe Flash Cache   │
           │  • Storage Efficiency  │
           └───────────────────────┘
```

この構成の利点:
- **EC2 の VM レベル I/O 制限を回避**: FSx ONTAP はネットワーク帯域のみが制約。小型インスタンスでも高 IOPS を実現可能
- **ストレージとコンピュートの独立スケーリング**: EC2 を止めずに FSxN の容量/スループットを変更可能
- **ONTAP 運用モデルの継続**: オンプレと同じ CLI/API でスナップショット、クローン、レプリケーションを操作

## 移行ツールの選び方

「EC2 + FSx for ONTAP」に移行する場合でも、使うツールは環境によって異なります。

| 条件 | 推奨ツール | 特徴 |
|------|----------|------|
| ONTAP NFS データストア使用中 + 中小規模 | **NetApp Shift Toolkit** | FlexClone で秒単位のディスク変換。無償 |
| ONTAP 使用中 + 大規模 (100+ VM) | **Cirrus Migrate Cloud** | YAML 自動化、ゼロダウンタイムに近い移行 |
| ONTAP 未使用 or EBS のみ | **AWS MGN** | AWS 標準。幅広い OS 対応。無償 |
| 移行計画・サイジングのみ | **BlueXP Migration Advisor** | RVTools 連携、コスト比較、IaC 出力 |

### NetApp Shift Toolkit の位置づけ

Shift Toolkit は、ONTAP ユーザーが既存の NFS データストア上の VM を移行する際に最も高速なツールです。FlexClone を活用してデータコピーなしでディスク変換を行うため、1TB の VMDK を数秒〜数分で変換できます。

現在は VMware ESXi から Hyper-V、OpenShift Virtualization、Proxmox VE、OLVM への移行が GA しており、**VMware ESXi → Amazon EC2 / FSx for ONTAP への対応は Early Preview** 段階です。

> ⚠️ Early Preview の注意: 現時点ではデータディスクを FSx for ONTAP に配置する構成が対象です。仕様・制約は変更される可能性があります。

## このシリーズで検証すること

本シリーズでは、Shift Toolkit の Early Preview を使って以下を検証します。

1. **環境構築**: VPC + FSx for ONTAP + VPN の設計と構築
2. **移行実行**: Linux / Windows VM の EC2 への移行
3. **パフォーマンス**: FSx ONTAP iSCSI の IOPS / スループット実測
4. **運用継続性**: 移行後の Snapshot / Clone / SnapMirror 動作確認
5. **コスト比較**: EBS のみ構成との TCO 比較

## まとめ

- VMware からの移行は「どこへ行くか」だけでなく「ストレージ運用モデルをどう継続するか」が重要
- ONTAP ユーザーにとって、FSx for ONTAP は AWS 上で ONTAP の価値を継続する選択肢
- ツールは環境と規模で選ぶ。ONTAP + 中小規模なら Shift Toolkit が最速
- Early Preview 段階のため、検証結果は GA で変わる可能性あり

次回は Shift Toolkit そのものの仕組み — FlexClone が VM 移行をどう変えるか — を掘り下げます。

---

## 参考リンク

- [NetApp Shift Toolkit Overview](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/shift-toolkit-overview.html)
- [AWS Storage Blog: Seamless migration from VMware to FSx ONTAP and EC2](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [AWS Storage Blog: BlueXP Migration Advisor](https://aws.amazon.com/blogs/storage/expedite-vmware-migration-to-amazon-ec2-and-amazon-fsx-for-netapp-ontap-using-bluexp-workload-factory-for-aws-migration-advisor/)
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)
- [AWS VMware Migration Accelerator](https://aws.amazon.com/vmware/migrationaccelerator/)
- [NetApp Blog: Simplify VM migration with Shift Toolkit](https://www.netapp.com/blog/simplify-vm-migration-shift-toolkit/)

---

*本記事は NetApp Shift Toolkit Early Preview の検証シリーズ第1回です。Early Preview の仕様は変更される可能性があります。*
