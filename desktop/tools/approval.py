"""Safety approval gate — prompts user before executing destructive local actions.

Every desktop tool must call ``require_approval`` before running anything
that modifies files, launches programs, or interacts with external services.

The approval backend is pluggable:
  * **Streamlit** — shows an ``st.warning`` + confirm dialog in the browser.
  * **System tray** — shows a native OS notification + dialog (future).
  * **Auto-approve** — for explicitly whitelisted safe actions (e.g. read-only).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

# Type for the callback that asks the user
ApprovalCallback = Callable[..., Awaitable[bool]]

# Global registry
_approval_callback: Optional[ApprovalCallback] = None
_always_allow: set[str] = set()


@dataclass
class ApprovalRequest:
    """Describes a pending action that needs user sign-off."""
    tool: str
    action: str
    details: str = ""
    risk_level: str = "medium"  # low / medium / high


def set_approval_callback(callback: ApprovalCallback) -> None:
    """Register the function used to prompt the user for approval."""
    global _approval_callback
    _approval_callback = callback


def add_always_allow(action_pattern: str) -> None:
    """Whitelist an action pattern so it never prompts (e.g. ``read_file``)."""
    _always_allow.add(action_pattern.lower())


def remove_always_allow(action_pattern: str) -> None:
    """Remove an action pattern from the whitelist."""
    _always_allow.discard(action_pattern.lower())


async def require_approval(
    tool: str,
    action: str,
    details: str = "",
    risk_level: str = "medium",
) -> bool:
    """Ask the user to approve an action.  Returns ``True`` if approved.

    * If no callback is registered, **deny by default** (safe).
    * If the action matches an always-allow pattern, auto-approve.
    """
    # Check whitelist
    action_lower = action.lower()
    for pattern in _always_allow:
        if pattern in action_lower:
            return True

    if _approval_callback is None:
        return False

    return await _approval_callback(
        tool=tool,
        action=action,
        details=details,
        risk_level=risk_level,
    )


# ---------------------------------------------------------------------------
# Streamlit approval backend
# ---------------------------------------------------------------------------

async def streamlit_approval_callback(
    tool: str, action: str, details: str = "", **kwargs: Any,
) -> bool:
    """Approval callback that uses Streamlit session state.

    In the Streamlit UI, pending approvals are rendered as a warning box
    with Approve / Deny buttons.  This coroutine polls ``st.session_state``
    until the user clicks one.
    """
    import streamlit as st

    key = f"_approval_{hash((tool, action))}"
    st.session_state[key] = "pending"

    st.warning(
        f"**{tool}** wants to: {action}\n\n"
        f"```\n{details[:500]}\n```",
        icon="⚠️",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Allow", key=f"{key}_allow"):
            st.session_state[key] = "approved"
    with col2:
        if st.button("❌ Deny", key=f"{key}_deny"):
            st.session_state[key] = "denied"

    # Poll until user responds (with timeout)
    for _ in range(300):  # 30 seconds max
        status = st.session_state.get(key, "pending")
        if status == "approved":
            return True
        if status == "denied":
            return False
        await asyncio.sleep(0.1)

    return False  # timeout → deny
