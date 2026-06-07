#!/usr/bin/env python3
"""
Parse fio JSON output and generate a summary report.

Usage:
    python3 parse-fio-results.py ./benchmark-results/

Output:
    - Console summary table
    - CSV file for spreadsheet analysis
    - Markdown table for blog/documentation
"""

import json
import sys
from pathlib import Path


def parse_fio_json(filepath: Path) -> dict:
    """Extract key metrics from a fio JSON output file."""
    with open(filepath) as f:
        data = json.load(f)

    job = data["jobs"][0]
    test_name = job["jobname"]

    # Determine if read or write test
    if "read" in test_name:
        metrics = job["read"]
        direction = "read"
    else:
        metrics = job["write"]
        direction = "write"

    lat_ns = metrics.get("clat_ns", metrics.get("lat_ns", {}))
    percentiles = lat_ns.get("percentile", {})

    return {
        "test_name": test_name,
        "direction": direction,
        "iops": round(metrics["iops"], 1),
        "bw_mbs": round(metrics["bw"] / 1024, 2),  # KiB/s -> MiB/s
        "lat_avg_us": round(lat_ns.get("mean", 0) / 1000, 2),
        "lat_p50_us": round(percentiles.get("50.000000", 0) / 1000, 2),
        "lat_p90_us": round(percentiles.get("90.000000", 0) / 1000, 2),
        "lat_p95_us": round(percentiles.get("95.000000", 0) / 1000, 2),
        "lat_p99_us": round(percentiles.get("99.000000", 0) / 1000, 2),
        "lat_max_us": round(lat_ns.get("max", 0) / 1000, 2),
    }


def format_iops(value: float) -> str:
    """Format IOPS with K suffix for readability."""
    if value >= 1000:
        return f"{value / 1000:.1f}K"
    return f"{value:.0f}"


def generate_markdown_table(results: list[dict], env_data: dict | None) -> str:
    """Generate a markdown table suitable for blog/docs."""
    lines = []

    if env_data:
        lines.append(f"**Benchmark Run ID**: `{env_data.get('benchmark_run_id', 'N/A')}`\n")
        lines.append("| Parameter | Value |")
        lines.append("|-----------|-------|")
        lines.append(f"| Instance Type | {env_data.get('instance_type', 'N/A')} |")
        lines.append(f"| Device Size | {env_data.get('device_size_gb', 'N/A')} GB |")
        lines.append(f"| iSCSI Sessions | {env_data.get('iscsi_sessions', 'N/A')} |")
        lines.append(f"| Multipath Paths | {env_data.get('multipath_paths', 'N/A')} |")
        lines.append(f"| Runtime/Test | {env_data.get('runtime_seconds', 'N/A')}s |")
        lines.append(f"| Kernel | {env_data.get('kernel', 'N/A')} |")
        lines.append("")

    lines.append(
        "| Test | IOPS | Throughput (MiB/s) | Avg Lat (μs) | P50 (μs) | P99 (μs) | Max (μs) |"
    )
    lines.append(
        "|------|------|--------------------|-------------|----------|----------|----------|"
    )

    for r in results:
        lines.append(
            f"| {r['test_name']} | {format_iops(r['iops'])} | {r['bw_mbs']} | "
            f"{r['lat_avg_us']} | {r['lat_p50_us']} | {r['lat_p99_us']} | {r['lat_max_us']} |"
        )

    lines.append("")
    lines.append(
        "> ⚠️ These results are a **sizing reference** for this specific test environment. "
        "They do NOT represent FSx for ONTAP service limits."
    )

    return "\n".join(lines)


def generate_csv(results: list[dict]) -> str:
    """Generate CSV for spreadsheet analysis."""
    headers = "test_name,direction,iops,bw_mbs,lat_avg_us,lat_p50_us,lat_p90_us,lat_p95_us,lat_p99_us,lat_max_us"
    lines = [headers]
    for r in results:
        lines.append(
            f"{r['test_name']},{r['direction']},{r['iops']},{r['bw_mbs']},"
            f"{r['lat_avg_us']},{r['lat_p50_us']},{r['lat_p90_us']},"
            f"{r['lat_p95_us']},{r['lat_p99_us']},{r['lat_max_us']}"
        )
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 parse-fio-results.py <results_directory>")
        sys.exit(1)

    results_dir = Path(sys.argv[1])
    if not results_dir.is_dir():
        print(f"ERROR: {results_dir} is not a directory")
        sys.exit(1)

    # Find fio result files
    fio_files = sorted(results_dir.glob("*k-*.json"))
    if not fio_files:
        print(f"No fio result files found in {results_dir}")
        sys.exit(1)

    # Find environment metadata
    env_files = list(results_dir.glob("environment-*.json"))
    env_data = None
    if env_files:
        with open(env_files[0]) as f:
            env_data = json.load(f)

    # Parse all results
    results = []
    for filepath in fio_files:
        try:
            result = parse_fio_json(filepath)
            results.append(result)
        except (KeyError, json.JSONDecodeError) as e:
            print(f"WARNING: Could not parse {filepath}: {e}")

    if not results:
        print("No valid results to report.")
        sys.exit(1)

    # Console output
    print("\n" + "=" * 70)
    print("  FSx for ONTAP iSCSI Benchmark Summary")
    print("=" * 70)
    if env_data:
        print(f"  Run ID:    {env_data.get('benchmark_run_id')}")
        print(f"  Instance:  {env_data.get('instance_type')}")
        print(f"  Device:    {env_data.get('device_size_gb')} GB")
    print("-" * 70)
    print(f"  {'Test':<20} {'IOPS':>8} {'BW (MiB/s)':>12} {'Avg Lat':>10} {'P99 Lat':>10}")
    print("-" * 70)
    for r in results:
        print(
            f"  {r['test_name']:<20} {format_iops(r['iops']):>8} "
            f"{r['bw_mbs']:>12} {r['lat_avg_us']:>8} μs {r['lat_p99_us']:>8} μs"
        )
    print("=" * 70)
    print()

    # Save markdown
    md_output = results_dir / "summary.md"
    md_output.write_text(generate_markdown_table(results, env_data))
    print(f"✅ Markdown summary: {md_output}")

    # Save CSV
    csv_output = results_dir / "summary.csv"
    csv_output.write_text(generate_csv(results))
    print(f"✅ CSV summary: {csv_output}")


if __name__ == "__main__":
    main()
