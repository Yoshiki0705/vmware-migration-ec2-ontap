# VMware to EC2 + FSx for ONTAP Migration Path Verification

🌐 **Language / 言語**: [日本語](README.md) | English (this page)

> Hands-on verification of VMware ESXi → Amazon EC2 + Amazon FSx for NetApp ONTAP migration using NetApp Shift Toolkit (Early Preview) and AWS Transform (Public Preview)

## Overview

This repository is a verification project for migrating VMware ESXi workloads to Amazon EC2 + Amazon FSx for NetApp ONTAP, evaluating multiple migration paths (NetApp Shift Toolkit / AWS Transform).

### Positioning

The key point of this verification is not just "migrating from VMware to AWS." It's about confirming whether we can leverage the storage operational model built with existing VMware/ONTAP environments and extend it to Amazon EC2 + FSx for ONTAP for cloud-native operations, scalability, and cost optimization.

### Architecture

```text
[Source: On-Premises]                [Target: AWS]
VMware ESXi                          Amazon EC2 (Nitro)
  └── VM (VMDK)                        ├── Boot: EBS gp3
       └── on ONTAP NFS                └── Data: FSx for ONTAP (iSCSI LUN)

Path A: NetApp Shift Toolkit (Early Preview)
┌────────────────────────────────────────────────────────┐
│ 1. FlexClone VMDK → iSCSI LUN conversion (seconds)     │
│ 2. SnapMirror: on-prem ONTAP → FSx for ONTAP           │
│ 3. OS disk → EBS snapshot → AMI                        │
│ 4. EC2 launch + FSx for ONTAP iSCSI attach             │
└────────────────────────────────────────────────────────┘

Path B: AWS Transform (Public Preview)
┌────────────────────────────────────────────────────────┐
│ 1. Discovery (RVTools / OVA / NetApp DII)              │
│ 2. AI-based wave planning                              │
│ 3. MGN replication (continuous sync)                   │
│ 4. Cutover: OS → EBS / Data → FSx for ONTAP            │
└────────────────────────────────────────────────────────┘
```

### Value for Three Audiences

| Perspective | Value |
|-------------|-------|
| **AWS Users** | New VMware → EC2 migration path. FSx for ONTAP thin provisioning / dedup / compression for cost optimization |
| **NetApp Users** | Continue ONTAP operational model (Snapshot, FlexClone, SnapMirror, Storage Efficiency) on AWS |
| **VMware Users** | Expanded migration destinations. Phased migration possible with non-destructive source VMs |

### Tool Selection Guide

| Condition | Recommended Tool |
|-----------|-----------------|
| No ONTAP or EBS-only sufficient | AWS MGN |
| ONTAP in use + FSx for ONTAP data placement + small/mid-scale | **Shift Toolkit** (Early Preview) |
| ONTAP in use + large scale (100+ VMs) + near-zero downtime | Cirrus Migrate Cloud (CMC) |
| AWS-native end-to-end (plan → compute → storage) / mixed sources | **AWS Transform** (VMware migration free; FSx for ONTAP destination Public Preview) |
| Migration planning & sizing only | BlueXP Migration Advisor | <!-- allow:naming -->

## Verification Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 0 | Research & planning | ✅ Complete |
| Phase 1 | AWS environment setup (VPC, FSx for ONTAP, EC2) | 📋 Planned |
| Phase 2a | AWS Transform verification (Discovery → Plan → Migrate) | 📋 Spec ready |
| Phase 2b | Shift Toolkit verification (FlexClone conversion → EC2 launch) | ⏳ Awaiting NetApp Q&A |
| Phase 3 | Validation & benchmarking (performance / cost / ONTAP features) | ⏳ Not started |
| Phase 4 | Documentation & blog articles | ⏳ Not started |

## Success Criteria

