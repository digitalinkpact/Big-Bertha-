#!/usr/bin/env python3
"""Baccano AI diagnostic — tests provider connections and tool registration."""
import asyncio
import sys
sys.path.insert(0, "/workspaces/Big-Bertha-")

from nanobot.config.loader import load_config
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.bus.queue import MessageBus
from nanobot.agent.loop import AgentLoop


def main():
    config = load_config()
    providers = config.providers
    workspace = config.workspace_path

    print("=" * 60)
    print("BACCANO AI DIAGNOSTIC")
    print("=" * 60)

    # 1. Check API keys
    print("\n--- API Keys ---")
    keys = {
        "xai": bool(providers.xai.api_key),
        "openai": bool(providers.openai.api_key),
        "deepseek": bool(providers.deepseek.api_key),
        "groq": bool(providers.groq.api_key),
        "anthropic": bool(providers.anthropic.api_key),
    }
    for name, has_key in keys.items():
        status = "✓ SET" if has_key else "✗ missing"
        print(f"  {name:12s}: {status}")

    # 2. Check workspace + SOUL.md
    print(f"\n--- Workspace ---")
    print(f"  Path: {workspace}")
    soul = workspace / "SOUL.md"
    if soul.exists():
        first_line = soul.read_text().split("\n")[1] if soul.read_text() else "(empty)"
        print(f"  SOUL.md: {first_line[:60]}")
    else:
        print(f"  SOUL.md: MISSING")

    # 3. Check Brave API key (for web search)
    brave_key = config.tools.web.search.api_key
    print(f"\n--- Web Search ---")
    print(f"  Brave API key: {'SET' if brave_key else 'NOT SET (will use DuckDuckGo fallback)'}")

    # 4. Build provider chain (same logic as app.py _build_provider)
    print(f"\n--- Provider Chain (Auto mode) ---")
    chain = [
        ("xai", providers.xai, "xai/grok-4-1-fast-reasoning"),
        ("openai", providers.openai, "gpt-4o"),
        ("deepseek", providers.deepseek, "deepseek/deepseek-chat"),
    ]
    selected = None
    for name, pcfg, model in chain:
        if pcfg.api_key:
            if selected is None:
                selected = (name, model)
                print(f"  → {name:12s} ({model}) — PRIMARY")
            else:
                print(f"    {name:12s} ({model}) — fallback")
        else:
            print(f"    {name:12s} — skipped (no key)")

    if not selected:
        print("  ✗ NO PROVIDER HAS AN API KEY — nothing will work!")
        return

    # 5. Create agent and check tools
    prov_name, prov_model = selected
    pcfg = getattr(providers, prov_name)
    provider = LiteLLMProvider(
        api_key=pcfg.api_key,
        api_base=pcfg.api_base,
        default_model=prov_model,
        provider_name=prov_name,
    )
    agent = AgentLoop(
        bus=MessageBus(),
        provider=provider,
        workspace=workspace,
        model=prov_model,
        max_iterations=config.agents.defaults.max_tool_iterations,
        context_window_tokens=config.agents.defaults.context_window_tokens,
        brave_api_key=config.tools.web.search.api_key or None,
        web_proxy=config.tools.web.proxy,
        restrict_to_workspace=config.tools.restrict_to_workspace,
    )

    tool_defs = agent.tools.get_definitions()
    print(f"\n--- Registered Tools ({len(tool_defs)}) ---")
    for t in tool_defs:
        print(f"  • {t['function']['name']:20s} — {t['function']['description'][:50]}")

    # 6. Check system prompt
    system_prompt = agent.context.build_system_prompt()
    print(f"\n--- System Prompt (first 300 chars) ---")
    print(f"  {system_prompt[:300]}")
    has_baccano = "baccano" in system_prompt.lower()
    has_web_search = "web_search" in system_prompt
    print(f"\n  Contains 'Baccano': {'✓' if has_baccano else '✗ MISSING'}")
    print(f"  Contains 'web_search': {'✓' if has_web_search else '✗ MISSING'}")

    # 7. Test actual API call
    print(f"\n--- Testing API Call ({prov_name}/{prov_model}) ---")
    try:
        response = asyncio.run(provider.chat(
            messages=[
                {"role": "system", "content": "You are Baccano AI. Reply in exactly one short sentence."},
                {"role": "user", "content": "Who are you?"},
            ],
            tools=tool_defs,
            model=prov_model,
            max_tokens=100,
        ))
        if response.content and response.content.startswith("Error calling LLM:"):
            print(f"  ✗ API ERROR: {response.content}")
        else:
            print(f"  ✓ Response: {(response.content or '(empty)')[:150]}")
            print(f"  Tool calls: {len(response.tool_calls) if response.tool_calls else 0}")
            print(f"  Finish reason: {response.finish_reason}")
    except Exception as e:
        print(f"  ✗ EXCEPTION: {e}")

    # 8. Test fallback providers
    for name, pcfg, model in chain:
        if name == prov_name or not pcfg.api_key:
            continue
        print(f"\n--- Testing Fallback: {name}/{model} ---")
        try:
            fb = LiteLLMProvider(
                api_key=pcfg.api_key,
                api_base=pcfg.api_base,
                default_model=model,
                provider_name=name,
            )
            resp = asyncio.run(fb.chat(
                messages=[
                    {"role": "system", "content": "You are Baccano AI. Reply in one sentence."},
                    {"role": "user", "content": "Who are you?"},
                ],
                model=model,
                max_tokens=100,
            ))
            if resp.content and resp.content.startswith("Error calling LLM:"):
                print(f"  ✗ API ERROR: {resp.content[:150]}")
            else:
                print(f"  ✓ Response: {(resp.content or '(empty)')[:150]}")
        except Exception as e:
            print(f"  ✗ EXCEPTION: {e}")

    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
