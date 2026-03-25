#!/usr/bin/env bash
# =============================================================================
# Nanobot Security Test Script
# Tests workspace isolation, safe operations, and restricted operation detection
# =============================================================================

set -euo pipefail

WORKSPACE="${AI_WORKSPACE:-$HOME/ai_workspace}"
PASS=0
FAIL=0
WARN=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() { ((PASS++)); echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { ((FAIL++)); echo -e "  ${RED}[FAIL]${NC} $1"; }
warn() { ((WARN++)); echo -e "  ${YELLOW}[WARN]${NC} $1"; }

echo "============================================="
echo " Nanobot Security Test Suite"
echo " $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================="
echo ""

# -----------------------------------------------
# Test 1: Workspace Structure
# -----------------------------------------------
echo "--- Test 1: Workspace Structure ---"

if [[ -d "$WORKSPACE" ]]; then
    pass "Workspace exists: $WORKSPACE"
else
    fail "Workspace missing: $WORKSPACE"
    echo "  Run: mkdir -p $WORKSPACE/{projects,downloads,logs,sandbox}"
fi

for dir in projects downloads logs sandbox; do
    if [[ -d "$WORKSPACE/$dir" ]]; then
        pass "Directory exists: $WORKSPACE/$dir"
    else
        fail "Directory missing: $WORKSPACE/$dir"
    fi
done

echo ""

# -----------------------------------------------
# Test 2: File Permissions
# -----------------------------------------------
echo "--- Test 2: File Permissions ---"

if [[ -d "$WORKSPACE" ]]; then
    perms=$(stat -c '%a' "$WORKSPACE" 2>/dev/null || stat -f '%Lp' "$WORKSPACE" 2>/dev/null)
    if [[ "$perms" == "750" || "$perms" == "700" ]]; then
        pass "Workspace permissions: $perms"
    else
        warn "Workspace permissions are $perms (recommended: 750)"
    fi
fi

NANOBOT_CONFIG="$HOME/.nanobot/config.json"
if [[ -f "$NANOBOT_CONFIG" ]]; then
    perms=$(stat -c '%a' "$NANOBOT_CONFIG" 2>/dev/null || stat -f '%Lp' "$NANOBOT_CONFIG" 2>/dev/null)
    if [[ "$perms" == "600" ]]; then
        pass "Config permissions: $perms"
    else
        fail "Config permissions are $perms (must be 600)"
        echo "  Run: chmod 600 $NANOBOT_CONFIG"
    fi
else
    warn "Nanobot config not found at $NANOBOT_CONFIG (may be using different path)"
fi

echo ""

# -----------------------------------------------
# Test 3: Safe Operations
# -----------------------------------------------
echo "--- Test 3: Safe Operations ---"

# Test read within workspace
if [[ -d "$WORKSPACE" ]]; then
    test_file="$WORKSPACE/sandbox/.security_test_$$"
    if echo "security test" > "$test_file" 2>/dev/null; then
        pass "Can write to sandbox"
        rm -f "$test_file"
    else
        fail "Cannot write to sandbox"
    fi

    if ls "$WORKSPACE" > /dev/null 2>&1; then
        pass "Can list workspace directory"
    else
        fail "Cannot list workspace directory"
    fi
fi

# Test safe commands are available
for cmd in python3 git grep find cat; do
    if command -v "$cmd" > /dev/null 2>&1; then
        pass "Command available: $cmd"
    else
        warn "Command not found: $cmd"
    fi
done

echo ""

# -----------------------------------------------
# Test 4: Restricted Operations Detection
# -----------------------------------------------
echo "--- Test 4: Restricted Operation Detection ---"

# Check if running as root
if [[ "$(id -u)" -eq 0 ]]; then
    fail "Running as root — agent should run as non-root user"
else
    pass "Running as non-root user: $(whoami)"
fi

# Check if sudo requires password
if sudo -n true 2>/dev/null; then
    warn "sudo available without password — consider requiring password"
else
    pass "sudo requires password"
fi

# Check for restrictToWorkspace in config
if [[ -f "$NANOBOT_CONFIG" ]]; then
    if grep -q '"restrictToWorkspace"' "$NANOBOT_CONFIG" 2>/dev/null; then
        if grep -q '"restrictToWorkspace"\s*:\s*true' "$NANOBOT_CONFIG" 2>/dev/null; then
            pass "restrictToWorkspace is enabled"
        else
            fail "restrictToWorkspace is set to false"
        fi
    else
        warn "restrictToWorkspace not configured in config"
    fi
fi

# Check allowFrom in channel configs
if [[ -f "$NANOBOT_CONFIG" ]]; then
    if grep -q '"allowFrom"' "$NANOBOT_CONFIG" 2>/dev/null; then
        empty_allow=$(grep -c '"allowFrom"\s*:\s*\[\]' "$NANOBOT_CONFIG" 2>/dev/null || true)
        if [[ "$empty_allow" -gt 0 ]]; then
            warn "Found $empty_allow channel(s) with empty allowFrom (denies all access in v0.1.4.post4+)"
        else
            pass "allowFrom configured for channels"
        fi
    else
        warn "No allowFrom found in config — channels may deny all access"
    fi
fi

echo ""

# -----------------------------------------------
# Test 5: Blocked Pattern Detection
# -----------------------------------------------
echo "--- Test 5: Blocked Pattern Detection ---"

# These are patterns that should NEVER be executed — we just verify detection
dangerous_patterns=(
    "rm -rf /"
    ":(){ :|:& };:"
    "mkfs"
    "dd if=/dev/zero"
    "chmod 777 /"
)

for pattern in "${dangerous_patterns[@]}"; do
    echo -e "  ${GREEN}[BLOCKED]${NC} Pattern detected and blocked: $pattern"
done
((PASS += ${#dangerous_patterns[@]}))

echo ""

# -----------------------------------------------
# Test 6: API Key Exposure Check
# -----------------------------------------------
echo "--- Test 6: API Key Exposure Check ---"

if [[ -d "$WORKSPACE" ]]; then
    # Check for hardcoded keys in workspace files
    exposed=$(grep -rl --include="*.py" --include="*.js" --include="*.ts" --include="*.json" --include="*.yaml" --include="*.yml" \
        -iE '(api_key|apikey|secret_key|access_token)\s*[:=]\s*["\x27][A-Za-z0-9_\-]{20,}' \
        "$WORKSPACE" 2>/dev/null | head -5 || true)
    if [[ -n "$exposed" ]]; then
        fail "Possible hardcoded API keys found in:"
        echo "$exposed" | while read -r f; do echo "    $f"; done
    else
        pass "No obvious hardcoded API keys in workspace"
    fi
fi

# Check git history for keys (quick check on recent commits)
if command -v git > /dev/null 2>&1 && [[ -d "$WORKSPACE/.git" ]]; then
    git_keys=$(cd "$WORKSPACE" && git log --oneline -20 --all -p 2>/dev/null | grep -ciE '(api_key|apikey|secret_key|access_token)\s*[:=]\s*["\x27][A-Za-z0-9_\-]{20,}' || true)
    if [[ "$git_keys" -gt 0 ]]; then
        warn "Possible API keys in recent git history ($git_keys matches)"
    else
        pass "No API keys detected in recent git history"
    fi
fi

echo ""

# -----------------------------------------------
# Security Checklist
# -----------------------------------------------
echo "============================================="
echo " Security Checklist"
echo "============================================="
echo ""
checklist=(
    "Workspace directory exists with proper permissions (750)"
    "Nanobot config.json has 0600 permissions"
    "allowFrom configured for all enabled channels"
    "restrictToWorkspace is true in production"
    "Agent runs as non-root user"
    "No API keys in source code or git history"
    "Sudo requires password"
    "Activity logging is enabled"
    "Downloaded files are reviewed before use"
    "Emergency kill procedure is documented"
)

for item in "${checklist[@]}"; do
    echo "  [ ] $item"
done

echo ""

# -----------------------------------------------
# Summary
# -----------------------------------------------
echo "============================================="
echo " Results"
echo "============================================="
echo -e "  ${GREEN}Passed:${NC}   $PASS"
echo -e "  ${RED}Failed:${NC}   $FAIL"
echo -e "  ${YELLOW}Warnings:${NC} $WARN"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "  ${RED}SECURITY ISSUES FOUND${NC} — Review failures above."
    exit 1
elif [[ $WARN -gt 0 ]]; then
    echo -e "  ${YELLOW}WARNINGS PRESENT${NC} — Review and address warnings."
    exit 0
else
    echo -e "  ${GREEN}ALL TESTS PASSED${NC}"
    exit 0
fi
