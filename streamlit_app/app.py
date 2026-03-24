"""
Baccano AI — Desktop AI Assistant

Features:
- Browser mic input (st.audio_input) → Whisper STT (Groq or local)
- Text input fallback
- Baccano AI agent loop for responses
- pyttsx3 TTS (offline-capable)
- Multi-user auth with email confirmation + admin approval
- Browser localStorage for per-user memory
- Provider routing: ChatGPT → Ollama → Grok → DeepSeek fallback
- Rate limiting per session
"""

import asyncio
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

# Ensure the workspace root is on sys.path so "from streamlit_app.auth..." resolves
_WORKSPACE_ROOT = str(Path(__file__).resolve().parent.parent)
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

# Load .env file (must be before any os.environ.get calls)
from dotenv import load_dotenv
load_dotenv(Path(_WORKSPACE_ROOT) / ".env")

import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Baccano AI", page_icon="⚡", layout="centered")

# ---------------------------------------------------------------------------
# Initialise auth database
# ---------------------------------------------------------------------------
from streamlit_app.auth.db import init_db
init_db()

# ---------------------------------------------------------------------------
# Constants / limits
# ---------------------------------------------------------------------------
_MAX_MESSAGES_PER_MINUTE = 100   # rate limit: max messages per cooldown window
_RATE_WINDOW_SECONDS = 60        # rolling window size
_MAX_TEXT_LENGTH = 4000          # max chars per user message
_MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB max audio upload

# ---------------------------------------------------------------------------
# Multi-user authentication (signup, login, email confirm, admin, reset)
# ---------------------------------------------------------------------------
from streamlit_app.auth.pages import show_login_page, show_admin_panel

if not show_login_page():
    st.stop()

# ---------------------------------------------------------------------------
# Imports that depend on nanobot (loaded after auth to keep login fast)
# ---------------------------------------------------------------------------
from nanobot.config.loader import load_config
from nanobot.config.schema import Config
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.providers.transcription import GroqTranscriptionProvider
from nanobot.bus.queue import MessageBus
from nanobot.agent.loop import AgentLoop

# ---------------------------------------------------------------------------
# localStorage helper (per-user memory in the browser)
# ---------------------------------------------------------------------------
try:
    from streamlit_local_storage import LocalStorage
    _ls = LocalStorage()
except ImportError:
    _ls = None


def _ls_get(key: str, default=None):
    if _ls is None:
        return default
    val = _ls.getItem(key)
    if val is None:
        return default
    # streamlit-local-storage may return raw JSON strings — parse them
    if isinstance(val, str):
        try:
            val = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
    return val


def _ls_set(key: str, value):
    if _ls is not None:
        _ls.setItem(key, value)


# ---------------------------------------------------------------------------
# Configuration & provider routing
# ---------------------------------------------------------------------------

@st.cache_resource
def _load_baccano_config() -> Config:
    return load_config()


# Model choices available in the sidebar
_MODEL_OPTIONS: dict[str, tuple[str, str]] = {
    # label -> (provider_name, model_string)
    "ChatGPT (OpenAI)": ("openai", "gpt-4o"),
    "Ollama (local)": ("ollama", "ollama/llama3.2"),
    "Grok (XAI)": ("xai", "xai/grok-4-1-fast-reasoning"),
    "DeepSeek": ("deepseek", "deepseek/deepseek-chat"),
    "Auto (config default)": ("auto", ""),
}


def _available_models(config: Config) -> list[str]:
    """Return labels of models that are actually configured."""
    providers = config.providers
    available = []
    checks = [
        ("ChatGPT (OpenAI)", lambda: bool(providers.openai.api_key)),
        ("Ollama (local)", lambda: bool(providers.ollama.api_base)),
        ("Grok (XAI)", lambda: bool(providers.xai.api_key)),
        ("DeepSeek", lambda: bool(providers.deepseek.api_key)),
    ]
    for label, is_ready in checks:
        if is_ready():
            available.append(label)
    available.append("Auto (config default)")  # always available
    return available


