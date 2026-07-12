#!/usr/bin/env bash
# demo-ad-join-svm.sh — Join FSx for ONTAP SVM to a self-managed Active Directory
#
# Usage:
#   ./scripts/demo-ad-join-svm.sh \
#     --filesystem-id fs-0123456789abcdef0 \
#     --svm-name svm-smb \
#     --domain corp.example.com \
#     --ou "OU=FSxONTAP,OU=Servers,DC=corp,DC=example,DC=com" \
#     --dns-ips 198.51.100.10,198.51.100.11 \
#     --netbios-name CORP \
#     --admin-user svc-fsx-adjoin
#
# Prerequisites:
#   - AWS CLI v2 configured with appropriate permissions
#   - FSx for ONTAP file system exists and is AVAILABLE
#   - On-premises AD is reachable from the VPC (Direct Connect / VPN / AD Connector)
#   - DNS forwarding is configured (Route 53 Resolver or DHCP Options)
#   - Service account with delegated OU permissions on the AD domain
#
# Reference:
#   https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/self-managed-AD.html
#
set -euo pipefail

# ==============================================================================
# Defaults and Constants
# ==============================================================================
SCRIPT_NAME="$(basename "$0")"
AWS_REGION="${AWS_REGION:-ap-northeast-1}"

# ==============================================================================
# Helper Functions
# ==============================================================================
usage() {
  cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Join an FSx for ONTAP SVM to a self-managed Active Directory domain.

Required:
  --filesystem-id ID    FSx for ONTAP file system ID (fs-xxxx)
  --svm-name NAME       SVM name to create or update with AD config
  --domain FQDN         AD domain FQDN (e.g., corp.example.com)
  --dns-ips IPs         Comma-separated DNS server IPs (e.g., 198.51.100.10,198.51.100.11)
  --admin-user USER     AD service account username with OU delegation

Optional:
  --ou DN               Organizational Unit DN for computer account placement
                        (default: CN=Computers,DC=<derived from domain>)
  --netbios-name NAME   NetBIOS domain name (default: first label of domain, uppercase)
  --file-system-admins  Comma-separated AD groups for ONTAP admin (default: "Domain Admins")
  --region REGION       AWS region (default: \$AWS_REGION or ap-northeast-1)
  --dry-run             Show the API call without executing
  -h, --help            Show this help

Examples:
  # Join with custom OU (preserves migration source OU structure)
  ${SCRIPT_NAME} \\
    --filesystem-id fs-0123456789abcdef0 \\
    --svm-name svm-smb \\
    --domain corp.example.com \\
    --ou "OU=FSxONTAP,OU=Servers,DC=corp,DC=example,DC=com" \\
    --dns-ips 198.51.100.10,198.51.100.11 \\
    --admin-user svc-fsx-adjoin

EOF
  exit "${1:-0}"
}

info()  { echo "  ℹ️  $*"; }
ok()    { echo "  ✅ $*"; }
warn()  { echo "  ⚠️  $*"; }
err()   { echo "  ❌ $*" >&2; }
die()   { err "$*"; exit 1; }

# ==============================================================================
# Argument Parsing
# ==============================================================================
FILESYSTEM_ID=""
SVM_NAME=""
AD_DOMAIN=""
AD_OU=""
DNS_IPS=""
NETBIOS_NAME=""
ADMIN_USER=""
FS_ADMIN_GROUPS="Domain Admins"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --filesystem-id)   FILESYSTEM_ID="$2"; shift 2 ;;
    --svm-name)        SVM_NAME="$2"; shift 2 ;;
    --domain)          AD_DOMAIN="$2"; shift 2 ;;
    --ou)              AD_OU="$2"; shift 2 ;;
    --dns-ips)         DNS_IPS="$2"; shift 2 ;;
    --netbios-name)    NETBIOS_NAME="$2"; shift 2 ;;
    --admin-user)      ADMIN_USER="$2"; shift 2 ;;
    --file-system-admins) FS_ADMIN_GROUPS="$2"; shift 2 ;;
    --region)          AWS_REGION="$2"; shift 2 ;;
    --dry-run)         DRY_RUN=true; shift ;;
    -h|--help)         usage 0 ;;
    *)                 die "Unknown option: $1" ;;
  esac
