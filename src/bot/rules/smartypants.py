import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self, cast

import httpx
import openai
import telegram
from bs_config import Env

from bot.config import load_config_dict_from_yaml
from bot.rules import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _Config:
    enabled_chat_ids: list[int]
    openai_token: str

    @classmethod
    def from_dict(
        cls,
        config_dict: dict,
        secrets_env: Env,
    ) -> Self:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
            openai_token=secrets_env.get_string("OPENAI_TOKEN", required=True),
        )

    @classmethod
    def disabled(cls) -> Self:
        return cls(
            enabled_chat_ids=[],
            openai_token="",
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

        if not text.startswith("/draw"):
            _LOG.debug("Ignoring non-draw message")
            return

        message_parts = text.split(" ", maxsplit=1)
        if len(message_parts) < 2:
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
        async with httpx.AsyncClient() as http_client:
            async with openai.AsyncClient(
                api_key=self.config.openai_token,
                http_client=http_client,
            ) as ai_client:
                _LOG.info("Generating image with prompt %s", prompt)
                ai_response = await ai_client.images.generate(
                    prompt=prompt,
                    model="dall-e-3",
                    n=1,
                    quality="hd",
                    response_format="url",
                    size="1024x1024",
                )

                image = ai_response.data[0]
                image_url = cast(str, image.url)

                _LOG.info("Downloading generated image")
                download_response = await http_client.get(
                    url=image_url,
                )

                if not download_response.is_success:
                    _LOG.error(
                        "Could not download OpenAI image (response code %d)",
                        download_response.status_code,
                    )
                    return

                _LOG.info("Sending image as response")
                await bot.send_photo(
                    chat_id=chat_id,
                    reply_parameters=telegram.ReplyParameters(
                        message_id=message_id,
                        allow_sending_without_reply=True,
                    ),
                    photo=download_response.content,
                )
