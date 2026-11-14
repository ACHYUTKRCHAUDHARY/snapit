"""Interactive WhatsApp message models (Quick Reply buttons and List messages)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, Literal

MAX_BUTTONS: Final[int] = 3
MAX_BUTTON_TITLE_LENGTH: Final[int] = 20
MAX_LIST_SECTIONS: Final[int] = 10
MAX_LIST_ROWS: Final[int] = 10


@dataclass(frozen=True)
class QuickReplyButton:
    """An interactive quick reply button."""

    button_id: str
    title: str

    def __post_init__(self) -> None:
        if not self.button_id.strip():
            raise ValueError("button_id cannot be empty")
        if not self.title.strip():
            raise ValueError("title cannot be empty")
        if len(self.title) > MAX_BUTTON_TITLE_LENGTH:
            raise ValueError(f"title exceeds maximum length of {MAX_BUTTON_TITLE_LENGTH}")


@dataclass(frozen=True)
class ListRow:
    """A row inside a list section."""

    row_id: str
    title: str
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.row_id.strip():
            raise ValueError("row_id cannot be empty")
        if not self.title.strip():
            raise ValueError("title cannot be empty")


@dataclass(frozen=True)
class ListSection:
    """A section of rows inside an interactive list."""

    title: str
    rows: Sequence[ListRow]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("section title cannot be empty")
        if not self.rows:
            raise ValueError("section must contain at least one row")


@dataclass(frozen=True)
class InteractiveMessage:
    """Interactive message payload for WhatsApp."""

    type: Literal["button", "list"]
    body_text: str
    buttons: Sequence[QuickReplyButton] = ()
    button_text: str | None = None  # CTA text for list button
    sections: Sequence[ListSection] = ()

    def __post_init__(self) -> None:
        if not self.body_text.strip():
            raise ValueError("body_text cannot be empty")
        if self.type == "button":
            if not self.buttons or len(self.buttons) > MAX_BUTTONS:
                raise ValueError(f"button interactive message requires 1 to {MAX_BUTTONS} buttons")
        elif self.type == "list":
            if not self.button_text or not self.button_text.strip():
                raise ValueError("list interactive message requires button_text")
            if not self.sections or len(self.sections) > MAX_LIST_SECTIONS:
                raise ValueError(
                    f"list interactive message requires 1 to {MAX_LIST_SECTIONS} sections"
                )
            total_rows = sum(len(s.rows) for s in self.sections)
            if total_rows > MAX_LIST_ROWS:
                raise ValueError(
                    f"list interactive message cannot exceed {MAX_LIST_ROWS} total rows"
                )
