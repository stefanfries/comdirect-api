from __future__ import annotations

from typing import List

from pydantic import BaseModel


class Paging(BaseModel):
    """Paging information for paginated responses."""

    index: int
    matches: int


class Depot(BaseModel):
    """
    Represents a financial depot/account with associated metadata.
    Attributes:
        depotId (str): Unique identifier for the depot.
        depotDisplayId (str): Display identifier for the depot.
        clientId (str): Identifier for the client who owns the depot.
        depotType (str): Type/category of the depot.
        defaultSettlementAccountId (str): ID of the default settlement account.
        settlementAccountIds (List[str]): List of settlement account IDs linked to the depot.
        targetMarket (str): Target market associated with the depot.
    """

    depotId: str
    depotDisplayId: str
    clientId: str
    depotType: str
    defaultSettlementAccountId: str
    settlementAccountIds: List[str]
    targetMarket: str


class AccountDepots(BaseModel):
    """
    Represents a collection of depots with pagination information.
    Attributes:
        paging (Paging): Pagination details for the depots list.
        account_depots (List[Depot]): List of depot objects.
    """

    paging: Paging
    values: List[Depot]
