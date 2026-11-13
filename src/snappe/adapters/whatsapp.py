"""WhatsApp Cloud API outbound message sender."""

import httpx

from snappe.application.orchestration import MessageSendError, WhatsAppSender
from snappe.config import Settings

_META_API_BASE = "https://graph.facebook.com/v19.0"
_HTTP_OK = 200


class FakeWhatsAppSender:
    """In-memory WhatsApp sender for deterministic tests and offline dev.

    Records every ``(to, text)`` pair sent so tests can assert on outbound
    messages without making live Meta API calls.
    """

    def __init__(self, raise_error: Exception | None = None) -> None:
        self.sent: list[tuple[str, str]] = []
        self.raise_error = raise_error

    def send_reply(self, to: str, text: str) -> None:
        if self.raise_error is not None:
            raise self.raise_error
        self.sent.append((to, text))


class MetaWhatsAppSender:
    """Send WhatsApp text messages via the Meta Cloud API.

    Raises :exc:`~snappe.application.orchestration.MessageSendError` on any
    transient or permanent failure so the caller can decide whether to retry.
    """

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        timeout_seconds: float = 10.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._phone_number_id = phone_number_id
        self._access_token = access_token
        self._timeout = timeout_seconds
        self._client = http_client

    def send_reply(self, to: str, text: str) -> None:
        """POST a text message to the Meta Cloud API messages endpoint."""
        url = f"{_META_API_BASE}/{self._phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        try:
            client = self._client or httpx.Client(timeout=self._timeout)
            try:
                response = client.post(url, json=payload, headers=headers)
            finally:
                if self._client is None:
                    client.close()
        except (httpx.HTTPError, httpx.TimeoutException) as error:
            raise MessageSendError(f"Meta API network error: {error}") from error

        if response.status_code != _HTTP_OK:
            raise MessageSendError(
                f"Meta API returned status {response.status_code}: {response.text}"
            )


def create_whatsapp_sender(settings: Settings) -> WhatsAppSender:
    """Return a real :class:`MetaWhatsAppSender` or a :class:`FakeWhatsAppSender`.

    Uses the real sender when both ``META_PHONE_NUMBER_ID`` and
    ``META_ACCESS_TOKEN`` are configured; falls back to the fake for local
    development and tests.
    """
    if settings.meta_phone_number_id is not None and settings.meta_access_token is not None:
        return MetaWhatsAppSender(
            phone_number_id=settings.meta_phone_number_id,
            access_token=settings.meta_access_token.get_secret_value(),
        )
    return FakeWhatsAppSender()
