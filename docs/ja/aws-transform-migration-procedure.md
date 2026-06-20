# 手順: AWS Transform による VMware → EC2 / FSx for ONTAP 移行

**目的**: AWS Transform（エージェント型 AI の移行サービス）を用いて、VMware ワークロードを Amazon EC2 へリホストし、ブロックデータを Amazon FSx for NetApp ONTAP へ配置する移行手順。

> ⚠️ **Public Preview / 2026-06 時点**。FSx for ONTAP を移行先とする機能は Public Preview。対応リージョン・UI・制約は変更されうる。GA 仕様としては扱わない。一次情報: [What's New](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/) / [AWS Transform pricing](https://aws.amazon.com/transform/pricing/)

---

## 0. 位置づけ

- AWS Transform は **移行ウェーブ全体（discovery → 計画 → コンピュート + ネットワーク + ストレージ）**を回す AWS ネイティブのオーケストレーター。
- VMware 移行エージェント自体の利用は **無料**。移行先の AWS リソース（EC2 / EBS / FSx for ONTAP / 転送等）は通常課金。
- **OS/ルートは EBS、データは FSx for ONTAP（iSCSI）** に収束する点は他手法と同じ（EC2 は FSx for ONTAP から直接ブート不可）。

---

## 1. 前提条件

公式ブログ（[Accelerating VMware migration](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migration-aws-transforms-new-experience/)）に基づき整理:

- **AWS Organizations** がセットアップ済み
- **AWS IAM Identity Center** がセットアップ済み（Transform へのユーザー割り当てに使用）
- AWS アカウント構成:
  - **移行計画アカウント**: AWS Transform を稼働させるアカウント（コントロール）
  - **ターゲットアカウント**: 移行先の EC2 / FSx for ONTAP を配置するアカウント
  - 両方同一 Organization 内。小規模なら1アカウントに統合も可
- AWS Transform の利用権限。アクセス方式:
  - **Web API 認証（SSO / IAM Identity Center もしくは Cookie）**
  - **SigV4（AWS 認証情報）**: アカウントが Transform API に対応している場合
- discovery 用インベントリ（以下のいずれか）:
  - **AWS Transform Discovery Collector OVA**（オンプレ vCenter にデプロイ。AWS 接続不要で情報収集、SQL Server検出にも対応）
  - **RVTools** エクスポート（CSV/XLSX）
  - **NetApp DII**
  - **Migration Evaluator / MPA**
  - **PowerCLI ベースコレクタ**（[aws-samples/sample-vmware-collector-v2](https://github.com/aws-samples/sample-vmware-collector-v2)。MPA/ME/RVTools形式で出力。性能データ最大365日を P95 で収集可能）
- 移行先 FSx for ONTAP ファイルシステム（Multi-AZ 推奨）と SVM
- オンプレ ↔ AWS のネットワーク（VPN/DX）

---

## 2. 操作手段（2通り）

### 2A. AWS マネジメントコンソール

- AWS Transform コンソールで VMware migration の transformation path を開始。
- discovery データ投入 → 依存マッピング → ウェーブ計画 → 移行先（EC2 / ネットワーク / **FSx for ONTAP ストレージ宛先**）選択 → 実行。

### 2B. AWS Transform MCP サーバー（本リポジトリで構成済み）

`.kiro/settings/mcp.json` に `awslabs.aws-transform-mcp-server` を設定済み。読み取り系は auto-approve、作成系（`create_workspace` / `create_job` 等）は都度承認。

代表的な操作フロー（自然言語で AI に依頼 → 内部で MCP ツール実行）:

1. 接続確認: `get_status`（SigV4 可否 / 認証状態）
2. エージェント確認: `list_resources(resource="agents", agentType="ORCHESTRATOR_AGENT")` → `vmware-migration-agent-v2` を確認
3. ワークスペース作成: `create_workspace`（※リソース作成。承認のうえ実行）
4. コネクタ作成: `create_connector`（S3 / コードソース。discovery データ用 S3 等）
5. ジョブ作成・開始: `create_job`（orchestratorAgent に VMware 移行エージェントを指定）
6. HITL タスク対応: `list_resources(resource="tasks")` → `get_resource(resource="task")` で内容確認 → **ユーザー承認後に** `complete_task`
7. 状態確認: `get_job_status` / 進行待ちは `adaptive_poll`

> **ガードレール**: HITL タスクは自動承認しない（必ず内容提示→ユーザー判断）。`create_*` / `control_job` / `complete_task` / `accept_connector` は都度確認。

---

## 3. 移行ステップ（ウェーブ）

公式ブログ（[Accelerating VMware migration](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migration-aws-transforms-new-experience/)）と [UserGuide](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-migrate-servers.html) に基づくフロー:

1. **Discovery**: RVTools / NetApp DII / Discovery Collector OVA / PowerCLI コレクタ等を取り込み、VM・依存関係・ネットワークを把握。AI がパターン検出、重複排除、データ品質向上を自動実行
2. **Assessment（任意）**: `migration-assessment-agent-v2`（FSx for ONTAP を含むストレージ推奨・TCO/ビジネスケース生成）
3. **計画（ウェーブ）**: 依存関係ベースで移行ウェーブを自動提案。各 VM のターゲット（EC2 インスタンスタイプ、ネットワーク、ストレージ宛先）を決定。手動での修正・再計画も可能
4. **ネットワーク変換**: VMware vSwitch/ポートグループ/VLAN → AWS Security Group / VPC / サブネットへの変換を自動生成。Cisco ACI / Palo Alto / Fortinet にも対応（2025-12〜）
5. **ストレージ宛先 = FSx for ONTAP を選択**: ブロックデータを FSx for ONTAP ボリュームへ配置。OS/ルートは EBS
6. **レプリケーション**: MGN レプリケーションエージェントをソース VM にデプロイ（自動化可能。[MGN agent automation blog](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migrations-with-aws-transform-and-mgn-replication-agent-installation-automation/) 参照）。データを継続的に同期
7. **テスト**: テストインスタンスを起動し、動作確認
8. **カットオーバー**: 最終同期 → 切替。停止時間を実測。Deployment approvals による HITL 承認あり

---

## 4. 検証項目（AWS Transform 移行シナリオ）

| # | 検証項目 | 判定基準 | 備考 |
|---|---------|---------|------|
| T1 | discovery 取り込み | RVTools/DII が正しく解釈される | NetApp DII 連携の挙動を記録 |
| T2 | FSx for ONTAP 宛先の選択 UI | ウェーブ計画で FSx for ONTAP を宛先指定できる | マスキングの上スクショ |
| T3 | リホスト後 EC2 起動 | 正常ブート、status check OK | OS=EBS |
| T4 | データの FSx for ONTAP 配置 | ブロックデータが FSx for ONTAP ボリュームに配置 | iSCSI/プロトコルを記録 |
| T5 | データ整合性 | 移行前後 sha256sum 一致 | |
| T6 | ONTAP 機能継続 | Snapshot/SnapMirror/Efficiency が利用可能 | **要確認**: レプリ系譜の引き継ぎ |
| T7 | カットオーバー停止時間 | 実測・記録 | |
| T8 | コスト | サービス無料、移行先インフラ実費を分解計上 | research.md 3.2.3 / 6章 Phase 3d |

---

## 5. 確認が必要な未確定事項（NetApp / AWS）

`netapp-questions.md` と連動。特に:

- AWS Transform の FSx for ONTAP 移行は内部で SnapMirror/FlexClone を使うのか、AWS ネイティブコピーか（移行後の ONTAP 系譜継続性に影響）
- FSx for ONTAP 宛先はブロック（iSCSI LUN）のみか、NFS データストア相当も対象か
- 対応リージョン（東京 ap-northeast-1 での Preview 可否）と制約・GA 時期

---

*本手順は Public Preview（2026-06 時点）に基づく検証用ドラフト。実機確認後に確定情報へ更新する。*

---

## 参考リンク

- [AWS Transform VMware — Migrate servers (UserGuide)](https://docs.aws.amazon.com/transform/latest/userguide/transform-vmware-migrate-servers.html)
- [Accelerating VMware migration: AWS Transform's new experience](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migration-aws-transforms-new-experience/) — E2E ウォークスルー
- [Accelerating VMware Cloud Migration with PowerCLI](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-cloud-migration-with-aws-transform-and-powercli/) — PowerCLI コレクタ
- [MGN replication agent installation automation](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migrations-with-aws-transform-and-mgn-replication-agent-installation-automation/) — 大規模エージェントデプロイ
- [Network Migration APIs](https://aws.amazon.com/blogs/migration-and-modernization/automate-large-scale-network-migration-using-aws-transform-network-migration-apis/) — NW 変換 API
- [Guidance for Automated Setup of AWS Transform for VMware](https://aws.amazon.com/solutions/guidance/automated-setup-of-aws-transform-for-vmware/) — テスト環境自動構築
- [AWS Transform pricing](https://aws.amazon.com/transform/pricing/)
- [Migrate VMware to Amazon EC2 & iSCSI-based FSx for ONTAP (NetApp Blog)](https://www.netapp.com/blog/aws-fsxn-blg-migrate-vmware-to-amazon-ec2-iscsi-based-fsx-for-ontap/)
- [aws-samples/sample-vmware-collector-v2](https://github.com/aws-samples/sample-vmware-collector-v2) — PowerCLI インベントリ収集ツール