done

# ==============================================================================
# Validation
# ==============================================================================
echo "=== FSx for ONTAP SVM AD Join ==="
echo ""

[[ -z "$FILESYSTEM_ID" ]] && die "Missing required: --filesystem-id"
[[ -z "$SVM_NAME" ]]      && die "Missing required: --svm-name"
[[ -z "$AD_DOMAIN" ]]     && die "Missing required: --domain"
[[ -z "$DNS_IPS" ]]       && die "Missing required: --dns-ips"
[[ -z "$ADMIN_USER" ]]    && die "Missing required: --admin-user"

# Derive NetBIOS name from domain if not provided
if [[ -z "$NETBIOS_NAME" ]]; then
  NETBIOS_NAME=$(echo "$AD_DOMAIN" | cut -d. -f1 | tr '[:lower:]' '[:upper:]')
  info "Derived NetBIOS name: ${NETBIOS_NAME}"
fi

# Derive default OU from domain if not provided
if [[ -z "$AD_OU" ]]; then
  # Convert corp.example.com -> DC=corp,DC=example,DC=com
  DC_PATH=$(echo "$AD_DOMAIN" | sed 's/\./,DC=/g; s/^/DC=/')
  AD_OU="CN=Computers,${DC_PATH}"
  warn "No --ou specified. Using default: ${AD_OU}"
  warn "For VMware migration, specify the source OU to preserve SID history."
fi

# Prompt for password (never passed via CLI args)
echo ""
read -rsp "  🔑 Enter password for AD service account '${ADMIN_USER}@${AD_DOMAIN}': " AD_PASSWORD
echo ""
[[ -z "$AD_PASSWORD" ]] && die "Password cannot be empty"

# ==============================================================================
# Pre-flight Checks
# ==============================================================================
echo ""
echo "[1/4] Pre-flight checks"

# Verify AWS CLI
if ! command -v aws &>/dev/null; then
  die "AWS CLI not found. Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi
ok "AWS CLI available"

# Verify credentials
CALLER_ID=$(aws sts get-caller-identity --region "$AWS_REGION" --output text --query 'Account' 2>/dev/null) \
  || die "AWS credentials not configured or expired"
ok "AWS account: ${CALLER_ID}"

# Verify file system exists and is available
FS_STATUS=$(aws fsx describe-file-systems \
  --file-system-ids "$FILESYSTEM_ID" \
  --region "$AWS_REGION" \
  --query 'FileSystems[0].Lifecycle' \
  --output text 2>/dev/null) \
  || die "File system ${FILESYSTEM_ID} not found in ${AWS_REGION}"

if [[ "$FS_STATUS" != "AVAILABLE" ]]; then
  die "File system ${FILESYSTEM_ID} is in state '${FS_STATUS}' (must be AVAILABLE)"
fi
ok "File system ${FILESYSTEM_ID} is AVAILABLE"

# ==============================================================================
# Check if SVM already exists
# ==============================================================================
echo ""
echo "[2/4] SVM lookup"

SVM_ID=$(aws fsx describe-storage-virtual-machines \
  --region "$AWS_REGION" \
  --filters "Name=file-system-id,Values=${FILESYSTEM_ID}" \
  --query "StorageVirtualMachines[?Name=='${SVM_NAME}'].StorageVirtualMachineId | [0]" \
  --output text 2>/dev/null)

if [[ "$SVM_ID" == "None" || -z "$SVM_ID" ]]; then
  info "SVM '${SVM_NAME}' does not exist yet — will create with AD config"
  SVM_EXISTS=false
