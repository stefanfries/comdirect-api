"""Base models and utilities for Comdirect API models."""

import re

from pydantic import BaseModel, ConfigDict

from .messages import Document, DocumentMetadata, Documents


def to_camel(s: str) -> str:
    """
    Convert snake_case to camelCase.

    Examples:
        account_id -> accountId
        account_display_id -> accountDisplayId
    """
    return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), s)


class ComdirectBaseModel(BaseModel):
    """
    Base model for all Comdirect API models.

    Automatically converts Python snake_case field names to API camelCase.
    Also accepts both formats when parsing (populate_by_name=True).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
