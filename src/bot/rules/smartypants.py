import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self, cast

import telegram
from bs_config import Env
from replicate import Client as ReplicateClient
from replicate.exceptions import ReplicateException
from replicate.helpers import FileOutput

from bot.config import load_config_dict_from_yaml
from bot.rules import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _Config:
    enabled_chat_ids: list[int]
    model_name: str
    replicate_token: str

    @classmethod
    def from_dict(
        cls,
        config_dict: dict,
        secrets_env: Env,
    ) -> Self:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
            model_name=config_dict["modelName"],
            replicate_token=secrets_env.get_string("REPLICATE_TOKEN", required=True),
        )

    @classmethod
    def disabled(cls) -> Self:
        return cls(
            enabled_chat_ids=[],
            model_name="",
            replicate_token="",
        )


class SmartypantsRule(Rule[None]):
    @classmethod
    def name(cls) -> str:
        return "smartypants"

    def __init__(self, config_dir: Path, secrets_env: Env):
        self.config = self._load_config(config_dir, secrets_env)

    @staticmethod
    def _load_config(config_dir: Path, secret_envs: Env) -> _Config:
        config_dict = load_config_dict_from_yaml(config_dir / "smartypants.yaml")

        if not config_dict:
            _LOG.warning("Config is empty or missing")
            return _Config.disabled()

        try:
            return _Config.from_dict(config_dict, secret_envs)
        except (KeyError, ValueError) as e:
            _LOG.warning("Invalid or incomplete config", exc_info=e)
            return _Config.disabled()

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
        if chat_id not in self.config.enabled_chat_ids:
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
        ai_client = ReplicateClient(self.config.replicate_token)

        _LOG.info("Generating image with prompt %s", prompt)
        try:
            ai_response = cast(
                FileOutput,
                await ai_client.async_run(
                    self.config.model_name,
                    input=dict(
                        prompt=prompt,
                        aspect_ratio="4:3",
                    ),
                    use_file_output=True,
                ),
            )
        except ReplicateException as e:
            _LOG.error("Request failed", exc_info=e)
            await bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction="🤷",
            )

            return

        image = await ai_response.aread()
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
