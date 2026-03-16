"""Browser automation tool using Selenium WebDriver (headless Chrome)."""

from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from nanobot.agent.tools.base import Tool


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate URL: must be http(s) with valid domain."""
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False, f"Only http/https allowed, got '{p.scheme or 'none'}'"
        if not p.netloc:
            return False, "Missing domain"
        return True, ""
    except Exception as e:
        return False, str(e)


def _get_driver():
    """Create a headless Chrome WebDriver instance."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    # Reduce detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    return driver


class BrowserTool(Tool):
    """Interact with web pages using a headless browser.

    Supports: navigating to URLs, extracting page content (including
    JavaScript-rendered pages), taking screenshots, clicking elements,
    filling forms, and running JavaScript.
    """

    name = "browser"
    description = (
        "Control a headless Chrome browser. Can navigate to URLs, extract "
        "JS-rendered page content, take screenshots, click elements, fill "
        "forms, and execute JavaScript. Use this when web_fetch can't handle "
        "a page (e.g. JS-rendered content, SPAs, login forms)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "get_content",
                    "screenshot",
                    "click",
                    "fill",
                    "execute_js",
                    "back",
                    "close",
                ],
                "description": (
                    "Action to perform. 'navigate': go to URL. "
                    "'get_content': extract visible text/HTML. "
                    "'screenshot': capture page as base64 PNG. "
                    "'click': click element by CSS selector. "
                    "'fill': type text into element by CSS selector. "
                    "'execute_js': run JavaScript snippet. "
                    "'back': go to previous page. "
                    "'close': close the browser session."
                ),
            },
            "url": {
                "type": "string",
                "description": "URL to navigate to (for 'navigate' action).",
            },
            "selector": {
                "type": "string",
                "description": "CSS selector for the target element (for 'click'/'fill').",
            },
            "text": {
                "type": "string",
                "description": "Text to type (for 'fill') or JS code (for 'execute_js').",
            },
            "extract_mode": {
                "type": "string",
                "enum": ["text", "html", "markdown"],
                "description": "Content extraction mode (for 'get_content'). Default: text.",
            },
        },
        "required": ["action"],
    }

    # Max chars for content extraction to avoid overwhelming the context
    MAX_CONTENT_CHARS = 50_000

    def __init__(self):
        self._driver = None

    def _ensure_driver(self):
        """Lazily create the WebDriver."""
        if self._driver is None:
            self._driver = _get_driver()
            logger.info("Browser: headless Chrome session started")
        return self._driver

    async def execute(
        self,
        action: str,
        url: str | None = None,
        selector: str | None = None,
        text: str | None = None,
        extract_mode: str = "text",
        **kwargs: Any,
    ) -> str:
        try:
            if action == "navigate":
                return self._navigate(url)
            elif action == "get_content":
                return self._get_content(extract_mode)
            elif action == "screenshot":
                return self._screenshot()
            elif action == "click":
                return self._click(selector)
            elif action == "fill":
                return self._fill(selector, text)
            elif action == "execute_js":
                return self._execute_js(text)
            elif action == "back":
                return self._back()
            elif action == "close":
                return self._close()
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            logger.error("Browser tool error ({}): {}", action, e)
            return f"Browser error: {e}"

    def _navigate(self, url: str | None) -> str:
        if not url:
            return "Error: 'url' is required for navigate action."
        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            return f"URL validation failed: {error_msg}"

        driver = self._ensure_driver()
        driver.get(url)
        title = driver.title or "(no title)"
        current = driver.current_url
        return json.dumps(
            {"status": "ok", "title": title, "url": current},
            ensure_ascii=False,
        )

    def _get_content(self, mode: str = "text") -> str:
        driver = self._ensure_driver()
        if not driver.current_url or driver.current_url == "data:,":
            return "Error: no page loaded. Use 'navigate' first."

        title = driver.title or ""

        if mode == "html":
            content = driver.page_source
        elif mode == "markdown":
            content = self._html_to_markdown(driver.page_source, title)
        else:
            content = driver.find_element("tag name", "body").text

        truncated = len(content) > self.MAX_CONTENT_CHARS
        if truncated:
            content = content[: self.MAX_CONTENT_CHARS]

        return json.dumps(
            {
                "url": driver.current_url,
                "title": title,
                "mode": mode,
                "truncated": truncated,
                "length": len(content),
                "content": content,
            },
            ensure_ascii=False,
        )

    def _screenshot(self) -> str:
        import base64

        driver = self._ensure_driver()
        if not driver.current_url or driver.current_url == "data:,":
            return "Error: no page loaded. Use 'navigate' first."

        png_bytes = driver.get_screenshot_as_png()
        b64 = base64.b64encode(png_bytes).decode()
        return json.dumps(
            {
                "url": driver.current_url,
                "title": driver.title,
                "format": "png",
                "size_bytes": len(png_bytes),
                "base64": b64[:200] + "..." if len(b64) > 200 else b64,
                "note": "Screenshot captured. Full base64 truncated in output.",
            },
            ensure_ascii=False,
        )

    def _click(self, selector: str | None) -> str:
        if not selector:
            return "Error: 'selector' is required for click action."

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        driver = self._ensure_driver()
        try:
            el = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            el.click()
            return json.dumps(
                {"status": "clicked", "selector": selector, "url": driver.current_url},
                ensure_ascii=False,
            )
        except Exception as e:
            return f"Click failed for '{selector}': {e}"

    def _fill(self, selector: str | None, text: str | None) -> str:
        if not selector:
            return "Error: 'selector' is required for fill action."
        if not text:
            return "Error: 'text' is required for fill action."

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        driver = self._ensure_driver()
        try:
            el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            el.clear()
            el.send_keys(text)
            return json.dumps(
                {"status": "filled", "selector": selector, "length": len(text)},
                ensure_ascii=False,
            )
        except Exception as e:
            return f"Fill failed for '{selector}': {e}"

    def _execute_js(self, script: str | None) -> str:
        if not script:
            return "Error: 'text' (JS code) is required for execute_js action."

        # Block dangerous patterns
        blocked = re.search(
            r"\b(fetch|XMLHttpRequest|import\s*\(|eval\s*\(|Function\s*\()\b",
            script,
        )
        if blocked:
            return f"Blocked: '{blocked.group()}' is not allowed in execute_js for safety."

        driver = self._ensure_driver()
        try:
            result = driver.execute_script(script)
            if result is None:
                return '{"status": "executed", "result": null}'
            return json.dumps(
                {"status": "executed", "result": str(result)[:5000]},
                ensure_ascii=False,
            )
        except Exception as e:
            return f"JS execution error: {e}"

    def _back(self) -> str:
        driver = self._ensure_driver()
        driver.back()
        return json.dumps(
            {"status": "ok", "url": driver.current_url, "title": driver.title},
            ensure_ascii=False,
        )

    def _close(self) -> str:
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
            logger.info("Browser: session closed")
        return '{"status": "closed"}'

    @staticmethod
    def _html_to_markdown(html_source: str, title: str = "") -> str:
        """Best-effort HTML to markdown conversion."""
        text = html_source
        # Remove script/style
        text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.I)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.I)
        # Headers
        for i in range(1, 7):
            text = re.sub(
                rf"<h{i}[^>]*>(.*?)</h{i}>",
                lambda m, n=i: f"\n{'#' * n} {m.group(1).strip()}\n",
                text,
                flags=re.I | re.DOTALL,
            )
        # Links
        text = re.sub(
            r'<a[^>]+href="([^"]*)"[^>]*>(.*?)</a>',
            r"[\2](\1)",
            text,
            flags=re.I | re.DOTALL,
        )
        # Bold / italic
        text = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.I | re.DOTALL)
        text = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", text, flags=re.I | re.DOTALL)
        # Line breaks / paragraphs
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"<p[^>]*>", "\n\n", text, flags=re.I)
        text = re.sub(r"</p>", "", text, flags=re.I)
        # Lists
        text = re.sub(r"<li[^>]*>", "\n- ", text, flags=re.I)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", "", text)
        # Decode entities
        import html as html_mod
        text = html_mod.unescape(text)
        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        if title:
            text = f"# {title}\n\n{text.strip()}"
        return text.strip()

    def __del__(self):
        self._close()
