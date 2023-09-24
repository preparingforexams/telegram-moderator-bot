from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from google.cloud.pubsub_v1 import SubscriberClient
from google.cloud.pubsub_v1.subscriber.message import Message

from bot.events.rule import EventRule

_LOG = logging.getLogger(__name__)


@dataclass
class SubscriberConfig:
    subscription: str

    @classmethod
    def from_env(cls) -> SubscriberConfig:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        simple_sub_name = os.getenv("GOOGLE_PUBSUB_SUBSCRIPTION")

        if not project_id or not simple_sub_name:
            raise ValueError("Missing project_id or subscription name")

        sub_name = f"projects/{project_id}/subscriptions/{simple_sub_name}"

        return cls(
            subscription=sub_name,
        )


class EventSubscriber:
    def __init__(self, rule: EventRule):
        self._rule = rule
        self._config = SubscriberConfig.from_env()
        self.client = SubscriberClient()

    def subscribe(self):
        def _handle_message(message: Message):
            _LOG.debug("Received a Pub/Sub message")
            try:
                decoded = json.loads(message.data.decode("utf-8"))
            except Exception as e:
                _LOG.error("Could not decode message", exc_info=e)
                message.ack_with_response().result()
                return

            try:
                result = self._rule(decoded)
            except Exception as e:
                _LOG.error("Rule failed to handle message, requeuing", exc_info=e)
                message.nack_with_response().result()
            else:
                if result:
                    message.ack_with_response().result()
                else:
                    _LOG.warning("Rule result indicated failure, requeuing")
                    message.nack_with_response().result()

        self.client.subscribe(self._config.subscription, _handle_message).result()
