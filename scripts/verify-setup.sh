#!/usr/bin/env bash
# verify-setup.sh — Environment setup verification script
# Run after cloning to confirm all prerequisites are met.
set -euo pipefail

PASS=0
WARN=0
FAIL=0

pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
warn() { echo "  ⚠️  $1"; WARN=$((WARN + 1)); }
fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

echo "=== VMware Migration EC2+ONTAP — Environment Verification ==="
echo ""

# 1. Python
echo "[1/8] Python"
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
  pass "python3 found: $PY_VER"
else
  fail "python3 not found"
fi

# 2. Virtual environment
echo "[2/8] Virtual Environment"
if [ -d ".venv" ]; then
  pass ".venv/ exists"
  if [ -f ".venv/bin/activate" ]; then
    pass ".venv/bin/activate available"
  else
    warn ".venv exists but activate script missing"
  fi
else
  warn ".venv/ not found — run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi

# 3. Git hooks
echo "[3/8] Git Hooks"
HOOKS_PATH=$(git config core.hooksPath 2>/dev/null || echo "")
if [ "$HOOKS_PATH" = ".githooks" ]; then
  pass "core.hooksPath = .githooks"
else
  fail "core.hooksPath not set to .githooks — run: git config core.hooksPath .githooks"
fi

# 4. Git user email
echo "[4/8] Git Author Email"
GIT_EMAIL=$(git config user.email 2>/dev/null || echo "")
if echo "$GIT_EMAIL" | grep -qE '@(netapp\.com|gmail\.com)$'; then
  pass "user.email = $GIT_EMAIL"
else
  fail "user.email ($GIT_EMAIL) does not match @netapp.com or @gmail.com — pre-commit will reject commits"
fi

# 5. Security tools
echo "[5/8] Security Tools"
if command -v gitleaks &>/dev/null; then
  pass "gitleaks found: $(gitleaks version 2>&1 | head -1)"
else
  warn "gitleaks not found — install: brew install gitleaks"
fi
if command -v zizmor &>/dev/null; then
  pass "zizmor found"
else
  warn "zizmor not found — install: pip3 install zizmor"
fi

# 6. AWS CLI
echo "[6/8] AWS CLI"
if command -v aws &>/dev/null; then
  AWS_VER=$(aws --version 2>&1 | awk '{print $1}')
  pass "AWS CLI found: $AWS_VER"
  # Check if credentials are configured
  if aws sts get-caller-identity &>/dev/null 2>&1; then
    pass "AWS credentials valid"
  else
    warn "AWS credentials not configured or expired — run: aws sso login"
  fi
else
  fail "AWS CLI not found — install: brew install awscli"
fi

# 7. cfn-lint (in .venv or global)
echo "[7/8] CloudFormation Lint"
if [ -f ".venv/bin/cfn-lint" ]; then
  pass "cfn-lint found in .venv"
elif command -v cfn-lint &>/dev/null; then
  pass "cfn-lint found globally"
else
  warn "cfn-lint not found — install in venv: pip install cfn-lint"
fi

# 8. Key file paths (Apple Silicon)
echo "[8/8] Apple Silicon Paths"
if [ -x "/opt/homebrew/bin/uvx" ]; then
  pass "uvx found at /opt/homebrew/bin/uvx"
else
  warn "uvx not found at /opt/homebrew/bin/ — MCP servers may not start"
fi
if [ -x "/opt/homebrew/bin/npx" ]; then
  pass "npx found at /opt/homebrew/bin/npx"
else
  warn "npx not found at /opt/homebrew/bin/ — MCP servers may not start"
fi

# Summary
echo ""
echo "=== Summary ==="
echo "  Pass: $PASS | Warn: $WARN | Fail: $FAIL"
if [ $FAIL -gt 0 ]; then
  echo "  ❌ Setup incomplete — fix FAIL items above"
  exit 1
elif [ $WARN -gt 0 ]; then
  echo "  ⚠️  Setup functional with warnings"
  exit 0
else
  echo "  ✅ All checks passed"
  exit 0
fi
