#!/usr/bin/env python3
"""Setup and start nanobot with the new provider configuration."""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd: str, description: str) -> int:
    """Run a shell command and print output."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}\n")
    print(f"Running: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    return result.returncode

def main():
    """Install and start nanobot."""
    
    # Verify we're in the right directory
    if not Path("pyproject.toml").exists():
        print("Error: pyproject.toml not found!")
        print("Please run this script from the nanobot root directory.")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("NANOBOT SETUP AND INSTALLATION")
    print("="*60)
    
    # Step 1: Install package
    exit_code = run_command(
        "pip install -e .",
        "Step 1: Installing nanobot package in development mode"
    )
    
    if exit_code != 0:
        print("\n❌ Installation failed!")
        sys.exit(1)
    
    print("\n✓ Installation successful!")
    
    # Step 2: Run onboard
    print("\n" + "="*60)
    print("Step 2: Nanobot Configuration (Onboard)")
    print("="*60)
    print("""
You will be asked to configure:
  ✓ Channels (Slack, Discord, Telegram, WhatsApp, Email, etc.)
  ✓ LLM Providers (OpenAI, Anthropic, DeepSeek, XAI/Grok, etc.)
  ✓ Default Model (e.g., xai/grok-4-1-fast-reasoning)
  ✓ Other optional settings
    
Available Providers:
  • OpenAI (GPT models)
  • Anthropic (Claude models)
  • DeepSeek (DeepSeek models)
  • XAI/Grok (Grok models) ← NEW!
  • And many more...

""")
    
    exit_code = run_command(
        "nanobot onboard",
        "Running Nanobot Onboard Setup"
    )
    
    if exit_code != 0:
        print("\n⚠ Onboard setup did not complete normally (may have been skipped)")
    
    # Step 3: Start nanobot
    print("\n" + "="*60)
    print("Step 3: Starting Nanobot Gateway")
    print("="*60 + "\n")
    
    exit_code = run_command(
        "nanobot gateway",
        "Starting Nanobot Gateway Service"
    )
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
