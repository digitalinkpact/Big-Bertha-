# Nanobot Security Policy

## Overview

This document defines the security policy for the nanobot AI agent operating within a controlled workspace. It establishes security levels, permission protocols, and monitoring procedures to ensure safe autonomous operation.

---

## Security Levels

### Level 1: Always Allowed (Safe Operations)

Operations the agent can perform without asking permission:

| Category | Examples |
|----------|----------|
| **Read files** | Read any file within `~/ai_workspace/` |
| **Write files** | Create/edit files within `~/ai_workspace/projects/` and `~/ai_workspace/sandbox/` |
| **List directories** | `ls`, `find`, `tree` within workspace |
| **Run safe commands** | `python`, `node`, `git status`, `git diff`, `git log`, `cat`, `grep`, `wc` |
| **Install Python packages** | `pip install` in virtual environments within workspace |
| **Git operations (local)** | `git add`, `git commit`, `git branch`, `git checkout`, `git stash` |
| **Search** | Web search via configured search tools |
| **Logging** | Write to `~/ai_workspace/logs/` |

### Level 2: Ask Permission (Restricted Operations)

Operations that require explicit user approval before execution:

| Category | Examples |
|----------|----------|
| **System packages** | `apt install`, `brew install`, `npm install -g` |
| **Git push/remote** | `git push`, `git remote add`, `git fetch` |
| **Network operations** | `curl` to external APIs, `wget`, opening ports |
| **File operations outside workspace** | Read/write anything outside `~/ai_workspace/` |
| **Process management** | `kill`, `pkill`, starting background daemons |
| **Docker operations** | `docker run`, `docker build`, `docker-compose up` |
| **Config file changes** | Modifying `~/.nanobot/config.json`, `.env` files |
| **Cron/scheduled tasks** | Creating or modifying cron jobs |
| **Database operations** | Schema changes, data deletion, migrations |

### Level 3: Never Allowed (Blocked Operations)

Operations the agent must never execute under any circumstances:

| Category | Examples |
|----------|----------|
| **Destructive filesystem** | `rm -rf /`, `rm -rf ~`, `mkfs`, `dd if=/dev/zero` |
| **Fork bombs** | `:(){ :\|:& };:` or equivalent |
| **Credential exfiltration** | Sending API keys, tokens, or passwords to external services |
| **Privilege escalation** | `sudo` without explicit approval, `chmod 777`, `chown root` |
| **Network attacks** | Port scanning, brute force, DNS poisoning |
| **Kernel modifications** | `modprobe`, `insmod`, writing to `/proc` or `/sys` |
| **Bypass security controls** | `--no-verify`, disabling firewalls, removing audit logs |

---

## Permission Request Protocol

When the agent needs to perform a Level 2 (restricted) operation, it must use this format:

```
[SECURITY] Permission Required
Action: <specific command or operation>
Location: <file path or system area affected>
Impact: <what changes will occur>
Reason: <why this action is necessary for the current task>
Confirmation: Reply "APPROVE <action-tag>" to authorize
```

### Rules

1. **One action per request** — Do not bundle multiple restricted actions.
2. **Wait for approval** — Do not proceed until the user replies with `APPROVE`.
3. **Exact execution** — Execute only the approved action, not a modified version.
4. **Timeout** — If no response within the session, do not proceed.

---

## Workspace Configuration

### Directory Structure

```
~/ai_workspace/                    # Root workspace (chmod 750)
├── projects/                      # Active project files (read/write)
├── downloads/                     # Downloaded files (quarantine zone)
├── logs/                          # Agent activity logs
│   ├── actions.log                # All executed commands
│   ├── permissions.log            # Permission requests and responses
│   └── errors.log                 # Errors and security events
└── sandbox/                       # Experimental/test area (read/write)
```

### File Permissions

```bash
# Workspace root
chmod 750 ~/ai_workspace

# Project and sandbox (agent can read/write)
chmod 750 ~/ai_workspace/projects
chmod 750 ~/ai_workspace/sandbox

# Downloads (agent writes, user reviews)
chmod 750 ~/ai_workspace/downloads

# Logs (append-only for agent)
chmod 750 ~/ai_workspace/logs
```

---

## Nanobot Configuration (nanobot.yaml / config.json)

### Restrict Agent to Workspace

```json
{
  "tools": {
    "restrictToWorkspace": true,
    "exec": {
      "timeout": 60
    }
  }
}
```

### Channel Access Control

Always set `allowFrom` for production channels:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

> **Warning**: As of v0.1.4.post4, an empty `allowFrom` list denies all access (previously it allowed all). Set `["*"]` to explicitly allow everyone.

### API Key Security

```bash
# Store config with restricted permissions
chmod 600 ~/.nanobot/config.json

# Never commit keys to version control
echo "config.json" >> ~/.nanobot/.gitignore
```

---

## Monitoring and Audit Procedures

### Activity Logging

The agent should log every command it executes:

```bash
# Log format: [TIMESTAMP] [LEVEL] [ACTION] [DETAILS]
# Example:
[2026-03-25T00:30:00Z] [SAFE] [exec] python3 test_suite.py
[2026-03-25T00:31:00Z] [RESTRICTED] [request] apt install nodejs — PENDING
[2026-03-25T00:31:15Z] [RESTRICTED] [approved] apt install nodejs — APPROVED by user
```

### Security Audit Checklist

Run periodically to verify security posture:

- [ ] `~/.nanobot/config.json` permissions are `0600`
- [ ] `allowFrom` is configured for all enabled channels
- [ ] No API keys in version control (`git log --all -p | grep -i "apikey\|api_key\|token"`)
- [ ] `restrictToWorkspace` is `true` in production
- [ ] Agent runs as non-root user
- [ ] Logs are being written and rotated
- [ ] No unexpected cron jobs (`crontab -l`)
- [ ] Downloaded files reviewed before use

### Emergency Procedures

If the agent behaves unexpectedly:

1. **Stop the agent**: `Ctrl+C` or `kill $(pgrep -f nanobot)`
2. **Review logs**: `tail -100 ~/ai_workspace/logs/actions.log`
3. **Check for damage**: `git status`, `git diff` in project directories
4. **Revoke API keys** if credential exposure is suspected
5. **Report**: Document the incident with timestamps and log excerpts

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-25 | Initial security policy |
