from __future__ import annotations

from dataclasses import dataclass

from bs_state import StateStorage
from bs_state.implementation import config_map_storage
from pydantic import BaseModel

from bot import rules
from bot.config import Config


@dataclass
class RuleState[S: BaseModel]:
    rule: rules.Rule[S | None]
    state_storage: StateStorage[S] | None

    @classmethod
    async def load(
        cls,
        rule: rules.Rule[S | None],
        config: Config,
    ) -> RuleState[S] | None:
        storage = await _load_state_storage(config, rule)
        return cls(rule, storage)


async def _load_state_storage[S: BaseModel](
    config: Config,
    rule: rules.Rule[S | None],
) -> StateStorage[S] | None:
    initial_state = rule.initial_state()
    if initial_state is None:
        return None

    state_config = config.state
    if state_config is None:
        from bs_state.implementation import memory_storage

        return await memory_storage.load(initial_state=initial_state)
    else:
        name_prefix = state_config.secret_name_prefix
        namespace = state_config.secret_namespace

        name = f"{name_prefix}{rule.name()}"

        return await config_map_storage.load(
            initial_state=initial_state,
            namespace=namespace,
            config_map_name=name,
        )
