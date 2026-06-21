# NetApp 確認事項一覧 — VMware → EC2 / FSx for ONTAP 移行

> 目的: Shift Toolkit (Early Preview) と AWS Transform (Public Preview) を踏まえた
> 移行パスの確認。すべて公開情報ベースの技術質問であり、案件固有情報・社名・
> 内部識別子は含まない。

**背景（公開情報）:**

- NetApp Shift Toolkit が VMware ESXi → Amazon EC2 / FSx for ONTAP 移行を Early Preview で提供
- 2026-06-16: AWS Transform for migrations が FSx for ONTAP を移行先としてサポート（Public Preview）
  - [AWS What's New](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/)
- 2026-06-19: Shift Toolkit v8.0 リリース — EC2 + FSx for ONTAP が Early Preview として正式発表
  - [Tech ONTAP Blog: What's New in Shift v8.0](https://community.netapp.com/t5/Tech-ONTAP-Blogs/What-s-New-in-Shift-v8-0-File-to-LUN-EC2-FSx-for-ONTAP-Trident-Integration-amp/ba-p/467669)

---

## 回答ステータス凡例

| ステータス | 意味 |
|-----------|------|
| ✅ 確認済み | 公開ブログ/ドキュメントで回答が得られた |
| 🔶 部分回答 | 情報はあるが詳細確認が必要 |
| ⬜ 未回答 | ブログ/ドキュメントでカバーされていない — 要確認 |

---

## 1. OS / ルートディスクのブート方式（最優先）

EC2 は AMI（EBS バックド）からのみブート可能で、FSx for ONTAP iSCSI LUN から直接起動はできない、という物理制約の確認。

| # | 質問 | 優先度 | ステータス |
|---|------|--------|-----------|
| Q1 | Shift Toolkit Early Preview は OS ディスクの AMI 変換まで含むか、データディスクの FSx for ONTAP 配置のみか? | Critical | ✅ 確認済み |
| Q2 | OS ディスクのみ別ツール（VM Import/Export, AWS MGN 等）併用が必要となるケースの想定はあるか? | Critical | 🔶 部分回答 |
| Q3 | Shift Toolkit が変換した中間フォーマット（RAW/QCOW2）から AMI を作成する標準手順は提供されるか? | High | 🔶 部分回答 |
| Q4 | EC2 起動後に必要な OS 修正（Nitro ドライバ、ENA、NVMe 対応）は自動化されるか、手動対応か? | High | ⬜ 未回答 |

### Q1–Q3 回答根拠（Shift v8.0 ブログ 2026-06-19）

> Shift Toolkit v8.0 also introduces support for migrating to AWS by **converting the OS disks to EBS format** and associated data disks to Amazon FSx for ONTAP.
> The migration approach provides both **AWS Import/Export APIs for import** and **Direct Access APIs for EBS snapshot creation** as the options for OS disk conversions.

- **Q1**: OS ディスクの EBS 変換は Shift Toolkit 自身がカバーする。データディスクのみではない。
- **Q2**: Shift 自身が OS→EBS を担うため、別ツール併用は基本不要と読める。ただし Early Preview 制約下で非対応 OS がある場合は別途確認が必要。
- **Q3**: EBS snapshot 作成 API を直接使う方式が示されており、中間フォーマット経由ではなく EBS snapshot → AMI の直接パスが提供される模様。詳細手順は未公開。

## 2. AWS Transform と Shift Toolkit の関係

| # | 質問 | 優先度 | ステータス |
|---|------|--------|-----------|
| Q5 | AWS Transform の FSx for ONTAP 移行は内部で Shift Toolkit / FlexClone / SnapMirror を利用するのか、AWS ネイティブのブロックレプリケーションか? | Critical | ⬜ 未回答 |
| Q6 | NetApp DII 連携は AWS Transform の discovery（計画）フェーズのみか、移行実行フェーズにも及ぶか? | High | ⬜ 未回答 |
| Q7 | NetApp として、顧客への Shift Toolkit と AWS Transform の使い分け案内方針は（置き換え / 補完 / 並存）? | High | ⬜ 未回答 |
| Q8 | AWS Transform でコンピュート（ルート = EBS）、Shift Toolkit でデータ（FSx for ONTAP）を分担する構成は推奨構成として成立するか? | High | ✅ 確認済み |

### Q8 回答根拠（Shift v8.0 ブログ 2026-06-19）

> converting the OS disks to EBS format and associated data disks to Amazon FSx for ONTAP

- **Q8**: Shift Toolkit 自身が「OS = EBS、データ = FSx for ONTAP」の分離構成を標準パスとして実装している。AWS Transform との分担ではなく、Shift 単体でこの構成を実現。AWS Transform との組み合わせ方針については依然として未回答。

> **注**: Q5–Q7 は Shift v8.0 ブログでは一切触れられていない。AWS Transform との関係は NetApp 側に別途確認が必要。

## 3. FSx for ONTAP 移行先としての仕様

| # | 質問 | 優先度 | ステータス |
|---|------|--------|-----------|
| Q9 | AWS Transform の FSx for ONTAP 移行先はブロック（iSCSI LUN）のみか、NFS データストア相当も対象か? | High | ⬜ 未回答 |
| Q10 | 移行後に Snapshot / SnapMirror / FlexClone / Storage Efficiency はそのまま継続利用できるか（系譜・メタデータの引き継ぎ有無）? | Critical | 🔶 部分回答 |
| Q11 | 対応リージョン（東京 ap-northeast-1）での Preview 利用可否、Preview の制約、GA 時期の見通しは? | Medium | ⬜ 未回答 |

### Q10 回答根拠（Shift v8.0 ブログ 2026-06-19）

> By utilizing ONTAP snapshots, SnapMirror replication, and Amazon FSx for NetApp ONTAP storage service, organizations can easily and quickly migrate VM workloads to Amazon EC2, eliminating the need for the time consuming copy processes typically required in traditional cloud migrations.

- **Q10**: SnapMirror でデータを FSx for ONTAP に転送し、移行後も ONTAP データ管理機能（Snapshot, SnapMirror, FlexClone）が利用可能であることが示唆されている。ただし「メタデータ系譜の引き継ぎ」（Snapshot 履歴の完全移行等）については明記なし。

## 4. 前提・運用

| # | 質問 | 優先度 | ステータス |
|---|------|--------|-----------|
| Q12 | Shift Toolkit の「ソース VM は ONTAP NFS データストア上が必須」という前提は EC2 移行パスでも同じか? | Medium | 🔶 部分回答 |
| Q13 | 同時変換の並列数（最大 10 推奨）は EC2 移行パスでも同じか? | Low | ⬜ 未回答 |
| Q14 | Early Preview / Public Preview 検証結果の公開可能範囲（NDA 対象の有無）は? | Medium | ⬜ 未回答 |

### Q12 回答根拠（Shift v8.0 ブログ 2026-06-19）

ブログでは SnapMirror レプリケーション経由で FSx for ONTAP にデータを転送するフローが記載されており、ソース側が ONTAP NFS データストアである前提は変わらないと推定される。ただし明示的な記載はなく、Early Preview 有効化時に要確認。

## 5. DR（災害対策）シナリオ

| # | 質問 | 優先度 | ステータス |
|---|------|--------|-----------|
| Q15 | VMware×ONTAP → EC2×FSx for ONTAP の DR は SnapMirror（継続レプリ）＋ EC2 復旧が推奨構成か? 他の推奨パターンはあるか? | High | ⬜ 未回答 |
| Q16 | AWS Transform は DR 用途（継続レプリケーション）に使えるか、それとも移行専用か?（弊チーム理解では移行専用） | High | ⬜ 未回答 |
| Q17 | FSx for ONTAP destination を break→RW 化して EC2 から iSCSI アタッチする復旧フローの推奨手順・注意点は? | High | ⬜ 未回答 |
| Q18 | フェイルバック（DR→オンプレ resync）の推奨手順と停止ウィンドウの目安は? | Medium | ⬜ 未回答 |
| Q19 | 本番レプリを断たずに DR テストする手法は FlexClone が推奨か? 他の方法は? | Medium | ⬜ 未回答 |
| Q20 | クロスリージョン DR（FSx for ONTAP→別リージョン FSx for ONTAP）の構成・制約は? | Low | ⬜ 未回答 |

> **注**: DR シナリオは Shift Toolkit v8.0 ブログのスコープ外。Shift は移行ツールであり DR ツールではない。DR 関連は別チャネル（AWS Storage Blog / NetApp Solutions ドキュメント / SA 確認）で回答を収集する。

---

## 確認方法のメモ

- Shift Toolkit v8.0 Early Preview の有効化: `ng-shift-toolkit-support@netapp.com` に連絡（ブログ記載）
- Shift Toolkit ダウンロード: [MySupport Shift Toolkit ページ](https://mysupport.netapp.com/site/tools/tool-eula/netapp-shift-toolkit)（NetApp Support アカウント要）
- AWS Transform の FSx for ONTAP 宛先 UI: VMware migration の移行ウェーブ計画フロー内で確認（ジョブ作成・discovery データ投入が前提）

---

## 回答サマリー（2026-06-21 時点）

| カテゴリ | ✅ 確認済み | 🔶 部分回答 | ⬜ 未回答 |
|---------|-----------|-----------|---------|
| 1. OS / ブート方式 | Q1 | Q2, Q3 | Q4 |
| 2. AWS Transform 関係 | Q8 | — | Q5, Q6, Q7 |
| 3. FSx for ONTAP 仕様 | — | Q10 | Q9, Q11 |
| 4. 前提・運用 | — | Q12 | Q13, Q14 |
| 5. DR シナリオ | — | — | Q15–Q20 |

**残存未回答（要 NetApp 確認）**: 12/20 問

> 注: 本一覧は公開情報に基づく技術確認用。回答受領後、`research.md` の 3.2.1 / 3.2.4 の
> 想定（推定）箇所を確定情報に更新すること。
