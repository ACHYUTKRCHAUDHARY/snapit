"""Tests for domain interactive messages and WhatsApp adapter interactive dispatch."""

import json

import httpx
import pytest

from snappe.adapters.whatsapp import FakeWhatsAppSender, MetaWhatsAppSender
from snappe.application.orchestration import MessageSendError
from snappe.domain.messages import (
    InteractiveMessage,
    ListRow,
    ListSection,
    QuickReplyButton,
)


def test_quick_reply_button_validation() -> None:
    btn = QuickReplyButton(button_id="b1", title="View Hours")
    assert btn.button_id == "b1"
    assert btn.title == "View Hours"

    with pytest.raises(ValueError, match="button_id"):
        QuickReplyButton(button_id="  ", title="Valid")

    with pytest.raises(ValueError, match="title"):
        QuickReplyButton(button_id="b2", title="")

    with pytest.raises(ValueError, match="maximum length"):
        QuickReplyButton(button_id="b3", title="A" * 21)


def test_list_message_validation() -> None:
    row = ListRow(row_id="r1", title="Support", description="Talk to support")
    section = ListSection(title="Help", rows=[row])
    msg = InteractiveMessage(
        type="list",
        body_text="Choose an option",
        button_text="Menu",
        sections=[section],
    )
    assert msg.type == "list"
    assert len(msg.sections) == 1

    with pytest.raises(ValueError, match="button_text"):
        InteractiveMessage(type="list", body_text="Test", sections=[section])


def test_meta_sender_send_interactive_buttons() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.interactive"}]})

    sender = MetaWhatsAppSender(
        phone_number_id="12345",
        access_token="tok",  # noqa: S106
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    msg = InteractiveMessage(
        type="button",
        body_text="How can we help?",
        buttons=[
            QuickReplyButton("btn-1", "Opening Hours"),
            QuickReplyButton("btn-2", "Pricing"),
        ],
    )

    sender.send_interactive("+919876543210", msg)

    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert body["type"] == "interactive"
    assert body["interactive"]["type"] == "button"
    assert len(body["interactive"]["action"]["buttons"]) == 2


def test_meta_sender_send_interactive_list() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.interactive"}]})

    sender = MetaWhatsAppSender(
        phone_number_id="12345",
        access_token="tok",  # noqa: S106
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    msg = InteractiveMessage(
        type="list",
        body_text="Select a service",
        button_text="View Services",
        sections=[
            ListSection(
                title="Repairs",
                rows=[ListRow("rep-1", "Screen Fix"), ListRow("rep-2", "Battery Fix")],
            )
        ],
    )

    sender.send_interactive("+919876543210", msg)

    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert body["type"] == "interactive"
    assert body["interactive"]["type"] == "list"
    assert body["interactive"]["action"]["button"] == "View Services"
    assert len(body["interactive"]["action"]["sections"][0]["rows"]) == 2


def test_fake_sender_interactive() -> None:
    sender = FakeWhatsAppSender()
    msg = InteractiveMessage(
        type="button",
        body_text="Hi",
        buttons=[QuickReplyButton("b1", "Option 1")],
    )
    sender.send_interactive("+9100", msg)
    assert len(sender.interactive_sent) == 1
    assert sender.interactive_sent[0][1] == msg

    sender_err = FakeWhatsAppSender(raise_error=MessageSendError("fail"))
    with pytest.raises(MessageSendError):
        sender_err.send_interactive("+9100", msg)
