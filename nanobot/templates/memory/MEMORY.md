# Long-term Memory

This file stores important information that should persist across sessions.

## User Information

- User works on the Nanobot (Baccano AI) framework — an ultra-lightweight multi-channel AI agent
- Active on the `feature/xai-provider` branch — integrating XAI/Grok provider support
- Uses GitHub Codespaces for development (Ubuntu 24.04 dev containers)
- Interested in trading systems, crypto bots, and 3D car design automation
- Follows strict workspace security policies (see `security_policy.md`)

## Preferences

- Prefers technical, concise communication with code examples
- Expert-level developer — skip beginner explanations
- Always verify security implications before executing system-level commands
- Uses Python 3.11+ with virtual environments (`.venv/`)
- Streamlit UI runs on port 8501 (`streamlit run streamlit_app/app.py`)

## Project Context

### Nanobot / Baccano AI (Primary)
- Multi-channel AI assistant supporting 15+ chat platforms
- 20+ LLM provider integrations via LiteLLM
- Built-in tools: shell, filesystem, web search, browser, cron, MCP
- Desktop app with Blender/AutoCAD/SolidWorks/Illustrator hooks
- Current work: XAI/Grok provider integration on `feature/xai-provider` branch

### Trading Systems (Planned)
- Algorithmic trading bots and crypto market analysis
- No files created yet — planned future project
- Will need: pandas, numpy, ccxt, ta-lib, websocket feeds

### 3D Car Design (Planned)
- Parametric car design with Blender/SolidWorks integration
- Desktop tools for AutoCAD, Blender, SolidWorks already exist in `desktop/tools/`
- Will need: STL/OBJ file handling, design automation scripts

## Important Notes

- Port 8501 may stay occupied from previous Streamlit sessions — use `fuser -k 8501/tcp` to free it
- Virtual environment is `.venv/` (not `.venv-1/` which doesn't exist)
- Config stored at `~/.nanobot/config.json` — keep permissions at 0600
- `allowFrom: []` denies all access in v0.1.4.post4+ (breaking change)
- Always activate venv before running: `source .venv/bin/activate`

---

*This file is automatically updated by nanobot when important information should be remembered.*
