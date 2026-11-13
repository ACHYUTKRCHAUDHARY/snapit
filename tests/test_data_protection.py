from datetime import UTC, datetime, timedelta

import pytest

from snappe.application.data_protection import mask_phone, purge_expired


class Store:
    def __init__(self) -> None:
        self.cutoff = None

    def purge_before(self, cutoff: datetime) -> int:
        self.cutoff = cutoff
        return 2


def test_mask_phone_and_retention_boundary() -> None:
    assert mask_phone("+919876543210") == "*********3210"
    now = datetime(2026, 1, 1, tzinfo=UTC)
    store = Store()

    assert purge_expired(store, 7, now) == 2
    assert store.cutoff == now - timedelta(days=7)


def test_retention_rejects_non_positive_period() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        purge_expired(Store(), 0)
