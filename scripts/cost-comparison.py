#!/usr/bin/env python3
"""
EBS vs FSx for ONTAP コスト比較スクリプト

目的: 移行後のストレージコストを EBS のみ構成と EBS + FSx for ONTAP ハイブリッド構成で比較する。
東京リージョン (ap-northeast-1) の料金で計算。

Usage:
    python3 cost-comparison.py --data-size 1000 --throughput 512
    python3 cost-comparison.py --data-size 500 --throughput 256 --efficiency 0.6

注意: 料金は 2026年6月時点のもの。最新料金は以下で確認:
  https://aws.amazon.com/fsx/netapp-ontap/pricing/
  https://aws.amazon.com/ebs/pricing/
"""

import argparse
import json
from dataclasses import dataclass

# ==============================================================================
# 料金定義（ap-northeast-1, 2026年6月時点）
# 出典: https://aws.amazon.com/fsx/netapp-ontap/pricing/
#        https://aws.amazon.com/ebs/pricing/
# ==============================================================================


@dataclass
class FsxnPricing:
    """FSx for ONTAP 料金 (ap-northeast-1, Multi-AZ)"""

    ssd_per_gb_month: float = 0.250  # SSD ストレージ $/GB/月
    capacity_pool_per_gb_month: float = 0.020  # 容量プールストレージ $/GB/月
    throughput_per_mbps_month: float = 0.500  # スループット容量 $/MBps/月
    # 備考: プロビジョニング SSD の上に Tiering で容量プールを利用可能
    # iSCSI アクセスに追加料金なし


@dataclass
class EbsPricing:
    """EBS 料金 (ap-northeast-1)"""

    gp3_per_gb_month: float = 0.096  # gp3 $/GB/月
    gp3_baseline_iops: int = 3000  # gp3 ベースライン IOPS（無料）
    gp3_baseline_throughput: int = 125  # gp3 ベースラインスループット MB/s（無料）
    gp3_iops_per_month: float = 0.006  # 追加 IOPS $/IOPS/月 (3000 超過分)
    gp3_throughput_per_mbps_month: float = 0.048  # 追加スループット $/MBps/月 (125 超過分)
    io2_per_gb_month: float = 0.142  # io2 $/GB/月
    io2_per_iops_month: float = 0.074  # io2 $/IOPS/月


# ==============================================================================
# 計算ロジック
# ==============================================================================


def calculate_fsxn_cost(
    data_size_gb: float,
    throughput_mbps: int,
    ssd_ratio: float = 0.2,
    efficiency_ratio: float = 1.0,
    pricing: FsxnPricing | None = None,
) -> dict:
    """
    FSx for ONTAP の月額コストを計算。

    Args:
        data_size_gb: 論理データサイズ (GB)
        throughput_mbps: プロビジョニングスループット (MB/s)
        ssd_ratio: SSD に配置されるデータの割合 (0.0-1.0)
        efficiency_ratio: Storage Efficiency 後の実効データ率 (例: 0.6 = 40%削減)
        pricing: 料金オブジェクト
    """
    if pricing is None:
        pricing = FsxnPricing()
    # Storage Efficiency 適用後の物理容量
    physical_size_gb = data_size_gb * efficiency_ratio

    # SSD と容量プールの配分
    ssd_size_gb = physical_size_gb * ssd_ratio
    capacity_pool_gb = physical_size_gb * (1 - ssd_ratio)

    # 各コスト要素
    ssd_cost = ssd_size_gb * pricing.ssd_per_gb_month
    capacity_pool_cost = capacity_pool_gb * pricing.capacity_pool_per_gb_month
    throughput_cost = throughput_mbps * pricing.throughput_per_mbps_month

    total = ssd_cost + capacity_pool_cost + throughput_cost

    return {
        "service": "FSx for ONTAP (Multi-AZ)",
        "logical_data_gb": data_size_gb,
        "physical_data_gb": round(physical_size_gb, 1),
        "efficiency_savings_pct": round((1 - efficiency_ratio) * 100, 1),
        "ssd_gb": round(ssd_size_gb, 1),
        "capacity_pool_gb": round(capacity_pool_gb, 1),
        "throughput_mbps": throughput_mbps,
        "cost_ssd": round(ssd_cost, 2),
        "cost_capacity_pool": round(capacity_pool_cost, 2),
        "cost_throughput": round(throughput_cost, 2),
        "total_monthly_usd": round(total, 2),
    }


