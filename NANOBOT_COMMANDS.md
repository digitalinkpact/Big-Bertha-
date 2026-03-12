# Nanobot CLI Commands Reference

## Quick Reference

| Command | Purpose |
|---------|---------|
| `nanobot onboard` | Initialize configuration and workspace |
| `nanobot gateway` | Start the gateway service (main server) |
| `nanobot agent` | Run a single agent query |
| `nanobot status` | Show configuration and provider status |

---

## Detailed Command Documentation

### 1. Onboard (Setup)
```bash
nanobot onboard
```

**What it does:**
- Creates `~/.nanobot/config.json` if it doesn't exist
- Initializes `~/.nanobot/workspace/` directory
- Syncs template files (AGENTS.md, TOOLS.md, SOUL.md, memory/)
- Asks to overwrite if config already exists

**Options:**
- None (interactive setup)

**Example:**
```bash
$ nanobot onboard
✓ Created config at /Users/yourname/.nanobot/config.json
✓ Created workspace at /Users/yourname/.nanobot/workspace/
✓ nanobot is ready!
```

---

### 2. Gateway (Start Service)
```bash
nanobot gateway [OPTIONS]
```

**What it does:**
- Starts the main nanobot gateway server
- Connects to configured channels (Slack, Discord, Telegram, etc.)
- Listens for incoming messages
- Processes messages through the AI agent loop
- Runs cron tasks and heartbeat service

**Options:**
```
-p, --port PORT           Gateway port (default: 18790)
-w, --workspace PATH      Workspace directory path
-v, --verbose             Enable verbose/debug logging
-c, --config PATH         Path to config file
```

**Examples:**

Start on default port (18790):
```bash
nanobot gateway
```

Start on custom port:
```bash
nanobot gateway --port 9000
```

With verbose logging:
```bash
nanobot gateway -v
```

With custom config:
```bash
nanobot gateway --config ~/.nanobot/config.json
```

Custom workspace:
```bash
nanobot gateway --workspace ~/my-workspace
```

---

### 3. Agent (Single Query)
```bash
nanobot agent [OPTIONS]
```

**What it does:**
- Runs a single query through the agent
- Useful for testing or one-off commands
- Returns response without starting a persistent gateway

**Options:**
```
-m, --message TEXT        Message to send to the agent (required)
-s, --session SESSION     Session ID (default: "cli:direct")
```

**Examples:**

Simple query:
```bash
nanobot agent -m "What is 2+2?"
```

With the response:
```bash
$ nanobot agent -m "Hello nanobot"
Agent: Hello! I'm nanobot, your AI assistant. How can I help you today?
```

Custom session:
```bash
nanobot agent -m "Remember this" --session user123
```

Long message (with quotes):
```bash
nanobot agent -m "Write a poem about AI and explain it"
```

---

### 4. Status (Show Configuration)
```bash
nanobot status
```

**What it does:**
- Shows current nanobot configuration
- Lists configured providers
- Displays enabled channels
- Shows workspace path
- Validates provider setup

**Example output:**
```bash
$ nanobot status
╭─ Nanobot Configuration ──────────────────────────────────────────╮
│ Workspace: /Users/yourname/.nanobot/workspace                    │
│ Config: /Users/yourname/.nanobot/config.json                     │
│                                                                  │
│ Providers Configured:                                            │
│   ✓ XAI (API key present)                                        │
│   ✓ DeepSeek (API key present)                                   │
│   ✓ OpenAI (API key present)                                     │
│                                                                  │
│ Default Model: xai/grok-4-1-fast-reasoning                       │
│                                                                  │
│ Channels Enabled:                                                │
│   • None (CLI mode only)                                         │
╰──────────────────────────────────────────────────────────────────╯
```

---

## Common Workflows

### Setup Workflow
```bash
# 1. Install
pip install -e .

# 2. Configure
nanobot onboard

# 3. Edit config
nano ~/.nanobot/config.json

# 4. Check status
nanobot status

# 5. Start gateway
nanobot gateway
```

### Testing Workflow
```bash
# Test a quick query
nanobot agent -m "Test message"

# Test with different model
nanobot agent -m "Hello" -s test-session

# Start full gateway for integration
nanobot gateway --verbose
```

### Debug Workflow
```bash
# Check configuration
nanobot status

# Start with verbose logging
nanobot gateway --verbose

# Test agent in another terminal
nanobot agent -m "Debug test"
```

### Production Workflow
```bash
# Start background gateway
nanobot gateway --port 18790 &

# Monitor logs
tail -f ~/.nanobot/logs/nanobot.log

# Send test message
nanobot agent -m "System operational"
```

---

## Environment Variables

Override config with environment variables:

```bash
# Provider API keys
export XAI_API_KEY="xai-your-key"
export DEEPSEEK_API_KEY="sk-your-key"
export OPENAI_API_KEY="sk-your-key"

# Gateway settings
export NANOBOT_PORT=9000
export NANOBOT_WORKSPACE=~/my-workspace

# Start gateway
nanobot gateway
```

---

## Troubleshooting

### Command not found
```bash
# Make sure installation is complete
pip install -e .

# Verify installation
nanobot --help
```

### Config not found
```bash
# Run onboard
nanobot onboard

# Verify config exists
ls -la ~/.nanobot/config.json
```

### Port in use
```bash
# Use different port
nanobot gateway --port 19000

# Or find and kill process
lsof -i:18790
kill -9 <PID>
```

### Provider error
```bash
# Check configuration
nanobot status

# Verify API key
cat ~/.nanobot/config.json | grep apiKey

# Test with agent command first
nanobot agent -m "test"
```

---

## Help

Get help for any command:

```bash
nanobot --help
nanobot gateway --help
nanobot agent --help
nanobot status --help
nanobot onboard --help
```

---

## Version & Info

```bash
# Show version
nanobot --version

# Show help
nanobot -h
```
