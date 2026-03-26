#!/bin/bash
# setup_and_run_streamlit.sh — Fix venv, install deps, commit, push, and run
set -e

WORKSPACE="/workspaces/Big-Bertha-"
cd "$WORKSPACE"

echo "=== Step 1: Ensure .venv ==="
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip -q

echo "=== Step 2: Install nanobot + streamlit deps ==="
pip install -e ".[dev,streamlit]"
pip install -r streamlit_app/requirements.txt

echo "=== Step 3: Git commit & push ==="
git add streamlit_app/ || true
git commit -m "feat: add Streamlit voice chatbot UI with provider routing" 2>/dev/null || echo "(already committed or nothing to commit)"
git push origin feature/xai-provider 2>/dev/null || echo "(push failed or already up to date)"

echo "=== Step 4: Free port 8501 if occupied ==="
fuser -k 8501/tcp 2>/dev/null || true

echo "=== Step 5: Run Streamlit on 0.0.0.0:8501 ==="
cd "$WORKSPACE"
exec streamlit run streamlit_app/app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --server.headless true