| Metric | Target |
|--------|--------|
| Data disk conversion time | Under 5 min per 100GB (FlexClone) |
| Cutover downtime | Under 30 min (small VMs) |
| Data integrity | 100% (sha256sum match) |
| FSx for ONTAP iSCSI performance | Baseline comparison report |
| Cost comparison | EBS-only vs EBS + FSx for ONTAP hybrid |

## Directory Structure

```text
docs/
  ├── ja/                Japanese documentation
  │   ├── research.md    Research report
  │   └── aws-transform-migration-procedure.md
  ├── en/                English documentation
  │   └── research-summary.md
  └── images/            Architecture diagrams
scripts/                 Automation scripts (Python 3.12 / Bash)
templates/               CloudFormation templates
  └── poc-environment.yaml
verification/
  ├── evidence/          Verification evidence (YAML)
  └── screenshots/       Screenshots (masked)
```

## Quick Start

```bash
# Clone repository
git clone https://github.com/Yoshiki0705/vmware-migration-ec2-ontap.git
cd vmware-migration-ec2-ontap

# Set up git hooks
git config core.hooksPath .githooks

# Install Python dependencies
pip install -r requirements.txt

# Deploy PoC environment (Phase 1 — VPC + FSx for ONTAP)
aws cloudformation deploy \
  --template-file templates/poc-environment.yaml \
  --stack-name vmware-migration-poc \
  --parameter-overrides \
    VpcCidr=10.0.0.0/16 \
    FsxnThroughput=512 \
    FsxnStorageCapacity=1024 \
  --capabilities CAPABILITY_IAM
```

## Prerequisites

### On-Premises

- VMware vCenter 7.0.3+ (ESXi hosts + NFS datastore)
- ONTAP 9.14.1+
- NetApp Shift Toolkit (installed on Windows Server — for Shift Toolkit verification)
- NetApp Support account (for Early Preview enablement)

### AWS

- AWS account with appropriate IAM permissions
- AWS Organizations + IAM Identity Center (required for AWS Transform)
- VPN or Direct Connect (on-prem ↔ AWS connectivity)
- Tokyo Region (ap-northeast-1) recommended

## Disclaimer

> ⚠️ **Preview Status (as of 2026-06)**:
>
> - **Shift Toolkit**: VMware ESXi → AWS EC2 support is **Early Preview**.
>   OS disk → EBS + Data disk → FSx for ONTAP configuration. Requires enablement by NetApp.
> - **AWS Transform**: FSx for ONTAP as migration destination is **Public Preview**.
>   VMware migration agent is free. Supported regions, UI, and constraints may change.
>
> Specifications, constraints, and support scope may change for both tools. Do not treat as GA.

## References

### NetApp

> ⚠️ `docs.netapp.com` / `community.netapp.com` may intermittently return 403.
> If blocked, retry later or sign in to [NetApp Support Site](https://mysupport.netapp.com/).

- [NetApp Shift Toolkit (MySupport — login required)](https://mysupport.netapp.com/site/tools/tool-eula/netapp-shift-toolkit)
- [Migrate VMware to EC2 & iSCSI-based FSx for ONTAP (NetApp Blog)](https://www.netapp.com/blog/aws-fsxn-blg-migrate-vmware-to-amazon-ec2-iscsi-based-fsx-for-ontap/)
- [Simplify VM migration with Shift Toolkit (NetApp Blog)](https://www.netapp.com/blog/simplify-vm-migration-shift-toolkit/)

### AWS

- [AWS Transform: VMware to FSx for ONTAP (What's New)](https://aws.amazon.com/jp/about-aws/whats-new/2026/06/aws-transform-vmware-fsx-for-ontap-preview/)
- [Accelerating VMware migration: AWS Transform](https://aws.amazon.com/blogs/migration-and-modernization/accelerating-vmware-migration-aws-transforms-new-experience/)
- [AWS Storage Blog: Seamless VMware Migration](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)
- [AWS Transform Pricing](https://aws.amazon.com/transform/pricing/)

## License

MIT