else
  info "SVM '${SVM_NAME}' exists: ${SVM_ID}"
  SVM_EXISTS=true

  # Check if already joined to AD
  EXISTING_AD=$(aws fsx describe-storage-virtual-machines \
    --region "$AWS_REGION" \
    --storage-virtual-machine-ids "$SVM_ID" \
    --query 'StorageVirtualMachines[0].ActiveDirectoryConfiguration.NetBiosName' \
    --output text 2>/dev/null)

  if [[ "$EXISTING_AD" != "None" && -n "$EXISTING_AD" ]]; then
    warn "SVM is already joined to AD domain (NetBIOS: ${EXISTING_AD})"
    warn "To re-join, first unjoin via ONTAP CLI: vserver cifs delete -vserver ${SVM_NAME}"
    die "SVM already joined to AD. Aborting."
  fi
fi

# ==============================================================================
# Build AD Configuration JSON
# ==============================================================================
echo ""
echo "[3/4] Building AD join configuration"

# Convert comma-separated DNS IPs to JSON array
IFS=',' read -ra DNS_ARRAY <<< "$DNS_IPS"
DNS_JSON=$(printf '"%s",' "${DNS_ARRAY[@]}")
DNS_JSON="[${DNS_JSON%,}]"

# Convert comma-separated admin groups to JSON array
IFS=',' read -ra ADMIN_GROUPS_ARRAY <<< "$FS_ADMIN_GROUPS"
ADMIN_GROUPS_JSON=$(printf '"%s",' "${ADMIN_GROUPS_ARRAY[@]}")
ADMIN_GROUPS_JSON="[${ADMIN_GROUPS_JSON%,}]"

AD_CONFIG=$(cat <<EOF
{
  "NetBiosName": "${NETBIOS_NAME}",
  "SelfManagedActiveDirectoryConfiguration": {
    "DomainName": "${AD_DOMAIN}",
    "OrganizationalUnitDistinguishedName": "${AD_OU}",
    "FileSystemAdministratorsGroup": ${ADMIN_GROUPS_JSON},
    "UserName": "${ADMIN_USER}",
    "Password": "${AD_PASSWORD}",
    "DnsIps": ${DNS_JSON}
  }
}
EOF
)

# Display config (password masked)
DISPLAY_CONFIG=$(echo "$AD_CONFIG" | sed 's/"Password": "[^"]*"/"Password": "********"/')
info "AD Configuration:"
echo "$DISPLAY_CONFIG" | sed 's/^/    /'

# ==============================================================================
# Execute SVM Create or Update
# ==============================================================================
echo ""
echo "[4/4] Executing AD join"

if [[ "$DRY_RUN" == true ]]; then
  warn "DRY RUN — skipping actual API call"
  echo ""
  if [[ "$SVM_EXISTS" == false ]]; then
    info "Would execute: aws fsx create-storage-virtual-machine"
  else
    info "Would execute: aws fsx update-storage-virtual-machine"
  fi
  echo ""
  ok "Dry run complete. Review the configuration above."
  exit 0
fi

if [[ "$SVM_EXISTS" == false ]]; then
  # Create new SVM with AD configuration
  info "Creating SVM '${SVM_NAME}' with AD join..."
  SVM_ID=$(aws fsx create-storage-virtual-machine \
    --file-system-id "$FILESYSTEM_ID" \
    --name "$SVM_NAME" \
    --svm-admin-password "$(openssl rand -base64 16)" \
    --active-directory-configuration "$AD_CONFIG" \
    --region "$AWS_REGION" \
    --query 'StorageVirtualMachine.StorageVirtualMachineId' \
    --output text)

  ok "SVM create initiated: ${SVM_ID}"
else
  # Update existing SVM with AD configuration
  info "Updating SVM '${SVM_NAME}' with AD join..."
  aws fsx update-storage-virtual-machine \
    --storage-virtual-machine-id "$SVM_ID" \
    --active-directory-configuration "$AD_CONFIG" \
    --region "$AWS_REGION" \
    --output text > /dev/null

  ok "SVM update initiated: ${SVM_ID}"
fi

