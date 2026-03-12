# Example Nanobot Configuration

Save this as: `~/.nanobot/config.json`

## Complete Configuration Template

```json
{
  "providers": {
    "custom": {
      "apiKey": "",
      "apiBase": ""
    },
    "azure_openai": {
      "apiKey": "",
      "apiBase": ""
    },
    "anthropic": {
      "apiKey": ""
    },
    "openai": {
      "apiKey": "sk-your-chatgpt-key"
    },
    "openrouter": {
      "apiKey": ""
    },
    "deepseek": {
      "apiKey": "sk-your-deepseek-key"
    },
    "xai": {
      "apiKey": "xai-your-grok-key-here"
    },
    "groq": {
      "apiKey": ""
    },
    "zhipu": {
      "apiKey": ""
    },
    "dashscope": {
      "apiKey": ""
    },
    "vllm": {
      "apiKey": "",
      "apiBase": ""
    },
    "ollama": {
      "apiKey": "",
      "apiBase": ""
    },
    "gemini": {
      "apiKey": ""
    },
    "moonshot": {
      "apiKey": ""
    },
    "minimax": {
      "apiKey": ""
    },
    "aihubmix": {
      "apiKey": ""
    },
    "siliconflow": {
      "apiKey": ""
    },
    "volcengine": {
      "apiKey": ""
    },
    "volcengine_coding_plan": {
      "apiKey": ""
    },
    "byteplus": {
      "apiKey": ""
    },
    "byteplus_coding_plan": {
      "apiKey": ""
    },
    "openai_codex": {
      "apiKey": ""
    },
    "github_copilot": {
      "apiKey": ""
    }
  },
  "channels": {
    "whatsapp": {
      "enabled": false,
      "bridgeUrl": "ws://localhost:3001",
      "bridgeToken": "",
      "allowFrom": []
    },
    "telegram": {
      "enabled": false,
      "token": "",
      "allowFrom": [],
      "proxy": null,
      "replyToMessage": false,
      "groupPolicy": "mention"
    },
    "feishu": {
      "enabled": false,
      "appId": "",
      "appSecret": "",
      "encryptKey": "",
      "verificationToken": "",
      "allowFrom": [],
      "reactEmoji": "THUMBSUP",
      "groupPolicy": "mention"
    },
    "dingtalk": {
      "enabled": false,
      "clientId": "",
      "clientSecret": "",
      "allowFrom": []
    },
    "discord": {
      "enabled": false,
      "token": "",
      "allowFrom": [],
      "gatewayUrl": "wss://gateway.discord.gg/?v=10&encoding=json",
      "intents": 37377,
      "groupPolicy": "mention"
    },
    "matrix": {
      "enabled": false,
      "homeserver": "https://matrix.org",
      "accessToken": "",
      "userId": "",
      "deviceId": "",
      "e2eeEnabled": true,
      "syncStopGraceSeconds": 2,
      "maxMediaBytes": 20971520,
      "allowFrom": [],
      "groupPolicy": "open",
      "groupAllowFrom": [],
      "allowRoomMentions": false
    },
    "email": {
      "enabled": false,
      "consentGranted": false,
      "imapServer": "",
      "imapPort": 993,
      "smtpServer": "",
      "smtpPort": 587,
      "username": "",
      "password": "",
      "senderName": "Nanobot",
      "allowFrom": []
    },
    "slack": {
      "enabled": false,
      "appToken": "",
      "botToken": "",
      "signingSecret": "",
      "allowFrom": [],
      "groupPolicy": "mention"
    },
    "qq": {
      "enabled": false,
      "accessToken": "",
      "clientSecret": "",
      "region": "",
      "allowFrom": [],
      "groupPolicy": "mention"
    },
    "wecom": {
      "enabled": false,
      "corpId": "",
      "suiteId": "",
      "suiteSecret": "",
      "token": "",
      "encodingAESKey": "",
      "allowFrom": [],
      "groupPolicy": "mention"
    },
    "mochat": {
      "enabled": false,
      "corpId": "",
      "privateKey": "",
      "privateKeyId": "",
      "allowFrom": [],
      "groupPolicy": "mention"
    }
  },
  "agents": {
    "defaults": {
      "model": "xai/grok-4-1-fast-reasoning"
    }
  }
}
```

## Minimal Configuration (Get Started Quickly)

```json
{
  "providers": {
    "xai": {
      "apiKey": "xai-your-grok-key-here"
    },
    "deepseek": {
      "apiKey": "sk-your-deepseek-key"
    },
    "openai": {
      "apiKey": "sk-your-chatgpt-key"
    }
  },
  "agents": {
    "defaults": {
      "model": "xai/grok-4-1-fast-reasoning"
    }
  }
}
```

## Provider Key Sources

| Provider | Key Format | Get Key At |
|----------|-----------|-----------|
| **XAI/Grok** | `xai-...` | https://console.x.ai/ |
| **DeepSeek** | `sk-...` | https://platform.deepseek.com/api_keys |
| **OpenAI** | `sk-...` | https://platform.openai.com/api-keys |
| **Anthropic** | `sk-ant-...` | https://console.anthropic.com/keys |
| **Gemini** | `AIza...` | https://ai.google.dev/tutorials/setup |
| **Groq** | `gsk_...` | https://console.groq.com/keys |
| **Moonshot/Kimi** | `sk-...` | https://platform.moonshot.ai/keys |
| **DashScope/Qwen** | `sk-...` | https://dashscope.console.aliyun.com/ |
| **OpenRouter** | `sk-or-...` | https://openrouter.ai/keys |

## Configuration Notes

1. **Don't commit API keys to git!** Use `.gitignore`:
   ```
   ~/.nanobot/config.json
   .env
   ```

2. **All fields are optional** - only enable providers/channels you use

3. **Channel Configuration** - enabled/disabled per channel:
   - **disabled channels** are skipped at startup
   - **enabled channels** require valid credentials

4. **Default Model** - Must match a supported model from your providers:
   - `xai/grok-4-1-fast-reasoning` ← Recommended
   - `deepseek/deepseek-chat`
   - `gpt-4-turbo`
   - etc.

5. **Allowed Users/Groups** - Control who can use the bot:
   - Empty list = allow everyone
   - Add specific user IDs/phone numbers to restrict

## After Setup

1. Place this config at: `~/.nanobot/config.json`
2. Make it readable only by you: `chmod 600 ~/.nanobot/config.json`
3. Start nanobot gateway: `nanobot gateway`

## Security Best Practices

✓ Never hardcode API keys in code
✓ Use environment variables: `$OPENAI_API_KEY`, `$DEEPSEEK_API_KEY`, etc.
✓ Rotate keys regularly
✓ Use channel allow-lists to restrict bot access
✓ Keep `config.json` permissions tight: `chmod 600`
✓ Don't share or commit config files with keys

## Debugging Configuration

Check if config is valid:
```bash
# Show parsed configuration
nanobot status

# Test a specific provider
python -c "from nanobot.config.schema import Config; import json; print(json.dumps(Config().model_dump(), indent=2))"
```

## More Examples

See `~/.nanobot/workspace/` for template examples:
- `AGENTS.md` - Define AI agents
- `TOOLS.md` - Define tools/skills  
- `SOUL.md` - System prompts
- `memory/` - Memory management
