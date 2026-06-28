# Sorting Out VMware Migration Options — Why EC2 + FSx for ONTAP

<!-- dev.to front matter
---
title: "Sorting Out VMware Migration Options — Why EC2 + FSx for ONTAP"
published: false
description: "Comparing VMware-to-AWS migration tools and explaining why the EC2 + FSx for ONTAP combination makes sense"
tags: aws, vmware, netapp, migration
series: "NetApp Shift Toolkit × VMware to EC2 / FSx for ONTAP"
---
-->

## Introduction

Over the past year or two, there has been a rapid increase in organizations reconsidering the "next step" for their VMware workloads.

Triggered by the licensing changes following Broadcom's acquisition of VMware, many organizations are rethinking their virtualization strategies. The AWS Storage Blog also presents this shift not merely as license avoidance, but as an infrastructure modernization opportunity that leverages the cost efficiency, flexibility, and reliability of the cloud. [(Reference)](https://aws.amazon.com/blogs/storage/expedite-vmware-migration-to-amazon-ec2-and-amazon-fsx-for-netapp-ontap-using-bluexp-workload-factory-for-aws-migration-advisor/)

From my perspective working with Amazon FSx for NetApp ONTAP, I feel that **continuity of the storage operations model** is often overlooked in these migrations.

"Getting off VMware" is not the goal in itself. The real goal is to carry forward the storage operations cultivated in VMware / ONTAP environments — Snapshot, Clone, Replication, Storage Efficiency — into AWS while connecting to cloud-native scalability.

## Sorting Out Migration Destinations

