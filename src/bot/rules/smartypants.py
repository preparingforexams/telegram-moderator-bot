import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

import telegram
from replicate import Client as ReplicateClient
from replicate.exceptions import ReplicateException
from replicate.helpers import FileOutput

from bot.rules import Rule

if TYPE_CHECKING:
    from bs_config import Env

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class _Config:
    enabled_chat_ids: list[int]
    model_name: str
    openai_token: str
    replicate_token: str

    @classmethod
    def from_env(
        cls,
        env: Env,
    ) -> Self:
        enabled_chat_ids = env.get_int_list("enabled-chats", default=[])
        is_enabled = bool(enabled_chat_ids)
        return cls(
            enabled_chat_ids=enabled_chat_ids,
            model_name=env.get_string("model-name", required=is_enabled) or "",
            openai_token=env.get_string("openai-token", required=is_enabled) or "",
            replicate_token=env.get_string("replicate-token", required=is_enabled)
            or "",
        )


class SmartypantsRule(Rule[None]):
    @classmethod
    def name(cls) -> str:
        return "smartypants"

    def __init__(self, env: Env) -> None:
        self._config = self._load_config(env)

    @staticmethod
    def _load_config(env: Env) -> _Config:
        config = _Config.from_env(env)
        if not config.enabled_chat_ids:
            _LOG.warning("No chats configured")

        return config

    def initial_state(self) -> None:
        pass

    async def __call__(
        self,
        *,
        chat_id: int,
        message: telegram.Message,
        is_edited: bool,
        state: None,
    ) -> None:
        if chat_id not in self._config.enabled_chat_ids:
            _LOG.debug("Disabled in chat %d", chat_id)
            return

        if is_edited:
            _LOG.debug("Ignoring edited message")
            return

        text: str | None = message.text
        if not text:
            _LOG.debug("Ignoring non-text message")
            return

        message_parts = text.split(" ", maxsplit=1)
        if not message_parts[0].lower().startswith("/draw"):
            _LOG.debug("Ignoring non-draw message")
            return
        elif len(message_parts) < 2:
            await message.reply_text(
                text="Usage example: /draw a horse playing a saxophone",
            )
        else:
            await self._draw(
                bot=message.get_bot(),
                chat_id=chat_id,
                prompt=message_parts[1],
                message_id=message.message_id,
            )

    async def _draw(
        self,
        *,
        bot: telegram.Bot,
        chat_id: int,
        message_id: int,
        prompt: str,
    ) -> None:
        ai_client = ReplicateClient(self._config.replicate_token)

        _LOG.info("Generating image with prompt %s", prompt)
        try:
            ai_response = await ai_client.async_run(
                self._config.model_name,
                input=dict(
                    prompt=prompt,
                    aspect_ratio="1:1",
                    openai_api_key=self._config.openai_token,
                    moderation="low",
                    output_format="jpeg",
                ),
                use_file_output=True,
            )
        except ReplicateException as e:
            _LOG.error("Request failed", exc_info=e)
            await bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction="🤷",
            )

            return

        file_output: FileOutput
        if isinstance(ai_response, FileOutput):
            _LOG.info("Response was FileOutput")
            file_output = ai_response
        elif isinstance(ai_response, list):
            _LOG.info("Response was list")
            file_output = ai_response[0]
        elif isinstance(ai_response, AsyncIterator):
            _LOG.info("Response was AsyncIterator")
            async for item in ai_response:
                file_output = item
                break
            else:
                _LOG.error("Received empty response")
                await bot.set_message_reaction(
                    chat_id=chat_id,
                    message_id=message_id,
                    reaction="💊",
                )
                return
        else:
            _LOG.error("Response was %s", type(ai_response))
            return

        _LOG.info("Receiving image")
        image = await file_output.aread()
        _LOG.info("Sending image of size %d as response", len(image))
        await bot.send_photo(
            chat_id=chat_id,
            reply_parameters=telegram.ReplyParameters(
                message_id=message_id,
                allow_sending_without_reply=True,
            ),
            photo=image,
            write_timeout=60,
        )
