import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self, cast

import httpx
import openai
import telegram
from bs_config import Env

from bot.config import load_config_dict_from_yaml
from bot.rules import Rule

_LOG = logging.getLogger(__name__)

type ImageQuality = Literal["low", "medium", "high"]
type ModerationLevel = Literal["low", "auto"]


@dataclass
class _Config:
    enabled_chat_ids: list[int]
    image_quality: ImageQuality
    model_name: str
    moderation: ModerationLevel
    openai_token: str

    @classmethod
    def from_dict(
        cls,
        config_dict: dict,
        secrets_env: Env,
    ) -> Self:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
            image_quality=cast(ImageQuality, config_dict["imageQuality"]),
            model_name=config_dict["modelName"],
            moderation=cast(ModerationLevel, config_dict["moderationLevel"]),
            openai_token=secrets_env.get_string("OPENAI_TOKEN", required=True),
        )

    @classmethod
    def disabled(cls) -> Self:
        return cls(
            enabled_chat_ids=[],
            image_quality="low",
            openai_token="",
            model_name="",
            moderation="auto",
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
        async with httpx.AsyncClient() as http_client:
            async with openai.AsyncClient(
                api_key=self.config.openai_token,
                http_client=http_client,
            ) as ai_client:
                _LOG.info("Generating image with prompt %s", prompt)
                try:
                    ai_response = await ai_client.images.generate(
                        prompt=prompt,
                        model=self.config.model_name,
                        quality=self.config.image_quality,
                        moderation=self.config.moderation,
                        size="1024x1024",
                    )
                except openai.BadRequestError as e:
                    if (
                        e.type == "invalid_request_error"
                        and e.code == "content_policy_violation"
                    ):
                        _LOG.warning("Content policy violation")
                        await bot.send_message(
                            chat_id=chat_id,
                            reply_parameters=telegram.ReplyParameters(
                                message_id=message_id,
                                allow_sending_without_reply=True,
                            ),
                            text="Sorry, OpenAI sagt das sei unangebracht 🤷",
                        )
                    else:
                        _LOG.error("Request failed", exc_info=e)
                        await bot.set_message_reaction(
                            chat_id=chat_id,
                            message_id=message_id,
                            reaction="🤷",
                        )

                    return

                ai_response_data = ai_response.data
                if not ai_response_data:
                    _LOG.error("No data in response %s", ai_response)
                    return

                image = ai_response_data[0]
                image_data = image.b64_json

                if not image_data:
                    _LOG.error("No base64 data in response %s", ai_response)
                    return

                _LOG.info("Sending image as response")
                await bot.send_photo(
                    chat_id=chat_id,
                    reply_parameters=telegram.ReplyParameters(
                        message_id=message_id,
                        allow_sending_without_reply=True,
                    ),
                    photo=base64.b64decode(image_data),
                    write_timeout=60,
                )