# ==============================================================================
# Wait for SVM to become CREATED / ACTIVE
# ==============================================================================
echo ""
info "Waiting for SVM AD join to complete (this may take 5-15 minutes)..."
info "You can monitor in the AWS Console: FSx > Storage virtual machines > ${SVM_ID}"
echo ""

MAX_WAIT=900  # 15 minutes
INTERVAL=30
ELAPSED=0

while [[ $ELAPSED -lt $MAX_WAIT ]]; do
  SVM_LIFECYCLE=$(aws fsx describe-storage-virtual-machines \
    --storage-virtual-machine-ids "$SVM_ID" \
    --region "$AWS_REGION" \
    --query 'StorageVirtualMachines[0].Lifecycle' \
    --output text 2>/dev/null)

  case "$SVM_LIFECYCLE" in
    CREATED)
      ok "SVM '${SVM_NAME}' is CREATED and joined to AD domain '${AD_DOMAIN}'"
      break
      ;;
    FAILED)
      err "SVM AD join FAILED."
      err "Check the SVM in the console for failure reason."
      err "Common causes:"
      err "  - DNS cannot resolve AD domain from VPC"
      err "  - Service account lacks OU delegation permissions"
      err "  - OU path does not exist in AD"
      err "  - Network connectivity to Domain Controllers is blocked"
      exit 1
      ;;
    MISCONFIGURED)
      warn "SVM is MISCONFIGURED — AD join may have partial issues"
      warn "Check the console for details and consider re-joining"
      break
      ;;
    CREATING|PENDING)
      printf "  ⏳ Status: %s (%ds elapsed)...\r" "$SVM_LIFECYCLE" "$ELAPSED"
      sleep "$INTERVAL"
      ELAPSED=$((ELAPSED + INTERVAL))
      ;;
    *)
      info "Status: ${SVM_LIFECYCLE} (${ELAPSED}s elapsed)"
      sleep "$INTERVAL"
      ELAPSED=$((ELAPSED + INTERVAL))
      ;;
  esac
done

if [[ $ELAPSED -ge $MAX_WAIT ]]; then
  warn "Timed out waiting for SVM AD join (${MAX_WAIT}s)."
  warn "Current status: ${SVM_LIFECYCLE}"
  warn "The operation may still be in progress — check the console."
  exit 2
fi

# ==============================================================================
# Post-Join Verification
# ==============================================================================
echo ""
echo "=== Post-Join Verification ==="
echo ""

# Get SVM management endpoint for ONTAP CLI access hint
MGMT_IP=$(aws fsx describe-storage-virtual-machines \
  --storage-virtual-machine-ids "$SVM_ID" \
  --region "$AWS_REGION" \
  --query 'StorageVirtualMachines[0].Endpoints.Management.IpAddresses[0]' \
  --output text 2>/dev/null || echo "N/A")

SMB_IP=$(aws fsx describe-storage-virtual-machines \
  --storage-virtual-machine-ids "$SVM_ID" \
  --region "$AWS_REGION" \
  --query 'StorageVirtualMachines[0].Endpoints.Smb.IpAddresses[0]' \
  --output text 2>/dev/null || echo "N/A")

info "SVM ID:            ${SVM_ID}"
info "SVM Name:          ${SVM_NAME}"
info "AD Domain:         ${AD_DOMAIN}"
info "NetBIOS Name:      ${NETBIOS_NAME}"
info "OU:                ${AD_OU}"
info "Management IP:     ${MGMT_IP}"
info "SMB Endpoint IP:   ${SMB_IP}"
echo ""
info "Next steps:"
info "  1. Verify DNS: nslookup ${SVM_NAME}.${AD_DOMAIN}"
info "  2. Test SMB access: smbclient -L //${SMB_IP} -U ${ADMIN_USER}@${AD_DOMAIN}"
info "  3. Create SMB shares: vserver cifs share create (via ONTAP CLI)"
info "  4. Verify SID resolution: wbinfo -n 'DOMAIN\\user'"
echo ""
ok "SVM AD join complete."
