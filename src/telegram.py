"""
Telegram delivery module.

Sends briefings via Telegram Bot API using aiohttp.
Uses HTML parse_mode for maximum LLM output compatibility.
"""

from __future__ import annotations

import logging

import aiohttp

from src.config import VeraConfig

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4096


async def send_briefing(config: VeraConfig, message: str) -> None:
    """
    Send a briefing message via Telegram.

    Automatically splits messages exceeding 4096 characters.
    Uses HTML parse_mode (more robust than MarkdownV2 for LLM output).
    """
    token = config.secrets.telegram_bot_token
    chat_id = config.secrets.telegram_chat_id

    # Split long messages
    parts = _split_message(message)

    async with aiohttp.ClientSession() as session:
        for i, part in enumerate(parts):
            url = f"{TELEGRAM_API}/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": part,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }

            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info(
                        f"Message {i + 1}/{len(parts)} sent "
                        f"({len(part)} chars)"
                    )
                else:
                    body = await resp.json()
                    error_desc = body.get("description", "Unknown error")

                    # If HTML parsing fails, retry without parse_mode
                    if "can't parse" in error_desc.lower():
                        logger.warning(
                            f"HTML parse failed, sending as plain text: {error_desc}"
                        )
                        payload["parse_mode"] = ""
                        # Strip HTML tags for plain fallback
                        payload["text"] = _strip_html(part)
                        async with session.post(url, json=payload) as retry_resp:
                            if retry_resp.status == 200:
                                logger.info(f"Message {i + 1} sent (plain fallback)")
                            else:
                                retry_body = await retry_resp.json()
                                logger.error(
                                    f"Failed to send message {i + 1}: "
                                    f"{retry_body.get('description')}"
                                )
                    else:
                        logger.error(
                            f"Telegram API error ({resp.status}): {error_desc}"
                        )


def _split_message(text: str) -> list[str]:
    """
    Split a message into chunks respecting Telegram's 4096 char limit.
    Tries to split at paragraph boundaries.
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    parts = []
    remaining = text

    while remaining:
        if len(remaining) <= MAX_MESSAGE_LENGTH:
            parts.append(remaining)
            break

        # Find last paragraph break within limit
        chunk = remaining[:MAX_MESSAGE_LENGTH]
        split_pos = chunk.rfind("\n\n")

        if split_pos == -1 or split_pos < MAX_MESSAGE_LENGTH // 2:
            # No good paragraph break, try single newline
            split_pos = chunk.rfind("\n")

        if split_pos == -1 or split_pos < MAX_MESSAGE_LENGTH // 2:
            # No good break at all, hard split
            split_pos = MAX_MESSAGE_LENGTH

        parts.append(remaining[:split_pos].rstrip())
        remaining = remaining[split_pos:].lstrip()

    return parts


def _strip_html(text: str) -> str:
    """Basic HTML tag removal for plain text fallback."""
    import re
    return re.sub(r"<[^>]+>", "", text)
