from __future__ import annotations

from . import ComdirectBaseModel


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
