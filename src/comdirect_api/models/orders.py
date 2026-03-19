from __future__ import annotations

from decimal import Decimal

from .base import AmountValue, ComdirectBaseModel


class PercentageValue(ComdirectBaseModel):
    """Percentage value as returned by the Comdirect API."""

    pre_decimal_places: str | None = None
    decimal_places: str | None = None
    percent_string: str | None = None


class Execution(ComdirectBaseModel):
    """A single execution (fill) of an order."""

    execution_id: str | None = None
    execution_number: int | None = None
    executed_quantity: AmountValue | None = None
    execution_price: AmountValue | None = None
    execution_timestamp: str | None = None


class Order(ComdirectBaseModel):
    """A brokerage order."""

    depot_id: str | None = None
    settlement_account_id: str | None = None
    order_id: str | None = None
    creation_timestamp: str | None = None
    leg_number: int | None = None
    best_ex: bool | None = None
    order_type: str | None = None
    order_status: str | None = None
    sub_orders: list[Order] | None = None
    side: str | None = None
    instrument_id: str | None = None
    quote_id: str | None = None
    venue_id: str | None = None
    quantity: AmountValue | None = None
    open_quantity: AmountValue | None = None
    cancelled_quantity: AmountValue | None = None
    executed_quantity: AmountValue | None = None
    limit_extension: str | None = None
    trading_restriction: str | None = None
    limit: AmountValue | None = None
    trigger_limit: AmountValue | None = None
    trailing_limit_dist_abs: AmountValue | None = None
    trailing_limit_dist_rel: PercentageValue | None = None
    validity_type: str | None = None
    validity: str | None = None
    expected_value: AmountValue | None = None
    executions: list[Execution] | None = None
    quote_ticket_id: str | None = None
    version: str | None = None


# Required for self-referential model (sub_orders field)
Order.model_rebuild()


class Orders(ComdirectBaseModel):
    """List of orders with pagination."""

    paging: dict | None = None
    aggregated: dict | None = None
    values: list[Order] = []
