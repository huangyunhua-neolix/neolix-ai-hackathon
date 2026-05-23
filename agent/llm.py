"""LLM client: calls Anthropic Claude to generate lark-card JSON."""

import logging
from collections import OrderedDict, deque
from typing import AsyncIterator

import anthropic

from agent.card_templates import CARD_TEMPLATES_PROMPT
from agent.config import LlmConfig

logger = logging.getLogger(__name__)

_MAX_HISTORY = 20
_MAX_CONVERSATIONS = 200


class LlmClient:
    """Anthropic Claude client that outputs lark-card JSON."""

    def __init__(self, config: LlmConfig) -> None:
        self.config_ = config
        self.client_ = anthropic.AsyncAnthropic(
            base_url=config.base_url,
            api_key=config.api_key,
        )
        self.histories_: OrderedDict[str, deque[dict]] = OrderedDict()

    def _GetSystemPrompt(self) -> str:
        """Build the full system prompt with card templates."""
        return (
            self.config_.system_prompt
            + "\n\n"
            + CARD_TEMPLATES_PROMPT
        )

    def _GetHistory(self, chat_id: str) -> deque[dict]:
        if chat_id in self.histories_:
            self.histories_.move_to_end(chat_id)
            return self.histories_[chat_id]
        history: deque[dict] = deque(maxlen=_MAX_HISTORY * 2)
        self.histories_[chat_id] = history
        while len(self.histories_) > _MAX_CONVERSATIONS:
            self.histories_.popitem(last=False)
        return history

    async def GenerateCardJson(self, chat_id: str, user_message: str) -> str:
        """Call LLM to generate a lark-card JSON response.

        Returns the full response text (should be a valid JSON string).
        """
        history = self._GetHistory(chat_id)
        history.append({"role": "user", "content": user_message})

        messages = list(history)
        full_response = ""

        try:
            response = await self.client_.messages.create(
                model=self.config_.model,
                max_tokens=self.config_.max_tokens,
                system=self._GetSystemPrompt(),
                messages=messages,
            )
            for block in response.content:
                if block.type == "text":
                    full_response += block.text
        except Exception:
            logger.exception("LLM call error")
            if history and history[-1]["role"] == "user":
                history.pop()
            raise

        history.append({"role": "assistant", "content": full_response})
        return full_response
