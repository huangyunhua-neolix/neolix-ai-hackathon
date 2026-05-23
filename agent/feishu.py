"""Feishu channel: WebSocket message reception + lark-cli card reply.

Receiving: lark-oapi WebSocket long connection.
Sending: subprocess call to ``lark-cli im +messages-send --msg-type interactive``,
exactly matching the lark-card skill's send behavior.
"""

import asyncio
import json
import logging
import subprocess
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Coroutine

import lark_oapi as lark
import lark_oapi.ws.client as _lark_ws_client

from agent.config import CardConfig, FeishuConfig

logger = logging.getLogger(__name__)

FEISHU_DOMAIN = lark.FEISHU_DOMAIN
LARK_CLI = "/opt/homebrew/lib/node_modules/@larksuite/cli/bin/lark-cli"

# Callback type: (chat_id, sender_id, message_id, text) -> Coroutine
MessageHandler = Callable[[str, str, str, str], Coroutine[Any, Any, None]]


def BuildNotificationCard(
    card_config: CardConfig,
    content: str,
    *,
    title: str = "",
    template: str = "",
    footer: str = "",
) -> str:
    """Build a lark-card notification template card JSON string.

    Exactly matches the lark-card skill's notification template:
        Header (title + template color)
        ├── Markdown (content body)
        ├── Hr
        └── Markdown (grey footer via <text_tag>)
    """
    card_title = title or card_config.title
    card_template = template or card_config.template
    card_footer = footer or card_config.footer

    card = {
        "schema": "2.0",
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": card_title},
            "template": card_template,
        },
        "body": {
            "elements": [
                {"tag": "markdown", "content": content},
                {"tag": "hr"},
                {
                    "tag": "markdown",
                    "content": f"<text_tag color='grey'>{card_footer}</text_tag>",
                },
            ]
        },
    }
    return json.dumps(card, ensure_ascii=False)


