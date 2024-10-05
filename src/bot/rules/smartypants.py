import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

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
        message: dict,
        is_edited: bool,
        state: None,
    ) -> None:
        if chat_id not in self.config.enabled_chat_ids:
            _LOG.debug("Disabled in chat %d", chat_id)
            return

        _LOG.warning("Not implemented yet")
