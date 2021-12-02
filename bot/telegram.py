import json
import logging
import os
from typing import Optional, Union, List, Callable

import requests
from requests.exceptions import HTTPError

_LOG = logging.getLogger(__name__)

_API_KEY = os.getenv("TELEGRAM_API_KEY")


def is_configured() -> bool:
    return bool(_API_KEY)


def _build_url(method: str) -> str:
    return f"https://api.telegram.org/bot{_API_KEY}/{method}"


def _get_actual_body(response: requests.Response) -> Union[dict, list]:
    response.raise_for_status()
    body = response.json()
    if body.get("ok"):
        return body["result"]
    raise ValueError(f"Body was not ok! {json.dumps(body)}")


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


def handle_updates(handler: Callable[[dict], None]):
    last_update_id: Optional[int] = None
    while True:
        updates = _request_updates(last_update_id)
        try:
            for update in updates:
                handler(update)
                last_update_id = update["update_id"]
        except Exception as e:
            _LOG.error("Could not handle update", exc_info=e)


def send_message(chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> dict:
    return _get_actual_body(requests.post(
        _build_url("sendMessage"),
        json={
            "text": text,
            "chat_id": chat_id,
            "reply_to_message_id": reply_to_message_id,
        },
        timeout=10,
    ))


def delete_message(message: dict) -> bool:
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
        return False
    else:
        return True