class FeishuBot:
    """Feishu bot: WebSocket receive + lark-cli card send."""

    def __init__(
        self, config: FeishuConfig, card_config: CardConfig | None = None
    ) -> None:
        self.config_ = config
        self.card_config_ = card_config or CardConfig()
        self.ws_client_: lark.ws.Client | None = None
        self.ws_thread_: threading.Thread | None = None
        self.running_ = False
        self.loop_: asyncio.AbstractEventLoop | None = None
        self.on_message_: MessageHandler | None = None
        self.processed_ids_: OrderedDict[str, None] = OrderedDict()

    def SetMessageHandler(self, handler: MessageHandler) -> None:
        self.on_message_ = handler

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def Start(self) -> None:
        """Start the Feishu WebSocket long connection."""
        if not self.config_.app_id or not self.config_.app_secret:
            logger.error("Feishu app_id / app_secret not configured")
            return

        self.running_ = True
        self.loop_ = asyncio.get_running_loop()

        event_handler = (
            lark.EventDispatcherHandler.builder(
                self.config_.encrypt_key or "",
                self.config_.verification_token or "",
            )
            .register_p2_im_message_receive_v1(self._OnMessageSync)
            .build()
        )

        self.ws_client_ = lark.ws.Client(
            self.config_.app_id,
            self.config_.app_secret,
            domain=FEISHU_DOMAIN,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO,
        )

        def RunWs():
            ws_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(ws_loop)
            _lark_ws_client.loop = ws_loop
            try:
                while self.running_:
                    try:
                        self.ws_client_.start()
                    except Exception as exc:
                        logger.warning("WebSocket error: %s", exc)
                    if self.running_:
                        time.sleep(5)
            finally:
                ws_loop.close()

        self.ws_thread_ = threading.Thread(target=RunWs, daemon=True)
        self.ws_thread_.start()
        logger.info("Feishu WebSocket started")

    async def Stop(self) -> None:
        self.running_ = False
        logger.info("Feishu bot stopped")

    # ------------------------------------------------------------------
    # Incoming messages
    # ------------------------------------------------------------------

    def _OnMessageSync(self, data: Any) -> None:
        if self.loop_ and self.loop_.is_running():
            asyncio.run_coroutine_threadsafe(self._OnMessage(data), self.loop_)

    async def _OnMessage(self, data: Any) -> None:
        try:
            event = data.event
            message = event.message
            sender = event.sender

            if sender.sender_type == "bot":
                return

            message_id = message.message_id
            sender_id = (
                sender.sender_id.open_id if sender.sender_id else "unknown"
            )
            chat_id = message.chat_id
            chat_type = message.chat_type
            msg_type = message.message_type

            if message_id in self.processed_ids_:
                return
            self.processed_ids_[message_id] = None
            while len(self.processed_ids_) > 1000:
                self.processed_ids_.popitem(last=False)

            if msg_type != "text":
                logger.debug("Ignoring non-text message type: %s", msg_type)
                return

            try:
                content_json = (
                    json.loads(message.content) if message.content else {}
                )
            except json.JSONDecodeError:
                content_json = {}

            text = content_json.get("text", "").strip()
            if not text:
                return

            mentions = getattr(message, "mentions", None)
            if mentions:
                for m in mentions:
                    at_key = getattr(m, "key", "")
                    if at_key:
                        text = text.replace(at_key, "").strip()

            reply_to = chat_id if chat_type == "group" else sender_id

            logger.info(
                "Message from %s in %s: %s", sender_id, reply_to, text[:80]
            )

            if self.on_message_:
                await self.on_message_(reply_to, sender_id, message_id, text)

        except Exception:
            logger.exception("Error processing Feishu message")

    # ------------------------------------------------------------------
    # Sending via lark-cli (matches lark-card skill exactly)
    # ------------------------------------------------------------------

    async def SendCard(
        self,
        chat_id: str,
        content: str,
        *,
        title: str = "",
        template: str = "",
        footer: str = "",
    ) -> bool:
        """Send a lark-card notification template card via lark-cli.

        Uses: lark-cli im +messages-send --msg-type interactive --content '<card JSON>' --as bot
        Exactly the same command the lark-card skill uses.
        """
        card_json = BuildNotificationCard(
            self.card_config_,
            content,
            title=title,
            template=template,
            footer=footer,
        )

        if chat_id.startswith("oc_"):
            id_flag = "--chat-id"
        else:
            id_flag = "--user-id"

        cmd = [
            LARK_CLI,
            "im",
            "+messages-send",
            id_flag,
            chat_id,
            "--msg-type",
            "interactive",
            "--content",
            card_json,
            "--as",
            "bot",
        ]

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._RunLarkCli, cmd)
        return result

    async def SendRawCard(self, chat_id: str, card_json: str) -> bool:
        """Send a raw card JSON string via lark-cli.

        The JSON is passed directly as --content, no wrapping.
        This is for LLM-generated card JSON that already follows a template.
        """
        if chat_id.startswith("oc_"):
            id_flag = "--chat-id"
        else:
            id_flag = "--user-id"

        cmd = [
            LARK_CLI,
            "im",
            "+messages-send",
            id_flag,
            chat_id,
            "--msg-type",
            "interactive",
            "--content",
            card_json,
            "--as",
            "bot",
        ]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._RunLarkCli, cmd)

    def _RunLarkCli(self, cmd: list[str]) -> bool:
        """Execute a lark-cli command synchronously."""
        try:
            logger.info("lark-cli: %s", " ".join(cmd[:6]) + " ...")
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                logger.error(
                    "lark-cli failed (rc=%d): %s",
                    proc.returncode,
                    proc.stderr.strip(),
                )
                return False
            logger.info("lark-cli ok: %s", proc.stdout.strip()[:200])
            return True
        except subprocess.TimeoutExpired:
            logger.error("lark-cli timed out")
            return False
        except Exception:
            logger.exception("lark-cli error")
            return False