def _get_api_key(pcfg, env_var: str) -> str:
    """Get API key from config, then env var, then st.secrets."""
    if pcfg.api_key:
        return pcfg.api_key
    if os.environ.get(env_var):
        return os.environ[env_var]
    try:
        return st.secrets.get(env_var, "")
    except (KeyError, FileNotFoundError):
        return ""


def _build_provider(config: Config, chosen_label: str = "Auto (config default)") -> tuple[LiteLLMProvider, str]:
    """
    Build the LLM provider.

    If chosen_label is a specific model, use it directly.
    If 'Auto', fall back through the chain using config + env vars + st.secrets.

    Returns (provider, model_name).
    """
    providers = config.providers
    defaults = config.agents.defaults

    # --- Explicit user choice from sidebar ---
    if chosen_label != "Auto (config default)" and chosen_label in _MODEL_OPTIONS:
        prov_name, model_str = _MODEL_OPTIONS[chosen_label]
        pcfg = getattr(providers, prov_name, None)
        if pcfg:
            return LiteLLMProvider(
                api_key=pcfg.api_key or None,
                api_base=pcfg.api_base,
                default_model=model_str,
                provider_name=prov_name,
            ), model_str

    # --- Auto: ordered fallback chain ---
    # Checks config file, then env vars, then st.secrets for each provider.
    chain = [
        ("deepseek", providers.deepseek, "deepseek/deepseek-chat", "DEEPSEEK_API_KEY"),
        ("xai", providers.xai, "xai/grok-4-1-fast-reasoning", "XAI_API_KEY"),
        ("openai", providers.openai, "gpt-4o", "OPENAI_API_KEY"),
        ("ollama", providers.ollama, "ollama/llama3.2", ""),
    ]

    for name, pcfg, default_model, env_var in chain:
        if name == "ollama" and pcfg.api_base:
            return LiteLLMProvider(
                api_base=pcfg.api_base,
                default_model=default_model,
                provider_name=name,
            ), default_model
        key = _get_api_key(pcfg, env_var) if env_var else ""
        if key:
            # Also set the env var so LiteLLM picks it up
            if env_var:
                os.environ[env_var] = key
            return LiteLLMProvider(
                api_key=key,
                api_base=pcfg.api_base,
                default_model=default_model,
                provider_name=name,
            ), default_model

    # Ultimate fallback
    matched_cfg = config.get_provider()
    matched_name = config.get_provider_name() or "openai"
    model = defaults.model
    return LiteLLMProvider(
        api_key=matched_cfg.api_key if matched_cfg else "",
        api_base=matched_cfg.api_base if matched_cfg else None,
        default_model=model,
        provider_name=matched_name,
    ), model


def _get_agent(chosen_model: str = "Auto (config default)") -> tuple[AgentLoop, str]:
    """Create the agent loop for the selected model."""
    # Cache key: re-create only when model choice changes
    cache_key = f"_agent_{chosen_model}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    config = _load_baccano_config()
    provider, model = _build_provider(config, chosen_model)
    workspace = config.workspace_path
    workspace.mkdir(parents=True, exist_ok=True)

    # Brave Search key: config → env var → (tool auto-falls back to DuckDuckGo)
    brave_key = config.tools.web.search.api_key or os.environ.get("BRAVE_API_KEY") or None

    bus = MessageBus()
    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=workspace,
        model=model,
        max_iterations=config.agents.defaults.max_tool_iterations,
        context_window_tokens=config.agents.defaults.context_window_tokens,
        brave_api_key=brave_key,
        web_proxy=config.tools.web.proxy,
        exec_config=config.tools.exec,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers if config.tools.mcp_servers else None,
    )
    st.session_state[cache_key] = (agent, model)
    return agent, model


# ---------------------------------------------------------------------------
# Whisper STT (server-side via Groq, offline-capable via local whisper)
# ---------------------------------------------------------------------------

