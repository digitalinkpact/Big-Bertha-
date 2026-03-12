#!/usr/bin/env bash
# Nanobot Setup and Start Script

set -e

echo "======================================"
echo "Nanobot Setup and Installation"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "Error: pyproject.toml not found. Please run this script from the nanobot root directory."
    exit 1
fi

echo "Step 1: Installing nanobot package in development mode..."
echo ""
pip install -e .

echo ""
echo "Step 2: Nanobot installed successfully!"
echo ""
echo "======================================"
echo "Running Nanobot Onboard Setup"
echo "======================================"
echo ""
echo "You will be asked to configure:"
echo "  - Channels (Slack, Discord, Telegram, etc.)"
echo "  - LLM Providers (OpenAI, Anthropic, DeepSeek, XAI/Grok, etc.)"
echo "  - Default Model"
echo "  - Other optional settings"
echo ""

nanobot onboard

echo ""
echo "======================================"
echo "Starting Nanobot Gateway"
echo "======================================"
echo ""

nanobot gateway