AWS officially presents five pathways for VMware workload migration. [(Reference: AWS for VMware — Comprehensive Pathways)](https://aws.amazon.com/vmware/explore/)

### AWS Official VMware Pathways Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│              VMware Workload AWS Pathways                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Migrate to Amazon EC2 (Rehost)                                  │
│     └─ VMware VM → EC2 instance                                     │
│        Tools: AWS Transform, MGN, CMC, Shift Toolkit               │
│                                                                     │
│  2. Modernize on AWS (Modernization)                                │
│     └─ Containerization / Serverless                                │
│        → Amazon ECS / EKS (EC2 mode / Fargate)                     │
│        → AWS Lambda / AWS Batch                                     │
│        → Amazon WorkSpaces (VDI)                                    │
│                                                                     │
│  3. Run VMware on AWS (VMware Continuity)                           │
│     └─ Amazon Elastic VMware Service (EVS)                          │
│        Leverage existing vSphere skills and tools                   │
│                                                                     │
│  4. Run AWS on-premises (On-prem AWS)                               │
│     └─ AWS Outposts                                                 │
│                                                                     │
│  5. Run third-party hypervisors on AWS (Partner Solutions)          │
│     └─ Red Hat OpenShift Service on AWS (ROSA)                      │
│     └─ Nutanix Cloud Clusters on AWS (NC2)                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

> Source: [AWS for VMware Partner Offerings](https://aws.amazon.com/vmware/partner-offerings/)
> — "AWS offers the most comprehensive set of migration and modernization options for
> VMware-based workloads - from relocating to Amazon EVS, to rehosting on Amazon EC2,
> containerizing with Amazon EKS, or transitioning to running third-party hypervisors
> in the cloud like ROSA and NC2 on AWS." (Summarized; rephrased for licensing constraints.)

### Pathway Details

#### 1. Rehost to Amazon EC2

The most straightforward path: migrating VMware VMs as EC2 instances. AWS Transform for VMware (an Agentic AI-based automated migration service) went GA in 2025, advancing automation for large-scale migrations.

**Storage configuration options:**

- **EBS only**: Simple. Automated via MGN / AWS Transform
- **EBS (OS) + FSx for ONTAP (Data)**: Continuity of ONTAP features. Addressed by Shift Toolkit / CMC ← **Scope of this validation**

#### 2. Modernization (Containers / Serverless)

After rehosting to EC2, further modernization is possible depending on workload characteristics.

| Target | Suitable Workloads | FSx for ONTAP Integration |
|-----------|------------------|-----------|
| **ECS / EKS (EC2 mode)** | Stateful containers (DB, middleware) | ✅ iSCSI / NFS mount available |
| **ECS / EKS (Fargate)** | Stateless microservices | △ EFS only (no iSCSI) |
| **AWS Lambda** | Event-driven, short-duration processing | △ EFS mount available, no iSCSI |
| **AWS Batch** | Batch processing / HPC | ✅ iSCSI available in EC2 mode |
| **Amazon WorkSpaces** | VDI (virtual desktops) | ✅ FSx for ONTAP file shares |

**Important**: This does not mean containerizing VMs directly. The journey is EC2 rehost → application containerization → gradual migration to Fargate/Lambda.

#### 3. Amazon EVS (Continue VMware on AWS)

Amazon Elastic VMware Service lets you deploy VMware Cloud Foundation (VCF) directly on EC2 bare metal within a VPC. You can leverage your existing vSphere skill set as-is, with the option to connect FSx for ONTAP as an external datastore.

**Suitable for:** Organizations with a large VMware-dependent application estate where a short-term exit from VMware is impractical.

#### 4. AWS Outposts (On-prem AWS + NetApp External Storage)

AWS Outposts is a fully managed service that places AWS infrastructure on-premises.
In December 2024, AWS announced third-party block storage integration for Outposts, making **NetApp ONTAP and StorageGRID available as storage partners validated through the AWS Service Ready Program**.
[(Reference: AWS Blog)](https://aws.amazon.com/blogs/compute/new-simplifying-the-use-of-third-party-block-storage-with-aws-outposts/) [(Reference: NetApp)](https://netapp.com/aws/outposts/)

NetApp ONTAP iSCSI LUNs can be attached directly from the AWS console as data volumes for EC2 instances, and boot volume support was added in July 2025. [(Reference: AWS Blog)](https://aws.amazon.com/blogs/compute/deploying-external-boot-volumes-with-aws-outposts/)

**NetApp ecosystem perspective**: The Outposts + ONTAP combination enables **separation of compute and storage** — "compute is AWS-managed, storage is existing ONTAP." This makes it possible to build a consistent data platform spanning on-premises ONTAP → FSx for ONTAP (cloud) → Outposts + ONTAP (hybrid).

#### 5. Partner Solutions (ROSA / NC2 + Expanding NetApp Integration)

**Red Hat OpenShift Service on AWS (ROSA):** A fully managed application platform based on OpenShift. It provides a migration path from VMs to OpenShift as a runtime for containerized workloads. The NetApp Trident CSI driver enables ROSA Pods to access FSx for ONTAP via NFS/iSCSI. [(Reference)](https://aws.amazon.com/rosa/)

**Nutanix Cloud Clusters on AWS (NC2) + NetApp ONTAP:**

In April 2026, Nutanix and NetApp announced a strategic partnership, revealing that **NetApp ONTAP will be integrated as external storage for the Nutanix Cloud Platform**. NFS-based connectivity enables independent scaling of compute (Nutanix AHV) and storage (ONTAP). [(Reference: NetApp Blog)](https://www.netapp.com/blog/modernize-virtualization-nutanix-partnership/) [(Reference: NetApp Press Release)](https://www.netapp.com/newsroom/press-releases/news-rel-20260407-695711/)

Nutanix CEO Rajiv Ramaswami stated that "support for external storage platforms simplifies the migration to Nutanix without significant hardware changes." (Reported as comments from the Q1 FY2027 Earnings Call)

**The NetApp ecosystem as a whole:**

```text
┌─────────────────────────────────────────────────────────────┐
│          NetApp ONTAP — Data Portability & Consistency       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  On-premises                 AWS                            │
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
│  Common: Snapshot / FlexClone / SnapMirror / Efficiency     │
│  Common: NFS / SMB / iSCSI / S3 Multi-protocol             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

What this diagram illustrates is that **ONTAP is a data platform independent of hypervisor or cloud choice**. Whether you move compute from VMware to EC2, Nutanix, or ROSA, the ONTAP data layer remains consistently available, with SnapMirror enabling data movement and protection.

The Shift Toolkit-based VMware → EC2/FSx for ONTAP migration is **one migration path** within this ecosystem. If workload relocation to NC2 + ONTAP or ROSA + FSx for ONTAP becomes necessary in the future, data layer compatibility is preserved.

### Positioning of This Validation

```text
VMware ESXi (Current State)
    │
    ├─ Phase 1: Rehost ← Scope of this validation
    │   EC2 + FSx for ONTAP (iSCSI)
    │   Data disk conversion via Shift Toolkit
    │
    ├─ Phase 2: Replatform (Future)
    │   Containerize applications on EC2
    │   → ECS/EKS + FSx for ONTAP (NFS/iSCSI)
    │
    └─ Phase 3: Refactor (Future)
        Stateless transformation → Fargate / Lambda
        Data layer separated to FSx for ONTAP / S3 / DynamoDB
```

This validation focuses on **Phase 1 (Rehost)**, but the EC2 + FSx for ONTAP architecture is designed not to close off the migration path to Phase 2 and beyond. Since FSx for ONTAP is accessible via NFS/iSCSI not only from EC2 but also from ECS/EKS, the data layer can be maintained as-is even after containerization.

## Why "EC2 + FSx for ONTAP"

Here is why we focus on "EC2 + FSx for ONTAP" among the five pathways.

### An entry point for rehosting and a foundation for modernization

The EC2 + FSx for ONTAP architecture is not just a rehost destination — it is **a design that does not close off future modernization**.

- **Now (Phase 1)**: Rehost VMs to EC2. Data disks on FSx for ONTAP iSCSI
- **Next (Phase 2)**: Containerize applications. Continue NFS/iSCSI access from ECS/EKS to FSx for ONTAP
- **Future (Phase 3)**: Stateless components move to Fargate/Lambda. FSx for ONTAP data layer stays intact

The multi-protocol access (NFS/SMB/iSCSI) capability of FSx for ONTAP underpins this phased migration. A volume used as an iSCSI LUN for EC2 can later be NFS-mounted by an EKS Pod.

### The value of ONTAP is "capability," not "capacity"

If you view FSx for ONTAP simply as "high-capacity storage," it may appear expensive compared to EBS. However, the essential value of ONTAP is not capacity.

| ONTAP Feature | Application on AWS |
|-----------|------------|
| **Snapshot** | Point-in-time copies in seconds. Instant test environment creation |
| **FlexClone** | Clones without data copying. Cost reduction for dev/test |
| **SnapMirror** | Block-level replication. Cross-region DR |
| **Compression / Dedup** | Effective capacity reduction. Especially impactful for databases and logs |
| **Thin Provisioning** | Pay only for used capacity. Avoid over-provisioning |
| **Multi-protocol** | Access the same volume via NFS/SMB/iSCSI |

### FSx for ONTAP EC2 Integration Pattern

```text
┌──────────────────────────────────┐
│      Amazon EC2 (Nitro)       │
│  ┌─────────┐  ┌───────────┐  │
│  │ OS: EBS │  │ Data: iSCSI│ │
│  │  (gp3)  │  │  (FSx for ONTAP)   │  │
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

Benefits of this architecture:

- **Bypass EC2 VM-level I/O limits**: FSx for ONTAP is constrained only by network bandwidth. High IOPS achievable even on small instances
- **Independent scaling of storage and compute**: Modify FSx for ONTAP capacity/throughput without stopping EC2
- **Continuity of the ONTAP operations model**: Manage snapshots, clones, and replication with the same CLI/API as on-premises

## Choosing a Migration Tool

Even when migrating to "EC2 + FSx for ONTAP," the right tool depends on your environment.

| Condition | Recommended Tool | Characteristics |
|------|----------|------|
| Using ONTAP NFS datastore + small/medium scale | **NetApp Shift Toolkit** | Disk conversion in seconds via FlexClone. Free |
| Using ONTAP + large scale (100+ VMs) | **Cirrus Migrate Cloud** | YAML automation, near-zero downtime migration |
| Not using ONTAP or EBS only | **AWS MGN** | AWS standard. Broad OS support. Free |
| Migration planning / sizing only | **BlueXP Migration Advisor** | RVTools integration, cost comparison, IaC output | <!-- allow:naming -->

### Positioning of NetApp Shift Toolkit

Shift Toolkit is the fastest tool for ONTAP users migrating VMs from existing NFS datastores. By leveraging FlexClone, it converts disks without data copying, converting a 1TB VMDK in seconds to minutes.

Currently, migrations from VMware ESXi to Hyper-V, OpenShift Virtualization, Proxmox VE, and OLVM are GA. **VMware ESXi → Amazon EC2 / FSx for ONTAP support is in Early Preview**.

> ⚠️ Early Preview note: At this time, the scope covers configurations where data disks are placed on FSx for ONTAP. Specifications and constraints may change.

## What This Series Validates

This series uses the Shift Toolkit Early Preview to validate the following:

1. **Environment setup**: VPC + FSx for ONTAP + VPN design and deployment
2. **Migration execution**: Migrating Linux / Windows VMs to EC2
3. **Performance**: Measured IOPS / throughput of FSx for ONTAP iSCSI
4. **Operational continuity**: Post-migration Snapshot / Clone / SnapMirror verification
5. **Cost comparison**: TCO comparison with an EBS-only configuration

## Summary

- VMware migration is not just about "where to go" but "how to maintain the storage operations model"
- For ONTAP users, FSx for ONTAP is the option to continue ONTAP's value on AWS
- Choose tools based on your environment and scale. For ONTAP + small/medium scale, Shift Toolkit is a strong candidate
- Since this is at Early Preview stage, validation results may change at GA

The next article dives into the mechanics of Shift Toolkit itself — how FlexClone transforms VM migration.

---

## Reference Links

- [AWS for VMware — Comprehensive Pathways](https://aws.amazon.com/vmware/explore/)
- [AWS Transform for VMware](https://aws.amazon.com/transform/vmware/)
- [AWS for VMware Partner Offerings (ROSA, NC2)](https://aws.amazon.com/vmware/partner-offerings/)
- [NetApp Shift Toolkit Overview](https://docs.netapp.com/us-en/netapp-solutions-virtualization/migration/shift-toolkit-overview.html)
- [AWS Storage Blog: Seamless migration from VMware to FSx for ONTAP and EC2](https://aws.amazon.com/blogs/storage/seamless-migration-from-any-vmware-environment-to-amazon-fsx-for-netapp-ontap-and-amazon-ec2/)
- [AWS Storage Blog: BlueXP Migration Advisor](https://aws.amazon.com/blogs/storage/expedite-vmware-migration-to-amazon-ec2-and-amazon-fsx-for-netapp-ontap-using-bluexp-workload-factory-for-aws-migration-advisor/) <!-- allow:naming -->
- [Amazon FSx for NetApp ONTAP](https://aws.amazon.com/fsx/netapp-ontap/)
- [Amazon Elastic VMware Service (EVS)](https://aws.amazon.com/evs/)
- [Red Hat OpenShift Service on AWS (ROSA)](https://aws.amazon.com/rosa/)
- [Nutanix Cloud Clusters on AWS (NC2)](https://aws.amazon.com/blogs/apn/accelerate-vmware-migrations-to-aws-with-nutanix-nc2/)
- [AWS VMware Migration Accelerator](https://aws.amazon.com/vmware/migrationaccelerator/)
- [NetApp Blog: Simplify VM migration with Shift Toolkit](https://www.netapp.com/blog/simplify-vm-migration-shift-toolkit/)

---

*This article is part 1 of the NetApp Shift Toolkit Early Preview validation series. Early Preview specifications are subject to change.*