def _transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio bytes to text. Tries Groq first, then local whisper."""
    if len(audio_bytes) > _MAX_AUDIO_BYTES:
        st.warning(f"Audio too large ({len(audio_bytes) // 1024 // 1024}MB). Max is {_MAX_AUDIO_BYTES // 1024 // 1024}MB.")
        return ""

    if not audio_bytes or len(audio_bytes) < 1000:
        return ""  # too short to be real audio

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        # Try Groq Whisper (fast, free tier)
        config = _load_baccano_config()
        groq_key = (
            config.providers.groq.api_key
            if config.providers.groq.api_key
            else os.environ.get("GROQ_API_KEY")
        )
        if groq_key:
            try:
                groq = GroqTranscriptionProvider(api_key=groq_key)
                text = _run_async(groq.transcribe(tmp_path))
                if text:
                    return text
            except Exception:
                pass  # fall through to local

        # Fallback: local openai-whisper (if installed)
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(tmp_path)
            return result.get("text", "")
        except ImportError:
            st.info("Offline STT unavailable. Install `openai-whisper` for local transcription, or set a Groq API key.")
            return ""
        except Exception:
            st.warning("Local Whisper transcription failed.")
            return ""
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# TTS (offline: pyttsx3)
# ---------------------------------------------------------------------------

def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so TTS speaks clean text."""
    text = re.sub(r"```[\s\S]*?```", " code block omitted ", text)  # code blocks
    text = re.sub(r"`([^`]+)`", r"\1", text)  # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # [text](url)
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)  # bold/italic
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)  # headings
    text = re.sub(r"\n{2,}", ". ", text)  # paragraph breaks → pause
    return text.strip()


def _text_to_speech(text: str, rate: int = 175) -> bytes | None:
    """Convert text to speech audio bytes. Rate is words-per-minute."""
    clean = _strip_markdown(text)
    if not clean:
        return None
    try:
        import pyttsx3
    except ImportError:
        st.caption("TTS unavailable. Install `pyttsx3` for offline speech.")
        return None

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
        engine.save_to_file(clean[:2000], tmp_path)  # cap TTS length
        engine.runAndWait()
        p = Path(tmp_path)
        if p.stat().st_size < 100:
            p.unlink(missing_ok=True)
            return None
        audio_data = p.read_bytes()
        p.unlink(missing_ok=True)
        return audio_data
    except Exception as e:
        st.caption(f"TTS error: {e}")
        return None