def calculate_ebs_gp3_cost(
    data_size_gb: float,
    iops: int = 3000,
    throughput_mbps: int = 125,
    pricing: EbsPricing | None = None,
) -> dict:
    """
    EBS gp3 の月額コストを計算。

    Args:
        data_size_gb: データサイズ (GB)
        iops: 必要な IOPS
        throughput_mbps: 必要なスループット (MB/s)
        pricing: 料金オブジェクト
    """
    if pricing is None:
        pricing = EbsPricing()
    storage_cost = data_size_gb * pricing.gp3_per_gb_month

    # 追加 IOPS コスト（3000 超過分）
    extra_iops = max(0, iops - pricing.gp3_baseline_iops)
    iops_cost = extra_iops * pricing.gp3_iops_per_month

    # 追加スループットコスト（125 MB/s 超過分）
    extra_throughput = max(0, throughput_mbps - pricing.gp3_baseline_throughput)
    throughput_cost = extra_throughput * pricing.gp3_throughput_per_mbps_month

    total = storage_cost + iops_cost + throughput_cost

    return {
        "service": "EBS gp3",
        "data_gb": data_size_gb,
        "provisioned_iops": iops,
        "provisioned_throughput_mbps": throughput_mbps,
        "cost_storage": round(storage_cost, 2),
        "cost_extra_iops": round(iops_cost, 2),
        "cost_extra_throughput": round(throughput_cost, 2),
        "total_monthly_usd": round(total, 2),
    }


def calculate_ebs_io2_cost(
    data_size_gb: float,
    iops: int = 10000,
    pricing: EbsPricing | None = None,
) -> dict:
    """EBS io2 の月額コスト計算（高 IOPS 要件向け）。"""
    if pricing is None:
        pricing = EbsPricing()
    storage_cost = data_size_gb * pricing.io2_per_gb_month
    iops_cost = iops * pricing.io2_per_iops_month
    total = storage_cost + iops_cost

    return {
        "service": "EBS io2",
        "data_gb": data_size_gb,
        "provisioned_iops": iops,
        "cost_storage": round(storage_cost, 2),
        "cost_iops": round(iops_cost, 2),
        "total_monthly_usd": round(total, 2),
    }


# ==============================================================================
# レポート生成
# ==============================================================================


