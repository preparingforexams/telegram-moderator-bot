import json
import logging
from collections.abc import Awaitable, Callable
from typing import IO, BinaryIO

import httpx

_LOG = logging.getLogger(__name__)

_API_KEY = ""

_session = httpx.AsyncClient()


def initialize(token: str) -> None:
    global _API_KEY
    _API_KEY = token


def _build_url(method: str) -> str:
    return f"https://api.telegram.org/bot{_API_KEY}/{method}"


def _get_actual_body(response: httpx.Response) -> dict | list:
    response.raise_for_status()
    body = response.json()
    if body.get("ok"):
        return body["result"]
    raise ValueError(f"Body was not ok! {json.dumps(body)}")


async def _request_updates(last_update_id: int | None) -> list[dict]:
    body: dict | None = None
    if last_update_id:
        body = {
            "offset": last_update_id + 1,
            "timeout": 10,
        }
    try:
        response = await _session.post(
            _build_url("getUpdates"),
            json=body,
            timeout=15,
        )
        if 500 < response.status_code <= 600:
            _LOG.warning("Received server error response %d", response.status_code)
            return []
    except httpx.RequestError as e:
        _LOG.warning("Got exception during update request", exc_info=e)
        return []

    return _get_actual_body(response)  # type: ignore


async def handle_updates(handler: Callable[[dict], Awaitable[None]]):
    last_update_id: int | None = None
    while True:
        updates = await _request_updates(last_update_id)
        try:
            for update in updates:
                await handler(update)
                last_update_id = update["update_id"]
        except Exception as e:
            _LOG.error("Could not handle update", exc_info=e)


async def send_message(
    chat_id: int, text: str, reply_to_message_id: int | None = None
) -> dict:
    return _get_actual_body(  # type: ignore
        await _session.post(
            _build_url("sendMessage"),
            json={
                "text": text,
                "chat_id": chat_id,
                "reply_to_message_id": reply_to_message_id,
                "allow_sending_without_reply": True,
            },
        )
    )


async def delete_message(message: dict) -> bool:
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    try:
        _get_actual_body(
            await _session.post(
                _build_url("deleteMessage"),
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                },
            )
        )
    except (ValueError, httpx.RequestError, httpx.HTTPStatusError) as e:
        _LOG.error("Could not delete message", exc_info=e)
        return False
    else:
        return True


async def download_file(file_id: str, file: IO[bytes]):
    body: dict = _get_actual_body(  # type: ignore
        await _session.post(
            _build_url("getFile"),
            json={
                "file_id": file_id,
            },
        )
    )

    file_path = body["file_path"]
    url = f"https://api.telegram.org/file/bot{_API_KEY}/{file_path}"
    response = await _session.get(url)
    response.raise_for_status()
    for chunk in response.iter_bytes(chunk_size=8192):
        file.write(chunk)


async def send_image(
    chat_id: int,
    image_file: BinaryIO,
    caption: str | None = None,
    reply_to_message_id: int | None = None,
) -> dict:
    return _get_actual_body(  # type:ignore
        await _session.post(
            _build_url("sendPhoto"),
            files={
                "photo": image_file,
            },
            data={
                "caption": caption,
                "chat_id": chat_id,
                "reply_to_message_id": reply_to_message_id,
            },
        )
    )


async def send_existing_image(
    *,
    chat_id: int,
    file_id: str,
    reply_to_message_id: int | None = None,
) -> dict:
    return _get_actual_body(  # type:ignore
        await _session.post(
            _build_url("sendPhoto"),
            json={
                "chat_id": chat_id,
                "reply_to_message_id": reply_to_message_id,
                "photo": file_id,
            },
        )
    )


async def forward_message(
    to_chat_id: int,
    message: dict,
) -> dict:
    return _get_actual_body(  # type: ignore
        await _session.post(
            _build_url("forwardMessage"),
            json={
                "chat_id": to_chat_id,
                "from_chat_id": message["chat"]["id"],
                "message_id": message["message_id"],
            },
        )
    )
