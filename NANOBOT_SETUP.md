# Nanobot Setup and Installation Guide

## Quick Start

You have three options to install and start nanobot:

### Option 1: Python Setup Script (Recommended)
```bash
python setup_nanobot.py
```

### Option 2: Bash Setup Script
```bash
bash setup_and_start.sh
```

### Option 3: Manual Steps
```bash
pip install -e .
nanobot onboard
nanobot gateway
```

---

## Installation Overview

### Step 1: Install Package
```bash
pip install -e .
```

This installs nanobot in development mode with all dependencies including:
- **LiteLLM** - Multi-provider LLM support
- **Typer** - CLI framework
- **Pydantic** - Configuration validation
- **WebSockets** - Real-time communication
- Plus many more dependencies for various channels and features

### Step 2: Configure (Onboard)
```bash
nanobot onboard
```

The `onboard` command will:
1. **Create configuration** at `~/.nanobot/config.json`
2. **Initialize workspace** at `~/.nanobot/workspace/`
3. **Sync templates** for agents, tools, memory, etc.
4. **Ask to overwrite** if config already exists (Y = overwrite, N = refresh with defaults)

**Configuration includes:**
- ✓ Communication channels (Slack, Discord, Telegram, WhatsApp, Email, etc.)
- ✓ LLM provider keys (OpenAI, Anthropic, DeepSeek, **XAI/Grok**, etc.)
- ✓ Default model
- ✓ Bot behavior settings

### Step 3: Start Nanobot (Gateway)
```bash
nanobot gateway
```

Launches the nanobot gateway service and connects to configured channels.

Optional flags:
- `-p, --port` - Gateway port (default: 18790)
- `-w, --workspace` - Workspace directory
- `-v, --verbose` - Verbose output
- `-c, --config` - Path to config file

---

## Provider Configuration

Your `~/.nanobot/config.json` should include:

```json
{
  "providers": {
    "openai": {
      "apiKey": "sk-your-chatgpt-key"
    },
    "deepseek": {
      "apiKey": "sk-your-deepseek-key"
    },
    "xai": {
      "apiKey": "xai-your-grok-key-here"
    }
  },
  "agents": {
    "defaults": {
      "model": "xai/grok-4-1-fast-reasoning"
    }
  }
}
```

### Supported Models

After adding provider keys, you can use any of these models:

**XAI/Grok** ← NEW!
- `xai/grok-4-1-fast-reasoning`
- `xai/grok-3`

**DeepSeek**
- `deepseek/deepseek-chat`
- `deepseek/deepseek-reasoner`

**OpenAI**
- `gpt-4-turbo`
- `gpt-4o`
- `gpt-4-mini`

**Anthropic**
- `claude-opus-4-1`
- `claude-opus-4`
- `claude-sonnet-4`

**And many more...** (Gemini, Moonshot/Kimi, vLLM, Ollama, etc.)

---

## Onboard Workflow

When you run `nanobot onboard`, you'll be asked about:

### 1. Existing Configuration
- If config exists: Y (overwrite) or N (refresh)
- Typically answer **N** to preserve your API keys

### 2. Workspace Setup
- Creates folder structure at `~/.nanobot/`
- Syncs template files for:
  - `AGENTS.md` - Agent definitions
  - `TOOLS.md` - Tool specifications  
  - `SOUL.md` - System prompts
  - `memory/` - Memory management

### 3. Configuration File
Created at: `~/.nanobot/config.json`

Edit this file to add your LLM provider keys and configure channels.

---

## Starting Nanobot

```bash
nanobot start
```

### Console Interface
- Type messages to chat with the agent
- Commands: `exit`, `quit`, `/exit`, `/quit`, `:q`
- Supports multi-line input (Ctrl+Enter in some terminals)

### Channel Integration
If configured, nanobot will also connect to:
- Slack/Teams/Discord
- Telegram/WhatsApp
- Email (IMAP/SMTP)
- DingTalk, Feishu, Matrix, etc.

### Other Available Commands

**Run a single agent query:**
```bash
nanobot agent -m "Your message here"
```

**Check status:**
```bash
nanobot status
```

**Start gateway on custom port:**
```bash
nanobot gateway --port 9000
```

**Verbose output for debugging:**
```bash
nanobot gateway --verbose
```

---

## Testing Installation

After installation, verify everything works:

```bash
# Test XAI provider configuration
python test_xai_setup.py

# Show nanobot version and status
nanobot --version
nanobot status

# Run a simple query (if config is set up)
nanobot agent -m "Hello, test this installation"
```

---

## Troubleshooting

### Config Not Found
- Ensure you ran `nanobot onboard` successfully
- Config should be at: `~/.nanobot/config.json`
- Check with: `ls -la ~/.nanobot/`

### Provider API Key Error
- Verify `apiKey` spelling in config (camelCase)
- Restart nanobot after changing API keys
- Check provider website for active key

### No Module Named 'nanobot'
- Ensure `pip install -e .` completed successfully
- Try: `pip install -e . --force-reinstall`

### Connection Issues
- Check network connectivity
- Verify API endpoints are accessible
- Check provider status pages

---

## Next Steps

1. **Run setup**: `python setup_nanobot.py`
2. **Edit config**: `~/.nanobot/config.json`
3. **Start gateway**: `nanobot gateway`
4. **Create agent**: Update `~/.nanobot/workspace/AGENTS.md`
5. **Add tools**: Define tools in `~/.nanobot/workspace/TOOLS.md`

---

## Files Created

- `setup_nanobot.py` - Python setup script (recommended)
- `setup_and_start.sh` - Bash setup script
- `test_xai_setup.py` - Provider configuration test

All scripts are in the nanobot root directory.