def generate_comparison_report(
    data_size_gb: float, throughput_mbps: int, efficiency_ratio: float, iops: int
) -> str:
    """比較レポートを Markdown 形式で生成。"""
    fsxn = calculate_fsxn_cost(data_size_gb, throughput_mbps, efficiency_ratio=efficiency_ratio)
    ebs_gp3 = calculate_ebs_gp3_cost(data_size_gb, iops=iops, throughput_mbps=throughput_mbps)
    ebs_io2 = calculate_ebs_io2_cost(data_size_gb, iops=iops)

    # OS ディスク（EBS gp3 50GB）は両方の構成で共通
    os_disk_cost = 50 * EbsPricing().gp3_per_gb_month

    lines = []
    lines.append("# ストレージコスト比較レポート")
    lines.append("")
    lines.append("**リージョン**: ap-northeast-1 (東京)")
    lines.append(f"**データサイズ**: {data_size_gb} GB (論理)")
    lines.append(f"**必要 IOPS**: {iops}")
    lines.append(f"**必要スループット**: {throughput_mbps} MB/s")
    lines.append(f"**Storage Efficiency 想定削減率**: {round((1 - efficiency_ratio) * 100)}%")
    lines.append("")
    lines.append(
        "> ⚠️ 料金は 2026年6月時点の公開情報に基づく概算。最新料金は AWS 公式ページで確認。"
    )
    lines.append("")
    lines.append("## 構成比較")
    lines.append("")
    lines.append("| 項目 | 構成 A: EBS gp3 のみ | 構成 B: EBS + FSx for ONTAP | 構成 C: EBS io2 (高IOPS) |")
    lines.append("|------|---------------------|-------------------|------------------------|")
    lines.append("| OS ディスク | EBS gp3 50GB | EBS gp3 50GB | EBS gp3 50GB |")
    lines.append(
        f"| データディスク | EBS gp3 {data_size_gb}GB | FSx for ONTAP iSCSI {data_size_gb}GB | EBS io2 {data_size_gb}GB |"
    )
    lines.append(f"| IOPS | {iops} | FSx for ONTAP (NVMe cache) | {iops} |")
    lines.append("| Snapshot | EBS Snapshot | ONTAP Snapshot (即時) | EBS Snapshot |")
    lines.append("| Clone | 不可 | FlexClone (即時) | 不可 |")
    lines.append("| Replication | EBS 間コピー | SnapMirror (効率的) | EBS 間コピー |")
    lines.append(
        f"| Dedup/Compression | なし | あり ({round((1 - efficiency_ratio) * 100)}% 削減想定) | なし |"
    )
    lines.append("")
    lines.append("## 月額コスト詳細")
    lines.append("")
    lines.append("### 構成 A: EBS gp3 のみ")
    lines.append(f"- OS ディスク: ${os_disk_cost:.2f}")
    lines.append(f"- データストレージ: ${ebs_gp3['cost_storage']:.2f}")
    lines.append(f"- 追加 IOPS: ${ebs_gp3['cost_extra_iops']:.2f}")
    lines.append(f"- 追加スループット: ${ebs_gp3['cost_extra_throughput']:.2f}")
    lines.append(f"- **合計: ${os_disk_cost + ebs_gp3['total_monthly_usd']:.2f}/月**")
    lines.append("")
    lines.append("### 構成 B: EBS (OS) + FSx for ONTAP (Data)")
    lines.append(f"- OS ディスク (EBS gp3): ${os_disk_cost:.2f}")
    lines.append(f"- FSx for ONTAP SSD ({fsxn['ssd_gb']} GB): ${fsxn['cost_ssd']:.2f}")
    lines.append(
        f"- FSx for ONTAP 容量プール ({fsxn['capacity_pool_gb']} GB): ${fsxn['cost_capacity_pool']:.2f}"
    )
    lines.append(f"- FSx for ONTAP スループット ({throughput_mbps} MB/s): ${fsxn['cost_throughput']:.2f}")
    lines.append(f"- **合計: ${os_disk_cost + fsxn['total_monthly_usd']:.2f}/月**")
    lines.append(f"- (Storage Efficiency により物理容量 {fsxn['physical_data_gb']} GB)")
    lines.append("")
    lines.append("### 構成 C: EBS io2 (高 IOPS)")
    lines.append(f"- OS ディスク (EBS gp3): ${os_disk_cost:.2f}")
    lines.append(f"- データストレージ: ${ebs_io2['cost_storage']:.2f}")
    lines.append(f"- IOPS: ${ebs_io2['cost_iops']:.2f}")
    lines.append(f"- **合計: ${os_disk_cost + ebs_io2['total_monthly_usd']:.2f}/月**")
    lines.append("")
    lines.append("## コスト比較サマリー")
    lines.append("")
    total_a = os_disk_cost + ebs_gp3["total_monthly_usd"]
    total_b = os_disk_cost + fsxn["total_monthly_usd"]
    total_c = os_disk_cost + ebs_io2["total_monthly_usd"]
    lines.append("| 構成 | 月額 | 年額 | 対構成 A 比 |")
    lines.append("|------|------|------|-----------|")
    lines.append(f"| A: EBS gp3 のみ | ${total_a:.2f} | ${total_a * 12:.2f} | — |")
    lines.append(
        f"| B: EBS + FSx for ONTAP | ${total_b:.2f} | ${total_b * 12:.2f} | {((total_b / total_a) - 1) * 100:+.1f}% |"
    )
    lines.append(
        f"| C: EBS io2 | ${total_c:.2f} | ${total_c * 12:.2f} | {((total_c / total_a) - 1) * 100:+.1f}% |"
    )
    lines.append("")
    lines.append("## FSx for ONTAP が有利になるポイント")
    lines.append("")
    lines.append("FSx for ONTAP の月額コストが EBS より高い場合でも、以下の機能価値を考慮:")
    lines.append("- **ONTAP Snapshot**: 数秒で取得。EBS Snapshot は非同期でコピー時間が必要")
    lines.append("- **FlexClone**: データコピーなしの即時クローン。テスト環境の即時作成")
    lines.append("- **SnapMirror**: 効率的なブロックレプリケーション。DR コスト削減")
    lines.append("- **Storage Efficiency**: 実効容量を削減。データが増えるほど効果大")
    lines.append("- **VM レベル I/O 制限なし**: EBS は EC2 インスタンスタイプで I/O 上限あり")
    lines.append("")
    lines.append("> 結論: 純粋なストレージ容量コストだけでは FSx for ONTAP の価値は測れない。")
    lines.append(
        "> 運用効率（Snapshot/Clone/DR）+ 実効容量削減 + I/O 柔軟性を含めた TCO で判断すべき。"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本レポートは概算であり、実際の請求額とは異なる場合があります。*")
    lines.append("*最新料金: https://aws.amazon.com/fsx/netapp-ontap/pricing/*")

    return "\n".join(lines)


# ==============================================================================
# メイン
# ==============================================================================


def main():
    parser = argparse.ArgumentParser(description="EBS vs FSx for ONTAP コスト比較")
    parser.add_argument("--data-size", type=float, default=500, help="データサイズ (GB)")
    parser.add_argument("--throughput", type=int, default=512, help="FSx for ONTAP スループット (MB/s)")
    parser.add_argument(
        "--efficiency",
        type=float,
        default=0.65,
        help="Storage Efficiency 後の実効率 (0.65 = 35%%削減)",
    )
    parser.add_argument("--iops", type=int, default=5000, help="必要 IOPS")
    parser.add_argument("--output", type=str, default=None, help="出力ファイルパス (.md)")
    parser.add_argument("--json", action="store_true", help="JSON 形式でも出力")

    args = parser.parse_args()

    report = generate_comparison_report(
        data_size_gb=args.data_size,
        throughput_mbps=args.throughput,
        efficiency_ratio=args.efficiency,
        iops=args.iops,
    )

    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\n✅ レポート保存: {args.output}")

    if args.json:
        results = {
            "fsxn": calculate_fsxn_cost(
                args.data_size, args.throughput, efficiency_ratio=args.efficiency
            ),
            "ebs_gp3": calculate_ebs_gp3_cost(
                args.data_size, iops=args.iops, throughput_mbps=args.throughput
            ),
            "ebs_io2": calculate_ebs_io2_cost(args.data_size, iops=args.iops),
        }
        json_path = (args.output or "cost-comparison") + ".json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"✅ JSON 保存: {json_path}")


if __name__ == "__main__":
    main()
