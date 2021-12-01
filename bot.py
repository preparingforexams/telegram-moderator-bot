import json
import logging
import os
import re
import sys
from typing import Optional, List, Union

import requests
import sentry_sdk
from requests.exceptions import HTTPError

_ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
_API_KEY = os.getenv("TELEGRAM_API_KEY")

_LOG = logging.getLogger("bot")


def _build_url(method: str) -> str:
    return f"https://api.telegram.org/bot{_API_KEY}/{method}"


def _get_actual_body(response: requests.Response) -> Union[dict, list]:
    response.raise_for_status()
    body = response.json()
    if body.get("ok"):
        return body["result"]
    raise ValueError(f"Body was not ok! {json.dumps(body)}")


def _send_message(chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> dict:
    return _get_actual_body(requests.post(
        _build_url("sendMessage"),
        json={
            "text": text,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
        },
        timeout=10,
    ))


def _delete_message(message: dict):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    try:
        _get_actual_body(requests.post(
            _build_url("deleteMessage"),
            json={
                "chat_id": chat_id,
                "message_id": message_id,
            },
            timeout=10,
        ))
    except (ValueError, HTTPError) as e:
        _LOG.error("Could not delete message", exc_info=e)
        return


def _is_plain_command(text: str) -> bool:
    pattern = re.compile(r"/\w+")
    return bool(pattern.fullmatch(text))


def _handle_message(message: dict) -> None:
    text: Optional[str] = message.get("text")

    if text:
        if _is_plain_command(text):
            _delete_message(message)
    else:
        _LOG.debug("Skipping message: %s", json.dumps(message))


def _handle_update(update: dict):
    message = update.get("message")

    if not message:
        _LOG.debug("Skipping non-message update")
        return

    _handle_message(message)


def _request_updates(last_update_id: Optional[int]) -> List[dict]:
    body: Optional[dict] = None
    if last_update_id:
        body = {
            "offset": last_update_id + 1,
            "timeout": 10,
        }
    return _get_actual_body(requests.post(
        _build_url("getUpdates"),
        json=body,
        timeout=15,
    ))


def _handle_updates():
    last_update_id: Optional[int] = None
    while True:
        updates = _request_updates(last_update_id)
        try:
            for update in updates:
                _handle_update(update)
                last_update_id = update["update_id"]
        except Exception as e:
            _LOG.error("Could not handle update", exc_info=e)


def _setup_logging():
    logging.basicConfig()
    _LOG.level = logging.DEBUG


def _setup_sentry():
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        _LOG.warning("Sentry DSN not found")
        return

    version = os.getenv("BUILD_SHA", "dirty")

    sentry_sdk.init(
        dsn,

        release=version,

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0
    )


def main():
    _setup_logging()
    _setup_sentry()

    if not _API_KEY:
        _LOG.error("Missing API key")
        sys.exit(1)

    _handle_updates()


if __name__ == '__main__':
    main()
