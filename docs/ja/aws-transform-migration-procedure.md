# 手順: AWS Transform による VMware → EC2 / FSx for ONTAP 移行

**目的**: AWS Transform（エージェント型 AI の移行サービス）を用いて、VMware ワークロードを Amazon EC2 へリホストし、ブロックデータを Amazon FSx for NetApp ONTAP へ配置する移行手順。

> ⚠️ **Public Preview / 2026-06 時点**。FSxN を移行先とする機能は Public Preview。対応リージョン・UI・制約は変更されうる。GA 仕様としては扱わない。一次情報: [What's New](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/) / [AWS Transform pricing](https://aws.amazon.com/transform/pricing/)

---

## 0. 位置づけ

- AWS Transform は **移行ウェーブ全体（discovery → 計画 → コンピュート + ネットワーク + ストレージ）**を回す AWS ネイティブのオーケストレーター。
- VMware 移行エージェント自体の利用は **無料**。移行先の AWS リソース（EC2 / EBS / FSxN / 転送等）は通常課金。
- **OS/ルートは EBS、データは FSxN（iSCSI）** に収束する点は他手法と同じ（EC2 は FSxN から直接ブート不可）。

---

## 1. 前提条件

- AWS アカウント（対象リージョンで AWS Transform / FSxN が利用可能なこと）
- AWS Transform への利用権限。アクセス方式は次のいずれか:
  - **Web API 認証（SSO / IAM Identity Center もしくは Cookie）**
  - **SigV4（AWS 認証情報）**: アカウントが Transform API に対応している場合
- discovery 用インベントリ: RVTools / NetApp DII / Migration Evaluator / MPA エクスポートのいずれか
- 移行先 FSxN ファイルシステム（Multi-AZ 推奨）と SVM（未作成なら計画に含める）
- オンプレ ↔ AWS のネットワーク（VPN/DX）

---

## 2. 操作手段（2通り）

### 2A. AWS マネジメントコンソール

- AWS Transform コンソールで VMware migration の transformation path を開始。
- discovery データ投入 → 依存マッピング → ウェーブ計画 → 移行先（EC2 / ネットワーク / **FSxN ストレージ宛先**）選択 → 実行。

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

1. **Discovery**: RVTools / NetApp DII 等を取り込み、VM・依存関係・ネットワークを把握
2. **Assessment（任意）**: `migration-assessment-agent-v2`（FSxN を含むストレージ推奨・ビジネスケース生成）
3. **計画（ウェーブ）**: 移行単位を分割。各 VM のターゲット（EC2 インスタンスタイプ、ネットワーク、ストレージ宛先）を決定
4. **ストレージ宛先 = FSxN を選択**: ブロックデータを FSxN ボリュームへ。OS/ルートは EBS
5. **実行（リホスト）**: コンピュート＋ネットワーク＋ストレージを同一ウェーブで移行
6. **カットオーバー**: 最終同期 → 切替。停止時間を実測
7. **検証**: EC2 起動、データ整合性、iSCSI/FSxN アクセス、ネットワーク

---

## 4. 検証項目（AWS Transform 移行シナリオ）

| # | 検証項目 | 判定基準 | 備考 |
|---|---------|---------|------|
| T1 | discovery 取り込み | RVTools/DII が正しく解釈される | NetApp DII 連携の挙動を記録 |
| T2 | FSxN 宛先の選択 UI | ウェーブ計画で FSxN を宛先指定できる | マスキングの上スクショ |
| T3 | リホスト後 EC2 起動 | 正常ブート、status check OK | OS=EBS |
| T4 | データの FSxN 配置 | ブロックデータが FSxN ボリュームに配置 | iSCSI/プロトコルを記録 |
| T5 | データ整合性 | 移行前後 sha256sum 一致 | |
| T6 | ONTAP 機能継続 | Snapshot/SnapMirror/Efficiency が利用可能 | **要確認**: レプリ系譜の引き継ぎ |
| T7 | カットオーバー停止時間 | 実測・記録 | |
| T8 | コスト | サービス無料、移行先インフラ実費を分解計上 | research.md 3.2.3 / 6章 Phase 3d |

---

## 5. 確認が必要な未確定事項（NetApp / AWS）

`netapp-questions.md` と連動。特に:

- AWS Transform の FSxN 移行は内部で SnapMirror/FlexClone を使うのか、AWS ネイティブコピーか（移行後の ONTAP 系譜継続性に影響）
- FSxN 宛先はブロック（iSCSI LUN）のみか、NFS データストア相当も対象か
- 対応リージョン（東京 ap-northeast-1 での Preview 可否）と制約・GA 時期

---

*本手順は Public Preview（2026-06 時点）に基づく検証用ドラフト。実機確認後に確定情報へ更新する。*
