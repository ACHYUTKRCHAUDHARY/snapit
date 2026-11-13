"""Contract tests for the WhatsApp outbound adapter."""

import json

import httpx
import pytest
from pydantic import SecretStr

from snappe.adapters.whatsapp import (
    FakeWhatsAppSender,
    MetaWhatsAppSender,
    create_whatsapp_sender,
)
from snappe.application.orchestration import MessageSendError
from snappe.config import Settings

# ---------------------------------------------------------------------------
# FakeWhatsAppSender
# ---------------------------------------------------------------------------


def test_fake_sender_records_sent_messages() -> None:
    sender = FakeWhatsAppSender()
    sender.send_reply("+919876543210", "Hello!")
    sender.send_reply("+919876543211", "Hi there!")

    assert sender.sent == [
        ("+919876543210", "Hello!"),
        ("+919876543211", "Hi there!"),
    ]


def test_fake_sender_raises_configured_error() -> None:
    sender = FakeWhatsAppSender(raise_error=MessageSendError("offline"))

    with pytest.raises(MessageSendError, match="offline"):
        sender.send_reply("+91999", "test")

    assert sender.sent == []  # nothing recorded when error is raised


# ---------------------------------------------------------------------------
# MetaWhatsAppSender — httpx transport stubs
# ---------------------------------------------------------------------------


def _make_meta_sender(transport: httpx.MockTransport) -> MetaWhatsAppSender:
    return MetaWhatsAppSender(
        phone_number_id="123456789",
        access_token="test-access-token",  # noqa: S106
        http_client=httpx.Client(transport=transport),
    )


def test_meta_sender_happy_path() -> None:
    """A 200 OK from the Meta API means the message was accepted."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"messages": [{"id": "wamid.test123"}]},
        )

    sender = _make_meta_sender(httpx.MockTransport(handler))
    sender.send_reply("+919876543210", "Hello from Snappe!")

    assert len(captured) == 1
    req = captured[0]
    assert "123456789/messages" in str(req.url)
    assert req.headers["Authorization"] == "Bearer test-access-token"
    body = json.loads(req.content)
    assert body["to"] == "+919876543210"
    assert body["text"]["body"] == "Hello from Snappe!"
    assert body["messaging_product"] == "whatsapp"


def test_meta_sender_raises_on_4xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "Invalid parameter"}})

    sender = _make_meta_sender(httpx.MockTransport(handler))

    with pytest.raises(MessageSendError, match="400"):
        sender.send_reply("+919999", "hi")


def test_meta_sender_raises_on_5xx() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    sender = _make_meta_sender(httpx.MockTransport(handler))

    with pytest.raises(MessageSendError, match="503"):
        sender.send_reply("+919999", "hi")


def test_meta_sender_raises_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    sender = _make_meta_sender(httpx.MockTransport(handler))

    with pytest.raises(MessageSendError, match="network error"):
        sender.send_reply("+919999", "hi")


def test_meta_sender_raises_on_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out")

    sender = _make_meta_sender(httpx.MockTransport(handler))

    with pytest.raises(MessageSendError):
        sender.send_reply("+919999", "hi")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_factory_returns_fake_when_unconfigured() -> None:
    settings = Settings(_env_file=None)
    sender = create_whatsapp_sender(settings)
    assert isinstance(sender, FakeWhatsAppSender)


def test_factory_returns_real_when_configured() -> None:
    settings = Settings(
        _env_file=None,
        meta_phone_number_id="123",
        meta_access_token=SecretStr("tok"),
    )
    sender = create_whatsapp_sender(settings)
    assert isinstance(sender, MetaWhatsAppSender)
