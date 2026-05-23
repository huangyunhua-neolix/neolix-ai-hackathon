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

def ExtractJson(raw: str) -> dict | None:
    """Extract a valid JSON object from LLM output.

    Tries multiple strategies:
      1. Direct json.loads on stripped text
      2. Strip ```json ... ``` wrapping then parse
      3. Find first '{' ... last '}' and parse that substring

    Returns the parsed dict, or None if extraction fails.
    """
    text = raw.strip()

    # Strategy 1: direct parse.
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: strip ```json ... ``` wrapping.
    code_block_re = re.compile(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL
    )
    match = code_block_re.search(text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: find first '{' to last '}' and parse.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            pass

    return None


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
            logger.info(
                "LLM raw output (%d chars): %s ... %s",
                len(raw_output),
                raw_output[:200],
                raw_output[-100:],
            )

            card_obj = ExtractJson(raw_output)
            if card_obj is None:
                logger.error(
                    "Failed to extract JSON from LLM output (%d chars)",
                    len(raw_output),
                )
                await bot.SendCard(
                    chat_id,
                    "无法解析 AI 返回的卡片数据，请重试。",
                    template="orange",
                    title="解析失败",
                )
                return

            clean_json = json.dumps(card_obj, ensure_ascii=False)
            logger.info("Sending card JSON (%d chars)", len(clean_json))

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
