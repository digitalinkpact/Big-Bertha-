#!/bin/bash
# setup_and_run_streamlit.sh — Fix venv, install deps, commit, push, and run
set -e

WORKSPACE="/workspaces/Big-Bertha-"
cd "$WORKSPACE"

echo "=== Step 1: Recreate .venv ==="
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
python -m ensurepip --upgrade 2>/dev/null || true
pip install --upgrade pip

echo "=== Step 2: Install nanobot + streamlit deps ==="
pip install -e ".[dev]"
pip install streamlit streamlit-local-storage pyttsx3

echo "=== Step 3: Git commit & push ==="
git add streamlit_app/ || true
git commit -m "feat: add Streamlit voice chatbot UI with provider routing" 2>/dev/null || echo "(already committed or nothing to commit)"
git push origin feature/xai-provider 2>/dev/null || echo "(push failed or already up to date)"

echo "=== Step 4: Run Streamlit on 0.0.0.0:8501 ==="
cd "$WORKSPACE/streamlit_app"
exec streamlit run app.py
