"""Instrument models for Comdirect API."""

from datetime import date
from decimal import Decimal

from pydantic import Field

from .base import ComdirectBaseModel


class Price(ComdirectBaseModel):
    """Price model."""

    price: dict | None = None  # AmountValue
    price_datetime: str | None = None


class StaticData(ComdirectBaseModel):
    """Static instrument data."""

    notation: str | None = None
    currency: str | None = None
    instrument_type: str | None = None


class DerivativeData(ComdirectBaseModel):
    """Derivative-specific data."""

    underlying_instrument: dict | None = None  # Instrument
    underlying_price: Price | None = None
    certificate_type: str | None = None
    rating: dict | None = None
    strike_price: dict | None = None  # AmountValue
    leverage: Decimal | None = None
    multiplier: Decimal | None = None
    expiry_date: date | None = None
    yield_pa: Decimal | None = Field(default=None, alias="yieldPA")
    remaining_term_in_years: Decimal | None = None
    nominal_rate: Decimal | None = None
    warrant_type: str | None = None  # Call, Put
    maturity_date: date | None = None
    interest_payment_date: date | None = None
    # MONTHLY, QUARTERLY, SEMIANNUALLY, ANNUALLY, OTHER
    interest_payment_interval: str | None = None


class FundDistribution(ComdirectBaseModel):
    """Fund distribution data."""

    fund_type: str | None = None
    distribution_status: str | None = None


class Instrument(ComdirectBaseModel):
    """Instrument (security, derivative, etc.) model."""

    instrument_id: str | None = None
    wkn: str | None = None
    isin: str | None = None
    mnemonic: str | None = None
    name: str | None = None
    short_name: str | None = None
    static_data: StaticData | None = None
    order_dimensions: dict | None = None  # Dimensions
    funds_distribution: FundDistribution | None = None
    derivative_data: DerivativeData | None = None


class Instruments(ComdirectBaseModel):
    """List of instruments."""

    paging: dict
    values: list[Instrument]
    aggregated: dict | None = None
