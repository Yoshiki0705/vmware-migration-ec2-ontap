# FSx for ONTAP iSCSI Setup Guide (EC2 Linux → FSx for ONTAP Multipath)

**Purpose**: Procedure for connecting an EC2 instance to an FSx for ONTAP iSCSI LUN using multipath.
Used for data disk connectivity after migration.

> Reference: [AWS Official: Provisioning iSCSI for Linux](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/mount-iscsi-luns-linux.html)

---

## Prerequisites

- Amazon FSx for NetApp ONTAP file system is created
- SVM (Storage Virtual Machine) is created
- EC2 instance is in the same VPC as FSx for ONTAP (or VPC peering is configured)
- Security Group allows iSCSI (TCP 3260)
- `fsxadmin` credentials are available

---

## Step 1: Install iSCSI + Multipath Packages on EC2

```bash
# Amazon Linux 2023 / Amazon Linux 2
sudo yum install -y iscsi-initiator-utils device-mapper-multipath

# Ubuntu 22.04/24.04
# sudo apt install -y open-iscsi multipath-tools
```

## Step 2: Enable Multipath

```bash
# Enable multipath daemon configuration
sudo mpathconf --enable --with_multipathd y

# Recommended multipath.conf settings (for FSx for ONTAP)
sudo tee /etc/multipath.conf << 'EOF'
defaults {
    user_friendly_names yes
    find_multipaths yes
}

devices {
    device {
        vendor              "NETAPP"
        product             "LUN.*"
        path_grouping_policy group_by_prio
        path_selector       "service-time 0"
        path_checker        tur
        features            "3 queue_if_no_path pg_init_retries 50"
        prio                ontap
        failback            immediate
        no_path_retry       queue
    }
}
EOF

# Restart multipathd
sudo systemctl restart multipathd
sudo systemctl enable multipathd
```

## Step 3: Optimize iSCSI Settings

```bash
# Set replacement_timeout to 5 seconds (faster failover)
sudo sed -i 's/node.session.timeo.replacement_timeout = .*/node.session.timeo.replacement_timeout = 5/' /etc/iscsi/iscsid.conf

# Start iSCSI service
sudo systemctl start iscsid
sudo systemctl enable iscsid

# Check Initiator name (to be registered in igroup later)
cat /etc/iscsi/initiatorname.iscsi
# Example output: InitiatorName=iqn.1994-05.com.redhat:ec2-instance-01
```

## Step 4: Configure LUN + igroup on FSx for ONTAP

SSH to the FSx for ONTAP management endpoint and configure using the ONTAP CLI:

```bash
# Connect to FSx for ONTAP management endpoint
ssh fsxadmin@<management-endpoint-ip>
```

```text
# Create a volume on the SVM (for data disk)
FsxId0123456789abcdef::> volume create -vserver svm1 -volume data_vol01 \
  -aggregate aggr1 -size 100g -state online -type RW \
  -space-guarantee none -percent-snapshot-space 5

# Create a LUN
FsxId0123456789abcdef::> lun create -vserver svm1 \
  -path /vol/data_vol01/lun01 -size 100g -ostype linux

# Create an igroup (specify the EC2 initiator name)
FsxId0123456789abcdef::> lun igroup create -vserver svm1 \
  -igroup ec2-linux-ig -initiator iqn.1994-05.com.redhat:ec2-instance-01 \
  -protocol iscsi -ostype linux

# Map the LUN to the igroup
FsxId0123456789abcdef::> lun mapping create -vserver svm1 \
  -path /vol/data_vol01/lun01 -igroup ec2-linux-ig -lun-id 0

# Check iSCSI LIF IP addresses
FsxId0123456789abcdef::> network interface show -vserver svm1 -data-protocol iscsi
# Two IPs are displayed: preferred subnet and standby subnet
```

## Step 5: Discover and Connect Targets from EC2

```bash
# Discover targets (preferred LIF)
sudo iscsiadm -m discovery -t sendtargets -p <iscsi-lif-ip-preferred>:3260

# Discover targets (standby LIF - for Multi-AZ)
sudo iscsiadm -m discovery -t sendtargets -p <iscsi-lif-ip-standby>:3260

# Log in to all targets
sudo iscsiadm -m node --login

# Verify sessions
sudo iscsiadm -m session
# Example output:
# tcp: [1] 10.0.1.x:3260,1 iqn.1992-08.com.netapp:sn.xxxxx (non-flash)
# tcp: [2] 10.0.2.x:3260,1 iqn.1992-08.com.netapp:sn.xxxxx (non-flash)
```

## Step 6: Verify Multipath

```bash
# Check multipath devices
sudo multipath -ll

# Example output (normal: both paths active):
# 3600a0980xxxxx dm-0 NETAPP,LUN C-Mode
# size=100G features='3 queue_if_no_path pg_init_retries 50' hwhandler='0' wp=rw
# |-+- policy='service-time 0' prio=50 status=active
# | `- 1:0:0:0 sda 8:0  active ready running
# `-+- policy='service-time 0' prio=10 status=enabled
#   `- 2:0:0:0 sdb 8:16 active ready running
```

**Key points to verify:**

- At least one path has `status=active`
- For Multi-AZ, the preferred path has `prio=50` and the standby has `prio=10`
- `features` contains `queue_if_no_path` (queues I/O during failover)

## Step 7: Create File System and Mount

```bash
# Create a file system on the multipath device (first time only)
sudo mkfs.xfs /dev/mapper/3600a0980xxxxx

# Create mount point
sudo mkdir -p /mnt/data

# Mount
sudo mount /dev/mapper/3600a0980xxxxx /mnt/data

# Verify
df -h /mnt/data
lsblk

# Add persistent mount to /etc/fstab (_netdev option is required)
echo "/dev/mapper/3600a0980xxxxx /mnt/data xfs defaults,_netdev,nofail 0 0" | sudo tee -a /etc/fstab
```

**Important**: The `_netdev` option is required. This ensures the mount occurs only after the network (iSCSI) is available.

---

## Multi-AZ Failover Verification

```bash
# Check current active paths
sudo multipath -ll | grep -A2 "status="

# Failover test (trigger failover from the FSx for ONTAP console)
# → multipathd automatically switches to the standby path
# → I/O is temporarily queued and resumes within seconds

# Verify after failover
sudo multipath -ll
# Confirm that the former standby path has been promoted to active
```

---

## Troubleshooting

| Symptom | Cause | Resolution |
|---------|-------|------------|
| `iscsiadm: No portals found` | Port 3260 is blocked in Security Group | Add TCP 3260 inbound rule to the SG |
| `multipath -ll` shows nothing | LUN is not mapped | Verify with `lun mapping show` in ONTAP CLI |
| Only one path is displayed | Discovery not performed for standby LIF | Run `sendtargets` for both LIF IPs |
| I/O errors | replacement_timeout is at default (120s) | Change to 5 in `/etc/iscsi/iscsid.conf` and restart |
| Mount fails at boot | `_netdev` option is not set | Add `_netdev,nofail` to `/etc/fstab` |

---

*This procedure is based on the FSx for ONTAP official documentation (as of June 2026).*
