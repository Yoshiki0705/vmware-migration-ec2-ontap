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

VMware ワークロードの移行先について、AWS は公式に5つのパスウェイを提示しています。[（参考: AWS for VMware — Comprehensive Pathways）](https://aws.amazon.com/vmware/explore/)

### AWS 公式 VMware パスウェイ全体像

```
┌─────────────────────────────────────────────────────────────────────┐
│              VMware ワークロードの AWS パスウェイ                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Migrate to Amazon EC2（リホスト）                                │
│     └─ VMware VM → EC2 インスタンス化                               │
│        ツール: AWS Transform, MGN, CMC, Shift Toolkit              │
│                                                                     │
│  2. Modernize on AWS（モダナイゼーション）                            │
│     └─ コンテナ化 / サーバーレス化                                   │
│        → Amazon ECS / EKS (EC2 mode / Fargate)                     │
│        → AWS Lambda / AWS Batch                                     │
│        → Amazon WorkSpaces (VDI)                                    │
│                                                                     │
│  3. Run VMware on AWS（VMware 継続）                                 │
│     └─ Amazon Elastic VMware Service (EVS)                          │
│        既存 vSphere スキル・ツールをそのまま活用                      │
│                                                                     │
│  4. Run AWS on-premises（オンプレ AWS）                              │
│     └─ AWS Outposts                                                 │
│                                                                     │
│  5. Run third-party hypervisors on AWS（パートナーソリューション）    │
│     └─ Red Hat OpenShift Service on AWS (ROSA)                      │
│     └─ Nutanix Cloud Clusters on AWS (NC2)                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

> 出典: [AWS for VMware Partner Offerings](https://aws.amazon.com/vmware/partner-offerings/) — "AWS offers the most comprehensive set of migration and modernization options for VMware-based workloads - from relocating to Amazon EVS, to rehosting on Amazon EC2, containerizing with Amazon EKS, or transitioning to running third-party hypervisors in the cloud like ROSA and NC2 on AWS."（内容を要約して記載。ライセンス制約に基づき表現を言い換え。）

### 各パスウェイの詳細

#### 1. Amazon EC2 へリホスト

VMware VM を EC2 インスタンスとして移行する最もストレートなパス。AWS Transform for VMware（Agentic AI ベースの自動移行サービス）が 2025年に GA し、大規模移行の自動化が進んでいます。

**ストレージ構成の選択肢:**
- **EBS のみ**: シンプル。MGN / AWS Transform で自動化
- **EBS (OS) + FSx for ONTAP (Data)**: ONTAP 機能の継続。Shift Toolkit / CMC で対応 ← **本検証のスコープ**

#### 2. モダナイゼーション（コンテナ / サーバーレス）

EC2 にリホストした後の次のステップとして、ワークロードの特性に応じたモダナイゼーションが可能です。

| ターゲット | 適するワークロード | FSxN 連携 |
|-----------|------------------|-----------|
| **ECS / EKS (EC2 mode)** | ステートフル・コンテナ（DB、ミドルウェア） | ✅ iSCSI / NFS マウント可能 |
| **ECS / EKS (Fargate)** | ステートレス・マイクロサービス | △ EFS 経由のみ（iSCSI 不可） |
| **AWS Lambda** | イベント駆動・短時間処理 | △ EFS マウント可能、iSCSI 不可 |
| **AWS Batch** | バッチ処理・HPC | ✅ EC2 mode なら iSCSI 可能 |
| **Amazon WorkSpaces** | VDI（仮想デスクトップ） | ✅ FSxN ファイル共有 |

**重要**: VM をそのままコンテナ化するわけではありません。EC2 リホスト → アプリケーションのコンテナ化 → Fargate/Lambda への段階的移行というジャーニーになります。

#### 3. Amazon EVS（VMware を AWS で継続）

Amazon Elastic VMware Service を使えば、VPC 内で VMware Cloud Foundation (VCF) を EC2 ベアメタル上に直接デプロイできます。既存の vSphere スキルセットをそのまま活かし、FSx for ONTAP を外部データストアとして接続可能です。

**適するケース:** VMware 依存のアプリケーション資産が大量にあり、短期間での脱 VMware が困難な場合。

#### 4. AWS Outposts（オンプレ AWS + NetApp 外部ストレージ）

AWS Outposts は、AWS インフラをオンプレミスに配置するフルマネージドサービスです。2024年12月に AWS は Outposts でのサードパーティブロックストレージ統合を発表し、**NetApp ONTAP と StorageGRID が AWS Service Ready Program で検証済み**のストレージパートナーとして利用可能になっています。[（参考: AWS Blog）](https://aws.amazon.com/blogs/compute/new-simplifying-the-use-of-third-party-block-storage-with-aws-outposts/) [（参考: NetApp）](https://netapp.com/aws/outposts/)

EC2 インスタンスのデータボリュームとして NetApp ONTAP の iSCSI LUN を AWS コンソールから直接アタッチでき、さらに 2025年7月にはブートボリュームのサポートも追加されています。[（参考: AWS Blog）](https://aws.amazon.com/blogs/compute/deploying-external-boot-volumes-with-aws-outposts/)

**NetApp エコシステムの観点**: Outposts + ONTAP の組み合わせにより、「コンピュートは AWS マネージド、ストレージは既存の ONTAP」という**コンピュートとストレージの分離**が実現します。これはオンプレ ONTAP → FSx for ONTAP（クラウド）→ Outposts + ONTAP（ハイブリッド）という一貫したデータプラットフォームの構築を可能にします。

#### 5. パートナーソリューション（ROSA / NC2 + NetApp 連携の拡大）

**Red Hat OpenShift Service on AWS (ROSA):** OpenShift ベースのフルマネージドアプリケーションプラットフォーム。コンテナ化されたワークロードの実行環境として、VM から OpenShift への移行パスを提供。NetApp Trident CSI ドライバにより、ROSA の Pod から FSx for ONTAP に NFS/iSCSI でアクセス可能です。[（参考）](https://aws.amazon.com/rosa/)

**Nutanix Cloud Clusters on AWS (NC2) + NetApp ONTAP:**

2026年4月、Nutanix と NetApp は戦略的パートナーシップを発表し、**NetApp ONTAP が Nutanix Cloud Platform の外部ストレージとして統合される**ことが明らかになりました。NFS ベースの接続により、コンピュート（Nutanix AHV）とストレージ（ONTAP）の独立スケーリングが可能になります。[（参考: NetApp Blog）](https://www.netapp.com/blog/modernize-virtualization-nutanix-partnership/) [（参考: NetApp Press Release）](https://www.netapp.com/newsroom/press-releases/news-rel-20260407-695711/)

Nutanix CEO Rajiv Ramaswami 氏は「外部ストレージプラットフォームのサポートが、大幅なハードウェア変更なしでの Nutanix 移行を簡素化している」と述べています。（Q1 FY2027 Earnings Call での発言として報道）

**NetApp エコシステムとしての全体像:**

```
┌─────────────────────────────────────────────────────────────┐
│          NetApp ONTAP — データの可搬性と一貫性                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  オンプレ                    AWS                            │
│  ┌──────────────┐           ┌──────────────────────┐       │
│  │ ONTAP (FAS/  │◄─SnapMirror─►│ FSx for ONTAP      │       │
│  │   AFF)       │           │  (EC2/ECS/EKS/EVS)  │       │
│  └──────┬───────┘           └──────────┬───────────┘       │
│         │                              │                    │
│  ┌──────▼───────┐           ┌──────────▼───────────┐       │
│  │ VMware ESXi  │           │ Amazon EC2 (Nitro)   │       │
│  │ Nutanix AHV  │           │ Amazon EVS           │       │
│  │ Hyper-V      │           │ ROSA                 │       │
│  │ OpenShift    │           │ NC2 on AWS           │       │
│  │ Proxmox      │           │ Outposts + ONTAP     │       │
│  └──────────────┘           └──────────────────────┘       │
│                                                             │
│  共通: Snapshot / FlexClone / SnapMirror / Efficiency       │
│  共通: NFS / SMB / iSCSI / S3 マルチプロトコル              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

この図が示すのは、**ONTAP はハイパーバイザーやクラウドの選択に依存しないデータプラットフォーム**だということです。VMware から EC2 へ、あるいは Nutanix へ、さらには ROSA へとコンピュート層を変えても、データ層の ONTAP は一貫して利用でき、SnapMirror でデータを移動・保護できます。

Shift Toolkit による VMware → EC2/FSxN 移行は、このエコシステムの中の**1つの移行パス**であり、将来的に NC2 + ONTAP や ROSA + FSxN へのワークロード再配置が必要になった場合にも、データ層の互換性が保たれます。

### 本検証の位置づけ

```
VMware ESXi (現在地)
    │
    ├─ Phase 1: リホスト ← 本検証のスコープ
    │   EC2 + FSx for ONTAP (iSCSI)
    │   Shift Toolkit でデータディスク変換
    │
    ├─ Phase 2: リプラットフォーム（将来）
    │   EC2 上のアプリをコンテナ化
    │   → ECS/EKS + FSxN (NFS/iSCSI)
    │
    └─ Phase 3: リファクタ（将来）
        ステートレス化 → Fargate / Lambda
        データ層は FSxN / S3 / DynamoDB に分離
```

本検証は **Phase 1（リホスト）** に集中しますが、EC2 + FSx for ONTAP の構成は Phase 2 以降への移行パスを閉じない設計になっています。FSx for ONTAP は EC2 だけでなく ECS/EKS からも NFS/iSCSI でアクセスできるため、コンテナ化した後もデータ層をそのまま維持できます。

## なぜ「EC2 + FSx for ONTAP」なのか

5つのパスウェイの中で「EC2 + FSx for ONTAP」に注目する理由を整理します。

### リホストの入口であり、モダナイゼーションの基盤

EC2 + FSx for ONTAP の構成は、単なるリホスト先ではなく、**将来のモダナイゼーションを閉じない設計**です。

- **今（Phase 1）**: VM を EC2 にリホスト。データディスクは FSxN iSCSI
- **次（Phase 2）**: アプリをコンテナ化。ECS/EKS から FSxN に NFS/iSCSI でアクセス継続
- **将来（Phase 3）**: ステートレス化した部分は Fargate/Lambda へ。データ層の FSxN はそのまま

FSx for ONTAP がマルチプロトコル（NFS/SMB/iSCSI）でアクセスできることが、この段階的移行を支えます。EC2 の iSCSI LUN として使っていたボリュームを、後から EKS Pod に NFS マウントすることも可能です。

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

- [AWS for VMware — Comprehensive Pathways](https://aws.amazon.com/vmware/explore/)
- [AWS Transform for VMware](https://aws.amazon.com/transform/vmware/)
- [AWS for VMware Partner Offerings (ROSA, NC2)](https://aws.amazon.com/vmware/partner-offerings/)
- [NetApp Shift Toolkit Overview](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/shift-toolkit-overview.html)
- [AWS Storage Blog: Seamless migration from VMware to FSx ONTAP and EC2](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [AWS Storage Blog: BlueXP Migration Advisor](https://aws.amazon.com/blogs/storage/expedite-vmware-migration-to-amazon-ec2-and-amazon-fsx-for-netapp-ontap-using-bluexp-workload-factory-for-aws-migration-advisor/)
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)
- [Amazon Elastic VMware Service (EVS)](https://aws.amazon.com/evs/)
- [Red Hat OpenShift Service on AWS (ROSA)](https://aws.amazon.com/rosa/)
- [Nutanix Cloud Clusters on AWS (NC2)](https://aws.amazon.com/blogs/apn/accelerate-vmware-migrations-to-aws-with-nutanix-nc2/)
- [AWS VMware Migration Accelerator](https://aws.amazon.com/vmware/migrationaccelerator/)
- [NetApp Blog: Simplify VM migration with Shift Toolkit](https://www.netapp.com/blog/simplify-vm-migration-shift-toolkit/)

---

*本記事は NetApp Shift Toolkit Early Preview の検証シリーズ第1回です。Early Preview の仕様は変更される可能性があります。*
