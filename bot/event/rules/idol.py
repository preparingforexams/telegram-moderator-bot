from bot.event.rule import EventRule


class IdolRule(EventRule):
    name = "idol"

    def __init__(self, config_dir: str):
        pass

    def __call__(self, event: dict) -> bool:
        return False
