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

    # Find the matching closing '}'.
    depth = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
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

            # Validate it's valid JSON.
            try:
                json.loads(card_json_str)
            except json.JSONDecodeError:
                logger.warning(
                    "LLM returned invalid JSON:\n%s", card_json_str[:500]
                )
                # Fallback: wrap raw LLM text in a notification card.
                await bot.SendCard(chat_id, raw_output)
                return

            # Send the card JSON via lark-cli.
            await bot.SendRawCard(chat_id, card_json_str)

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
