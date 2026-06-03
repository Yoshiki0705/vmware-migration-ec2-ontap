# NetApp Shift Toolkit — VMware ESXi to EC2 / FSx for ONTAP: Research Summary

**Date**: 2026-06-03
**Status**: Research phase (pre-verification)

---

## Executive Summary

This project verifies the NetApp Shift Toolkit Early Preview for migrating VMware ESXi workloads to Amazon EC2 with data disks on Amazon FSx for NetApp ONTAP.

The verification focuses not just on "migrating from VMware to AWS" but on confirming whether existing ONTAP operational models (Snapshot, FlexClone, SnapMirror, Storage Efficiency) can be preserved while transitioning to cloud-native operations on EC2 + FSx for ONTAP.

> ⚠️ The VMware ESXi → AWS EC2 path is Early Preview. Currently targets data disk placement on FSx for ONTAP only. Specifications may change.

## Key Findings

### Shift Toolkit Capabilities (GA)
- GUI-based VM migration across hypervisors (ESXi, Hyper-V, OpenShift, OLVM, Proxmox)
- ONTAP FlexClone for disk conversion in seconds (1TB VMDK in seconds vs hours)
- Source VM non-destructive (script copy only, immediate rollback possible)
- Prerequisites: ONTAP 9.14.1+, NFS datastore, Windows-only tool
- Free from NetApp

### EC2 Early Preview (Under Investigation)
- **Confirmed scope**: Data disk placement on FSx for ONTAP
- **Open question (P0)**: OS disk boot method — whether Shift Toolkit handles AMI conversion or requires VM Import/Export / MGN / CMC for the OS disk
- **Requires**: NetApp-side enablement

### Tool Selection Guidance

| Condition | Recommended Tool |
|-----------|-----------------|
| No ONTAP or EBS-only | AWS MGN |
| ONTAP + FSxN data placement + small/mid-scale | Shift Toolkit (Early Preview) |
| ONTAP + large scale (100+ VMs) + near-zero downtime | Cirrus Migrate Cloud |
| Planning & sizing only | BlueXP Migration Advisor |

## Success Criteria

| Metric | Target |
|--------|--------|
| Data disk conversion | < 5 min per 100GB (10x faster than copy-based tools) |
| Cutover downtime | < 30 min (small VMs) |
| Data integrity | 100% sha256sum match |
| FSxN iSCSI performance | Baseline comparison with documented fio parameters |
| Cost comparison | EBS-only vs EBS + FSxN hybrid |

## Verification Phases

1. **Environment Setup** — VPC, FSxN (Multi-AZ), EC2, VPN/DX
2. **Migration Test** — Shift Toolkit execution, evidence collection
3. **Validation** — Performance benchmarks, ONTAP features, cost analysis
4. **Documentation** — Blog series, architecture diagrams, reusable templates

## References

- [Shift Toolkit Overview](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/shift-toolkit-overview.html)
- [Migrate VMs to Amazon EC2](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/migrate-vms-to-ec2-fsxn-overview.html)
- [AWS Storage Blog: Seamless VMware Migration](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [AWS Storage Blog: BlueXP Migration Advisor](https://aws.amazon.com/blogs/storage/expedite-vmware-migration-to-amazon-ec2-and-amazon-fsx-for-netapp-ontap-using-bluexp-workload-factory-for-aws-migration-advisor/)
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)

---

*Full research report (Japanese): [docs/ja/research.md](../ja/research.md)*
