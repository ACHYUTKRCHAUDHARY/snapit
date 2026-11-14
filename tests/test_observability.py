"""Tests for conversation observability and Prometheus metric collection."""

from fastapi.testclient import TestClient

from snappe.application.observability import (
    HANDOVER_EVENTS_TOTAL,
    INBOUND_MESSAGES_TOTAL,
    OUTBOUND_REPLIES_TOTAL,
    record_handover,
    record_inbound_message,
    record_outbound_reply,
)
from snappe.config import Settings
from snappe.main import create_full_app


def test_observability_helper_functions() -> None:
    # Ensure manual recording functions increment labels without crashing
    record_inbound_message("biz-obs-1", "text")
    record_outbound_reply("biz-obs-1", delivered=True)
    record_handover("biz-obs-1", "guardrail decision")

    assert (
        INBOUND_MESSAGES_TOTAL.labels(business_id="biz-obs-1", message_type="text")._value.get()
        >= 1
    )
    assert (
        OUTBOUND_REPLIES_TOTAL.labels(business_id="biz-obs-1", delivered="true")._value.get() >= 1
    )
    assert (
        HANDOVER_EVENTS_TOTAL.labels(
            business_id="biz-obs-1", reason="guardrail decision"
        )._value.get()
        >= 1
    )


def test_metrics_endpoint_exports_prometheus_format() -> None:
    app = create_full_app(Settings(_env_file=None))
    client = TestClient(app)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text
    assert "snappe_inbound_messages_total" in text
    assert "snappe_outbound_replies_total" in text
    assert "snappe_handover_events_total" in text
    assert "snappe_message_processing_duration_seconds" in text
