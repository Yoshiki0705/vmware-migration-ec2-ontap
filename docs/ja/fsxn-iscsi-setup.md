# FSx for ONTAP iSCSI 接続手順書（EC2 Linux → FSxN Multipath）

**目的**: EC2 インスタンスから FSx for ONTAP の iSCSI LUN にマルチパスで接続する手順。
移行後のデータディスク接続で使用する。

> 参考: [AWS 公式: Provisioning iSCSI for Linux](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/mount-iscsi-luns-linux.html)

---

## 前提条件

- FSx for ONTAP ファイルシステムが作成済み
- SVM (Storage Virtual Machine) が作成済み
- EC2 インスタンスが FSxN と同一 VPC 内（または VPC ピアリング済み）
- Security Group で iSCSI (TCP 3260) が許可済み
- `fsxadmin` 認証情報を保有

---

## Step 1: EC2 に iSCSI + Multipath パッケージをインストール

```bash
# Amazon Linux 2023 / Amazon Linux 2
sudo yum install -y iscsi-initiator-utils device-mapper-multipath

# Ubuntu 22.04/24.04
# sudo apt install -y open-iscsi multipath-tools
```

## Step 2: Multipath を有効化

```bash
# multipath デーモン設定を有効化
sudo mpathconf --enable --with_multipathd y

# multipath.conf の推奨設定（FSxN 向け）
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

# multipathd 再起動
sudo systemctl restart multipathd
sudo systemctl enable multipathd
```

## Step 3: iSCSI 設定の最適化

```bash
# replacement_timeout を 5 秒に設定（フェイルオーバー高速化）
sudo sed -i 's/node.session.timeo.replacement_timeout = .*/node.session.timeo.replacement_timeout = 5/' /etc/iscsi/iscsid.conf

# iSCSI サービス起動
sudo systemctl start iscsid
sudo systemctl enable iscsid

# Initiator 名の確認（後で igroup に登録する）
cat /etc/iscsi/initiatorname.iscsi
# 出力例: InitiatorName=iqn.1994-05.com.redhat:ec2-instance-01
```

## Step 4: FSxN 側で LUN + igroup を構成

FSxN の管理エンドポイントに SSH 接続して ONTAP CLI で設定:

```bash
# FSxN 管理エンドポイントに接続
ssh fsxadmin@<management-endpoint-ip>
```

```
# SVM 上にボリューム作成（データディスク用）
FsxId0123456789abcdef::> volume create -vserver svm1 -volume data_vol01 \
  -aggregate aggr1 -size 100g -state online -type RW \
  -space-guarantee none -percent-snapshot-space 5

# LUN 作成
FsxId0123456789abcdef::> lun create -vserver svm1 \
  -path /vol/data_vol01/lun01 -size 100g -ostype linux

# igroup 作成（EC2 の initiator 名を指定）
FsxId0123456789abcdef::> lun igroup create -vserver svm1 \
  -igroup ec2-linux-ig -initiator iqn.1994-05.com.redhat:ec2-instance-01 \
  -protocol iscsi -ostype linux

# LUN を igroup にマッピング
FsxId0123456789abcdef::> lun mapping create -vserver svm1 \
  -path /vol/data_vol01/lun01 -igroup ec2-linux-ig -lun-id 0

# iSCSI LIF の IP アドレスを確認
FsxId0123456789abcdef::> network interface show -vserver svm1 -data-protocol iscsi
# preferred subnet と standby subnet の 2 つの IP が表示される
```

## Step 5: EC2 からターゲットを検出・接続

```bash
# ターゲットの検出（preferred LIF）
sudo iscsiadm -m discovery -t sendtargets -p <iscsi-lif-ip-preferred>:3260

# ターゲットの検出（standby LIF - Multi-AZ の場合）
sudo iscsiadm -m discovery -t sendtargets -p <iscsi-lif-ip-standby>:3260

# 全ターゲットにログイン
sudo iscsiadm -m node --login

# セッション確認
sudo iscsiadm -m session
# 出力例:
# tcp: [1] 10.0.1.x:3260,1 iqn.1992-08.com.netapp:sn.xxxxx (non-flash)
# tcp: [2] 10.0.2.x:3260,1 iqn.1992-08.com.netapp:sn.xxxxx (non-flash)
```

## Step 6: Multipath の確認

```bash
# マルチパスデバイスの確認
sudo multipath -ll

# 出力例（正常時: 2パスともアクティブ）:
# 3600a0980xxxxx dm-0 NETAPP,LUN C-Mode
# size=100G features='3 queue_if_no_path pg_init_retries 50' hwhandler='0' wp=rw
# |-+- policy='service-time 0' prio=50 status=active
# | `- 1:0:0:0 sda 8:0  active ready running
# `-+- policy='service-time 0' prio=10 status=enabled
#   `- 2:0:0:0 sdb 8:16 active ready running
```

**確認すべきポイント:**
- `status=active` のパスが少なくとも1つあること
- Multi-AZ の場合、preferred path が `prio=50`、standby が `prio=10`
- `features` に `queue_if_no_path` があること（フェイルオーバー時に I/O をキューイング）

## Step 7: ファイルシステム作成とマウント

```bash
# マルチパスデバイスにファイルシステムを作成（初回のみ）
sudo mkfs.xfs /dev/mapper/3600a0980xxxxx

# マウントポイント作成
sudo mkdir -p /mnt/data

# マウント
sudo mount /dev/mapper/3600a0980xxxxx /mnt/data

# 確認
df -h /mnt/data
lsblk

# /etc/fstab に永続マウント追加（_netdev オプション必須）
echo "/dev/mapper/3600a0980xxxxx /mnt/data xfs defaults,_netdev,nofail 0 0" | sudo tee -a /etc/fstab
```

**重要**: `_netdev` オプションは必須。これによりネットワーク（iSCSI）が利用可能になってからマウントする。

---

## Multi-AZ フェイルオーバーの動作確認

```bash
# 現在のアクティブパスを確認
sudo multipath -ll | grep -A2 "status="

# フェイルオーバーテスト（FSxN Console からファイルオーバーをトリガー）
# → multipathd が自動的に standby パスに切り替え
# → I/O が一時的にキューイングされ、数秒以内に再開

# フェイルオーバー後の確認
sudo multipath -ll
# standby だったパスが active に昇格していることを確認
```

---

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `iscsiadm: No portals found` | Security Group で 3260 が閉じている | SG に TCP 3260 のインバウンドルールを追加 |
| `multipath -ll` で何も表示されない | LUN がマップされていない | ONTAP CLI で `lun mapping show` を確認 |
| パスが1つしか表示されない | standby LIF への discovery 未実施 | 両方の LIF IP で `sendtargets` を実行 |
| I/O エラー | replacement_timeout がデフォルト(120s)のまま | `/etc/iscsi/iscsid.conf` で 5 に変更し再起動 |
| ブート時にマウント失敗 | `_netdev` オプションが未設定 | `/etc/fstab` に `_netdev,nofail` を追加 |

---

*本手順は FSx for ONTAP 公式ドキュメント（2026年6月時点）に基づいています。*
