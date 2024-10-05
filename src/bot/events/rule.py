import abc

import telegram


class EventRule(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        pass

    @abc.abstractmethod
    async def __call__(self, bot: telegram.Bot, event: dict) -> bool:
        pass
