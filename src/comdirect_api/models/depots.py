from __future__ import annotations

from decimal import Decimal

from .base import ComdirectBaseModel
from .instruments import Instrument


class Paging(ComdirectBaseModel):
    """Paging information for paginated responses."""

    index: int
    matches: int


class Depot(ComdirectBaseModel):
    """
    Represents a financial depot/account with associated metadata.
    Attributes:
        depot_id (str): Unique identifier for the depot.
        depot_display_id (str): Display identifier for the depot.
        client_id (str): Identifier for the client who owns the depot.
        depot_type (str): Type/category of the depot.
        default_settlement_account_id (str): ID of the default settlement account.
        settlement_account_ids (List[str]): List of settlement account IDs linked to the depot.
        target_market (str): Target market associated with the depot.
    """

    depot_id: str
    depot_display_id: str
    client_id: str
    depot_type: str
    default_settlement_account_id: str
    settlement_account_ids: list[str]
    target_market: str


class AccountDepots(ComdirectBaseModel):
    """
    Represents a collection of depots with pagination information.
    Attributes:
        paging (Paging): Pagination details for the depots list.
        account_depots (List[Depot]): List of depot objects.
    """

    paging: Paging
    values: list[Depot]


class Price(ComdirectBaseModel):
    """Price information."""

    price: dict | None = None  # AmountValue
    price_datetime: str | None = None


class DepotPosition(ComdirectBaseModel):
    """Securities position in a depot."""

    depot_id: str | None = None
    position_id: str | None = None
    wkn: str | None = None
    custody_type: str | None = None
    quantity: dict | None = None  # AmountValue
    available_quantity: dict | None = None  # AmountValue
    current_price: Price | None = None
    purchase_price: dict | None = None  # AmountValue
    prev_day_price: Price | None = None
    current_value: dict | None = None  # AmountValue
    purchase_value: dict | None = None  # AmountValue
    prev_day_value: dict | None = None  # AmountValue
    profit_loss_purchase_abs: dict | None = None  # AmountValue
    profit_loss_purchase_rel: Decimal | None = None  # PercentageString
    profit_loss_prev_day_abs: dict | None = None  # AmountValue
    profit_loss_prev_day_rel: Decimal | None = None  # PercentageString
    instrument: Instrument | None = None
    version: str | None = None


class DepotPositions(ComdirectBaseModel):
    """List of depot positions."""

    paging: dict
    values: list[DepotPosition]
    aggregated: dict | None = None
