"""Entry point: start the Feishu agent bot."""

import asyncio
import json
import logging
import re
import signal

from agent.config import LoadConfig
from agent.feishu import FeishuBot
from agent.llm import LlmClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Regex to strip ```json ... ``` wrapping that LLMs often add.
_CODE_BLOCK_RE = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL
)


def ExtractJson(raw: str) -> str:
    """Extract valid JSON from LLM output.

    Handles common LLM quirks:
      - ```json ... ``` wrapping
      - Leading/trailing prose around the JSON object
      - Extra whitespace
      - Strings containing braces (proper quote-aware matching)
    """
    text = raw.strip()

    # Try stripping ```json ... ``` block.
    match = _CODE_BLOCK_RE.search(text)
    if match:
        text = match.group(1).strip()

    # If it still doesn't start with '{', find the first '{'.
    start = text.find("{")
    if start == -1:
        return raw  # give up, return as-is

    # Find the matching closing '}', handling strings properly.
    depth = 0
    in_string = False
    escape = False
    end = start
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            if in_string:
                escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    return text[start : end + 1]


async def Main() -> None:
    config = LoadConfig()
    llm = LlmClient(config.llm)
    bot = FeishuBot(config.feishu, config.card)

    async def HandleMessage(
        chat_id: str, sender_id: str, message_id: str, text: str
    ) -> None:
        """Receive user message -> LLM generates card JSON -> lark-cli sends."""
        logger.info("Handling message from %s: %s", sender_id, text[:80])
        try:
            # LLM generates the full lark-card JSON.
            raw_output = await llm.GenerateCardJson(chat_id, text)
            card_json_str = ExtractJson(raw_output)

            # Validate and re-serialize JSON.
            try:
                card_obj = json.loads(card_json_str)
                clean_json = json.dumps(card_obj, ensure_ascii=False)
            except json.JSONDecodeError as e:
                logger.warning(
                    "JSON parse failed (error: %s), trying raw send.\n"
                    "First 300 chars: %s",
                    e,
                    card_json_str[:300],
                )
                # Still try to send the extracted string directly —
                # lark-cli may accept it even if Python's parser rejects it.
                clean_json = card_json_str

            logger.info(
                "Sending card JSON (%d chars) via lark-cli", len(clean_json)
            )
            ok = await bot.SendRawCard(chat_id, clean_json)
            if not ok:
                logger.warning("SendRawCard failed, sending error notice")
                await bot.SendCard(
                    chat_id,
                    "卡片发送失败，请重试。",
                    template="orange",
                    title="发送失败",
                )

        except Exception:
            logger.exception("Error handling message")
            try:
                await bot.SendCard(
                    chat_id,
                    "Sorry, something went wrong. Please try again.",
                    template="red",
                    title="Error",
                )
            except Exception:
                pass

    bot.SetMessageHandler(HandleMessage)
    await bot.Start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info("Agent is running. Press Ctrl+C to stop.")
    await stop_event.wait()
    await bot.Stop()
    logger.info("Agent stopped.")


if __name__ == "__main__":
    asyncio.run(Main())
