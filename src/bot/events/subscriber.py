from __future__ import annotations

import json
import logging

from google.cloud.pubsub_v1 import SubscriberClient
from google.cloud.pubsub_v1.subscriber.message import Message

from bot.config import SubscriberConfig
from bot.events.rule import EventRule

_LOG = logging.getLogger(__name__)


class EventSubscriber:
    def __init__(self, config: SubscriberConfig, rule: EventRule) -> None:
        self._rule = rule
        self._config = config
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

        self.client.subscribe(self._config.subscription_name, _handle_message).result()
