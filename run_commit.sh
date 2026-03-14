#!/bin/bash
set -e
cd /workspaces/Big-Bertha-
git add streamlit_app/app.py streamlit_app/requirements.txt
git commit -m "feat: add Streamlit voice chatbot UI with provider routing

- Browser mic input via st.audio_input with Whisper STT (Groq/local)
- Text input fallback
- Nanobot agent loop integration for LLM responses
- pyttsx3 TTS (offline-capable)
- Session state chat history with localStorage persistence
- Password protection with brute-force lockout
- Provider routing: Ollama → Grok → DeepSeek fallback
- Rate limiting per session
- Mobile-friendly layout"
git push origin feature/xai-provider
echo "=== DONE: committed and pushed ==="
