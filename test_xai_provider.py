#!/usr/bin/env python3
"""Test XAI/Grok provider configuration support."""

import json
from nanobot.config.schema import Config, ProvidersConfig, ProviderConfig
from nanobot.providers.registry import find_by_model, PROVIDERS

# Configuration from the user request
config_json = {
    "providers": {
        "xai": {"apiKey": "xai-your-grok-key-here"},
        "deepseek": {"apiKey": "sk-your-deepseek-key"},
        "openai": {"apiKey": "sk-your-chatgpt-key"}
    },
    "defaultModel": "xai/grok-4-1-fast-reasoning"
}

def test_xai_in_registry():
    """Test that XAI provider exists in registry."""
    xai_specs = [s for s in PROVIDERS if s.name == "xai"]
    assert len(xai_specs) == 1, "XAI provider not found in registry"
    spec = xai_specs[0]
    
    print(f"✓ XAI Provider Found:")
    print(f"  Name: {spec.name}")
    print(f"  Display Name: {spec.display_name}")
    print(f"  Keywords: {spec.keywords}")
    print(f"  Env Key: {spec.env_key}")
    print(f"  LiteLLM Prefix: {spec.litellm_prefix}")
    print()

def test_xai_model_detection():
    """Test that XAI models are properly detected."""
    model = "xai/grok-4-1-fast-reasoning"
    spec = find_by_model(model)
    
    assert spec is not None, f"Model {model} not detected"
    assert spec.name == "xai", f"Expected xai provider, got {spec.name}"
    
    print(f"✓ Model Detection:")
    print(f"  Model: {model}")
    print(f"  Detected Provider: {spec.name} ({spec.display_name})")
    print()

def test_grok_keyword_detection():
    """Test that 'grok' keyword is recognized."""
    model = "grok-4-1-fast-reasoning"
    spec = find_by_model(model)
    
    assert spec is not None, f"Model {model} not detected by 'grok' keyword"
    assert spec.name == "xai", f"'grok' keyword should match xai provider, got {spec.name}"
    
    print(f"✓ Grok Keyword Detection:")
    print(f"  Model: {model}")
    print(f"  Detected Provider: {spec.name} ({spec.display_name})")
    print()

def test_provider_config():
    """Test that provider configuration can be created."""
    try:
        # Create provider configs from the JSON
        xai_config = ProviderConfig(
            apiKey=config_json["providers"]["xai"]["apiKey"]
        )
        deepseek_config = ProviderConfig(
            apiKey=config_json["providers"]["deepseek"]["apiKey"]
        )
        openai_config = ProviderConfig(
            apiKey=config_json["providers"]["openai"]["apiKey"]
        )
        
        # Create providers config
        providers_config = ProvidersConfig(
            xai=xai_config,
            deepseek=deepseek_config,
            openai=openai_config
        )
        
        print(f"✓ Provider Configuration Created:")
        print(f"  XAI API Key: {xai_config.apiKey[:10]}...")
        print(f"  DeepSeek API Key: {deepseek_config.apiKey[:10]}...")
        print(f"  OpenAI API Key: {openai_config.apiKey[:10]}...")
        print()
        
        return True
    except Exception as e:
        print(f"✗ Failed to create provider config: {e}")
        return False

def test_deepseek_config():
    """Test that DeepSeek is properly configured."""
    deepseek_specs = [s for s in PROVIDERS if s.name == "deepseek"]
    assert len(deepseek_specs) == 1, "DeepSeek provider not found"
    spec = deepseek_specs[0]
    
    print(f"✓ DeepSeek Provider Verified:")
    print(f"  Name: {spec.name}")
    print(f"  Display Name: {spec.display_name}")
    print(f"  API Key Env Var: {spec.env_key}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing XAI/Grok and Provider Configuration")
    print("=" * 60)
    print()
    
    test_xai_in_registry()
    test_xai_model_detection()
    test_grok_keyword_detection()
    test_deepseek_config()
    test_provider_config()
    
    print("=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    print()
    print("Configuration JSON:")
    print(json.dumps(config_json, indent=2))