def _autoplay_audio_html(audio_bytes: bytes) -> None:
    """Inject an HTML <audio autoplay> tag as fallback for browsers that block st.audio autoplay."""
    # Skip if audio is too large for inline base64 (>2MB would bloat the DOM)
    if len(audio_bytes) > 2 * 1024 * 1024:
        return
    import base64
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(
        f'<audio autoplay src="data:audio/wav;base64,{b64}" style="display:none;"></audio>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Agent interaction
# ---------------------------------------------------------------------------

def _run_async(coro):
    """Safely run an async coroutine from Streamlit's sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Streamlit runs its own event loop — run in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=120)
    else:
        return asyncio.run(coro)


def _get_agent_reply(user_text: str, model_choice: str = "Auto (config default)") -> str:
    """Send user text to the Baccano AI agent and get a response.

    When a specific provider is chosen and fails, automatically tries the
    fallback chain so the user still gets a response.
    """
    agent, _model = _get_agent(model_choice)

    # Use a per-browser-session key so separate users don't share context.
    # Generate once per Streamlit session to avoid stale history pollution.
    if "_agent_session_key" not in st.session_state:
        import uuid
        st.session_state["_agent_session_key"] = f"streamlit:{uuid.uuid4().hex[:12]}"
    session_key = st.session_state["_agent_session_key"]

    import logging
    logging.info(f"[Baccano] Primary model: {_model}, session: {session_key}")

    try:
        reply = _run_async(agent.process_direct(user_text, session_key=session_key))
    except TimeoutError:
        reply = "The model took too long to respond. Please try again."
    except Exception as e:
        reply = f"Error calling LLM: {e}"

    logging.info(f"[Baccano] Primary reply status: {'OK' if reply and not reply.startswith('Error') else 'FAILED'}")
    logging.info(f"[Baccano] Reply preview: {(reply or '')[:100]}")

    # If the LLM returned an error (quota, auth, etc.), try fallback providers
    if reply and reply.startswith("Error calling LLM:"):
        logging.error(f"[Baccano] Primary FAILED: {reply[:200]}")
        original_error = reply
        config = _load_baccano_config()
        fallback_order = [
            ("deepseek", config.providers.deepseek, "deepseek/deepseek-chat"),
            ("xai", config.providers.xai, "xai/grok-4-1-fast-reasoning"),
            ("openai", config.providers.openai, "gpt-4o"),
        ]
        for name, pcfg, fallback_model in fallback_order:
            if not pcfg.api_key or name == _model.split("/")[0]:
                continue  # skip unconfigured or the one that just failed
            try:
                # Cache fallback agents in session_state to avoid leaking AgentLoop objects
                fb_cache_key = f"_fb_agent_{name}"
                if fb_cache_key not in st.session_state:
                    fb_provider = LiteLLMProvider(
                        api_key=pcfg.api_key,
                        api_base=pcfg.api_base,
                        default_model=fallback_model,
                        provider_name=name,
                    )
                    st.session_state[fb_cache_key] = AgentLoop(
                        bus=MessageBus(),
                        provider=fb_provider,
                        workspace=config.workspace_path,
                        model=fallback_model,
                        max_iterations=config.agents.defaults.max_tool_iterations,
                        context_window_tokens=config.agents.defaults.context_window_tokens,
                        brave_api_key=config.tools.web.search.api_key or None,
                        web_proxy=config.tools.web.proxy,
                        restrict_to_workspace=config.tools.restrict_to_workspace,
                    )
                fb_agent = st.session_state[fb_cache_key]
                fb_reply = _run_async(fb_agent.process_direct(user_text, session_key=session_key))
                if fb_reply and not fb_reply.startswith("Error calling LLM:"):
                    return fb_reply
            except Exception:
                continue
        # All fallbacks failed — show user-friendly message
        return f"All providers failed. Please check your API keys and billing.\n\n_Details: {original_error}_"

    return reply or "_(no response)_"


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    # Try to restore from localStorage
    saved = _ls_get("baccano_chat_history")
    if saved and isinstance(saved, list):
        st.session_state["messages"] = saved
    else:
        st.session_state["messages"] = []

if "user_facts" not in st.session_state:
    saved_facts = _ls_get("baccano_user_facts")
    st.session_state["user_facts"] = saved_facts if isinstance(saved_facts, dict) else {}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Grok-style dark theme CSS
# ---------------------------------------------------------------------------
_GROK_CSS = """
<style>
/* ── Base dark background ── */
.stApp {
    background-color: #0d0d0d;
    color: #e8e8e8;
}
section[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 1px solid #222;
}
section[data-testid="stSidebar"] * {
    color: #ccc !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d0d0d; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

/* ── Header area ── */
header[data-testid="stHeader"] {
    background-color: #0d0d0d !important;
    border-bottom: 1px solid #1a1a1a;
}

/* ── Branding ── */
.grok-brand {
    text-align: center;
    padding: 0.5rem 0 0.3rem 0;
    border-bottom: 1px solid #1a1a1a;
    margin-bottom: 1rem;
}
.grok-brand h1 {
    font-family: 'Inter', 'SF Pro Display', -apple-system, sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #ffffff;
    margin: 0;
    padding: 0;
}
.grok-brand .grok-sub {
    font-size: 0.75rem;
    color: #666;
    margin-top: 2px;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background-color: transparent !important;
    border: none !important;
    padding: 0.8rem 0 !important;
    max-width: 760px;
    margin: 0 auto;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span {
    color: #e0e0e0 !important;
    font-size: 0.95rem;
    line-height: 1.65;
}
/* User messages: subtle right-alignment feel */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background-color: #1a1a1a !important;
    border-radius: 16px !important;
    padding: 0.8rem 1.2rem !important;
}
/* Assistant messages */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background-color: transparent !important;
}
/* Avatar icons */
[data-testid="chatAvatarIcon-user"] {
    background-color: #2d2d2d !important;
}
[data-testid="chatAvatarIcon-assistant"] {
    background-color: #1a1a2e !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] {
    background-color: #0d0d0d !important;
    border-top: 1px solid #1a1a1a !important;
    padding-top: 0.5rem;
}
[data-testid="stChatInput"] textarea {
    background-color: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 24px !important;
    color: #e8e8e8 !important;
    padding: 12px 20px !important;
    font-size: 0.95rem !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #444 !important;
    box-shadow: 0 0 0 1px #333 !important;
}
[data-testid="stChatInput"] button {
    background-color: #fff !important;
    border-radius: 50% !important;
    color: #000 !important;
}

/* ── Buttons ── */
.stButton > button {
    background-color: #1a1a1a;
    color: #e0e0e0;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    font-size: 0.85rem;
    transition: background-color 0.15s;
}
.stButton > button:hover {
    background-color: #2a2a2a;
    border-color: #444;
    color: #fff;
}

/* ── Sidebar toggle/slider/divider ── */
.stSlider > div > div > div { background-color: #333 !important; }
.stSlider [data-testid="stThumbValue"] { color: #ccc !important; }
hr { border-color: #222 !important; }

/* ── Welcome empty state ── */
.grok-welcome {
    text-align: center;
    padding: 4rem 2rem 2rem 2rem;
    max-width: 600px;
    margin: 0 auto;
}
.grok-welcome h2 {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 1.8rem;
    color: #ffffff;
    margin-bottom: 0.5rem;
}
.grok-welcome p {
    color: #888;
    font-size: 1rem;
    line-height: 1.5;
}
.grok-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 1.5rem;
}
.grok-chip {
    background-color: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 20px;
    padding: 8px 16px;
    color: #aaa;
    font-size: 0.85rem;
    cursor: default;
}

/* ── Misc: spinner, info/warning boxes ── */
.stSpinner > div { color: #666 !important; }
.stAlert { background-color: #1a1a1a !important; border-color: #2a2a2a !important; }
[data-testid="stCaption"] { color: #555 !important; }

/* ── Audio input ── */
[data-testid="stAudioInput"] button {
    background-color: #1a1a1a !important;
    border: 1px solid #2a2a2a !important;
    color: #ccc !important;
}

/* ── Toggle ── */
[data-testid="stToggle"] label span { color: #ccc !important; }
</style>
"""
st.markdown(_GROK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Branding (Grok-style centered minimal header)
# ---------------------------------------------------------------------------
_current_user = st.session_state.get("current_user", {})
st.markdown(
    '<div class="grok-brand">'
    '<h1>⚡ Baccano AI</h1>'
    '<div class="grok-sub">Your private AI assistant</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar (clean, minimal)
# ---------------------------------------------------------------------------
with st.sidebar:
    config = _load_baccano_config()
    available = _available_models(config)
    chosen_model = st.selectbox("Model", available, index=len(available) - 1)
    _agent, active_model = _get_agent(chosen_model)
    st.caption(f"Active: `{active_model}`")

    if _current_user:
        st.caption(f"{_current_user.get('email', '')}")

    st.markdown("**Voice**")
    tts_enabled = st.toggle("Speak replies", value=True)
    voice_speed = st.slider(
        "Speed (WPM)",
        min_value=80, max_value=300, value=175, step=5,
        help="Words per minute. 175 is normal.",
    )

    st.divider()
    st.markdown("**Memory**")
    facts = st.session_state.get("user_facts", {})
    if facts:
        for k, v in facts.items():
            st.text(f"• {k}: {v}")
    else:
        st.caption("No learned facts yet.")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Clear chat", use_container_width=True):
            st.session_state["messages"] = []
            _ls_set("baccano_chat_history", [])
            for key in list(st.session_state.keys()):
                if key.startswith(("_agent_", "_fb_agent_")):
                    del st.session_state[key]
            st.rerun()
    with col_b:
        if st.button("Clear memory", use_container_width=True):
            st.session_state["user_facts"] = {}
            _ls_set("baccano_user_facts", {})
            st.rerun()

    if st.button("Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state.pop("current_user", None)
        st.rerun()

    # Admin panel (only visible to admins)
    current_user = st.session_state.get("current_user", {})
    if current_user.get("is_admin"):
        st.divider()
        show_admin_panel()

# ---------------------------------------------------------------------------
# Welcome state (Grok-style empty screen with suggestions)
# ---------------------------------------------------------------------------
if not st.session_state["messages"]:
    st.markdown(
        '<div class="grok-welcome">'
        '<h2>What can I help with?</h2>'
        '<p>Ask me anything — I can write, analyze, brainstorm, code, and more.</p>'
        '<div class="grok-suggestions">'
        '<span class="grok-chip">Write a short story</span>'
        '<span class="grok-chip">Explain quantum computing</span>'
        '<span class="grok-chip">Debug my code</span>'
        '<span class="grok-chip">Brainstorm ideas</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# Display chat history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Input: voice + text
# ---------------------------------------------------------------------------

# Mic input (collapsible, secondary to text)
with st.expander("🎤 Voice input", expanded=False):
    try:
        audio_input = st.audio_input("Record", key="mic")
    except Exception:
        audio_input = None
        st.caption("Mic unavailable.")

# Primary text input (Grok-style prominent bottom bar)
text_input = st.chat_input("Ask Baccano anything…")

user_text = None

# Voice input: deduplicate by hashing audio bytes so reruns don't re-transcribe
if audio_input is not None:
    audio_bytes = audio_input.getvalue()
    audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:16]
    if audio_hash != st.session_state.get("last_audio_hash"):
        st.session_state["last_audio_hash"] = audio_hash
        with st.spinner("Transcribing…"):
            user_text = _transcribe_audio(audio_bytes)
        if not user_text:
            st.warning("Could not transcribe audio. Try again or type your message.")

if text_input and not user_text:
    if len(text_input) > _MAX_TEXT_LENGTH:
        st.warning(f"Message too long ({len(text_input)} chars). Max is {_MAX_TEXT_LENGTH}.")
    else:
        user_text = text_input

# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------

if user_text:
    # --- Rate limiting ---
    msg_count = st.session_state.get("msg_count", 0)
    rate_reset = st.session_state.get("rate_reset", 0)
    now = time.time()

    # Reset counter after cooldown
    if now > rate_reset:
        msg_count = 0

    if msg_count >= _MAX_MESSAGES_PER_MINUTE:
        wait = int(rate_reset - now)
        st.warning(f"Rate limit reached ({_MAX_MESSAGES_PER_MINUTE} messages/min). Wait {max(wait, 1)}s.")
    else:
        msg_count += 1
        if msg_count == 1:
            st.session_state["rate_reset"] = now + _RATE_WINDOW_SECONDS
        st.session_state["msg_count"] = msg_count

        # Show user message
        st.session_state["messages"].append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        # Get agent reply
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                reply = _get_agent_reply(user_text, model_choice=chosen_model)
            st.markdown(reply)

        st.session_state["messages"].append({"role": "assistant", "content": reply})

        # TTS — use both st.audio(autoplay) and HTML <audio> for max compatibility
        if tts_enabled:
            tts_audio = _text_to_speech(reply, rate=voice_speed)
            if tts_audio:
                st.audio(tts_audio, format="audio/wav", autoplay=True)
                _autoplay_audio_html(tts_audio)  # fallback for browsers ignoring autoplay

        # Persist to localStorage
        _ls_set("baccano_chat_history", st.session_state["messages"][-50:])

        # Simple fact extraction: if the bot says "I'll remember that" or similar,
        # store the user message as a fact
        reply_lower = reply.lower()
        if any(phrase in reply_lower for phrase in ("i'll remember", "noted", "i've noted", "got it")):
            key = f"fact_{len(st.session_state['user_facts'])}"
            st.session_state["user_facts"][key] = user_text[:200]
            _ls_set("baccano_user_facts", st.session_state["user_facts"])
