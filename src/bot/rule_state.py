from __future__ import annotations

import logging
from dataclasses import dataclass

from bs_state import StateStorage
from bs_state.implementation import config_map_storage, redis_storage
from pydantic import BaseModel

from bot import rules
from bot.config import Config

_LOG = logging.getLogger(__name__)


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
        _LOG.warning("Using in-memory state storage")
        from bs_state.implementation import memory_storage

        return await memory_storage.load(initial_state=initial_state)
    elif redis_config := state_config.redis:
        _LOG.info("Using Redis state storage")
        key = f"{redis_config.username}:{state_config.secret_name_prefix}:{rule.name()}"

        return await redis_storage.load(
            initial_state=initial_state,
            host=redis_config.host,
            username=redis_config.username,
            password=redis_config.password,
            key=key,
        )
    else:
        _LOG.info("Using Kubernetes state storage")
        name_prefix = state_config.secret_name_prefix
        namespace = state_config.secret_namespace

        name = f"{name_prefix}{rule.name()}"

        return await config_map_storage.load(
            initial_state=initial_state,
            namespace=namespace,
            config_map_name=name,
        )
