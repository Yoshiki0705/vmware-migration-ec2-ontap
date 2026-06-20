# NetApp 確認事項一覧 — VMware → EC2 / FSx for ONTAP 移行

> 目的: Shift Toolkit (Early Preview) と AWS Transform (Public Preview) を踏まえた
> 移行パスの確認。すべて公開情報ベースの技術質問であり、案件固有情報・社名・
> 内部識別子は含まない。

**背景（公開情報）:**

- NetApp Shift Toolkit が VMware ESXi → Amazon EC2 / FSx for ONTAP 移行を Early Preview で提供
- 2026-06-16: AWS Transform for migrations が FSx for ONTAP を移行先としてサポート（Public Preview）
  - [AWS What's New](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/)

---

## 1. OS / ルートディスクのブート方式（最優先）

EC2 は AMI（EBS バックド）からのみブート可能で、FSx for ONTAP iSCSI LUN から直接起動はできない、という物理制約の確認。

| # | 質問 | 優先度 |
|---|------|--------|
| Q1 | Shift Toolkit Early Preview は OS ディスクの AMI 変換まで含むか、データディスクの FSx for ONTAP 配置のみか? | Critical |
| Q2 | OS ディスクのみ別ツール（VM Import/Export, AWS MGN 等）併用が必要となるケースの想定はあるか? | Critical |
| Q3 | Shift Toolkit が変換した中間フォーマット（RAW/QCOW2）から AMI を作成する標準手順は提供されるか? | High |
| Q4 | EC2 起動後に必要な OS 修正（Nitro ドライバ、ENA、NVMe 対応）は自動化されるか、手動対応か? | High |

## 2. AWS Transform と Shift Toolkit の関係

| # | 質問 | 優先度 |
|---|------|--------|
| Q5 | AWS Transform の FSx for ONTAP 移行は内部で Shift Toolkit / FlexClone / SnapMirror を利用するのか、AWS ネイティブのブロックレプリケーションか? | Critical |
| Q6 | NetApp DII 連携は AWS Transform の discovery（計画）フェーズのみか、移行実行フェーズにも及ぶか? | High |
| Q7 | NetApp として、顧客への Shift Toolkit と AWS Transform の使い分け案内方針は（置き換え / 補完 / 並存）? | High |
| Q8 | AWS Transform でコンピュート（ルート = EBS）、Shift Toolkit でデータ（FSx for ONTAP）を分担する構成は推奨構成として成立するか? | High |

## 3. FSx for ONTAP 移行先としての仕様

| # | 質問 | 優先度 |
|---|------|--------|
| Q9 | AWS Transform の FSx for ONTAP 移行先はブロック（iSCSI LUN）のみか、NFS データストア相当も対象か? | High |
| Q10 | 移行後に Snapshot / SnapMirror / FlexClone / Storage Efficiency はそのまま継続利用できるか（系譜・メタデータの引き継ぎ有無）? | Critical |
| Q11 | 対応リージョン（東京 ap-northeast-1）での Preview 利用可否、Preview の制約、GA 時期の見通しは? | Medium |

## 4. 前提・運用

| # | 質問 | 優先度 |
|---|------|--------|
| Q12 | Shift Toolkit の「ソース VM は ONTAP NFS データストア上が必須」という前提は EC2 移行パスでも同じか? | Medium |
| Q13 | 同時変換の並列数（最大 10 推奨）は EC2 移行パスでも同じか? | Low |
| Q14 | Early Preview / Public Preview 検証結果の公開可能範囲（NDA 対象の有無）は? | Medium |

## 5. DR（災害対策）シナリオ

| # | 質問 | 優先度 |
|---|------|--------|
| Q15 | VMware×ONTAP → EC2×FSx for ONTAP の DR は SnapMirror（継続レプリ）＋ EC2 復旧が推奨構成か? 他の推奨パターンはあるか? | High |
| Q16 | AWS Transform は DR 用途（継続レプリケーション）に使えるか、それとも移行専用か?（弊チーム理解では移行専用） | High |
| Q17 | FSx for ONTAP destination を break→RW 化して EC2 から iSCSI アタッチする復旧フローの推奨手順・注意点は? | High |
| Q18 | フェイルバック（DR→オンプレ resync）の推奨手順と停止ウィンドウの目安は? | Medium |
| Q19 | 本番レプリを断たずに DR テストする手法は FlexClone が推奨か? 他の方法は? | Medium |
| Q20 | クロスリージョン DR（FSx for ONTAP→別リージョン FSx for ONTAP）の構成・制約は? | Low |

---

## 確認方法のメモ

- Shift Toolkit Early Preview の有効化: [MySupport Shift Toolkit ページ](https://mysupport.netapp.com/site/tools/tool-eula/netapp-shift-toolkit)（NetApp Support アカウント要）
- AWS Transform の FSx for ONTAP 宛先 UI: VMware migration の移行ウェーブ計画フロー内で確認（ジョブ作成・discovery データ投入が前提）

> 注: 本一覧は公開情報に基づく技術確認用。回答受領後、`research.md` の 3.2.1 / 3.2.4 の
> 想定（推定）箇所を確定情報に更新すること。
