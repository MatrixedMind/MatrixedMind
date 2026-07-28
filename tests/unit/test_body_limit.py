import asyncio
from collections.abc import Iterator
from typing import Any

from starlette.requests import Request

from app.main import buffer_limited_request_body


def make_request(chunks: list[bytes]) -> tuple[Request, list[int]]:
    messages: Iterator[dict[str, Any]] = iter(
        [
            {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(chunks) - 1,
            }
            for index, chunk in enumerate(chunks)
        ]
    )
    receive_calls: list[int] = []

    async def receive() -> dict[str, Any]:
        receive_calls.append(1)
        return next(messages)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/llm/records/upsert",
            "headers": [],
        },
        receive,
    )
    return request, receive_calls


def test_bounded_body_reader_stops_when_stream_crosses_limit() -> None:
    request, receive_calls = make_request([b"1234", b"5678", b"unread"])

    assert asyncio.run(buffer_limited_request_body(request, limit=6)) is False
    assert len(receive_calls) == 2


def test_bounded_body_reader_replays_an_allowed_body() -> None:
    request, receive_calls = make_request([b"1234", b"56"])

    assert asyncio.run(buffer_limited_request_body(request, limit=6)) is True
    assert len(receive_calls) == 2
    assert asyncio.run(request.body()) == b"123456"
