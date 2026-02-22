"""Transaction models for Comdirect API."""

from datetime import date, datetime

from . import ComdirectBaseModel


class AccountInformation(ComdirectBaseModel):
    """Account information model (debtor/creditor)."""

    holder_name: str | None = None
    iban: str | None = None
    bic: str | None = None


class EnumText(ComdirectBaseModel):
    """Enum with key and text."""

    key: str
    text: str


class AccountTransaction(ComdirectBaseModel):
    """Account transaction model."""

    reference: str | None = None
    booking_status: str | None = None  # BOOKED, NOTBOOKED
    booking_date: date | None = None
    amount: dict | None = None  # AmountValue
    remitter: AccountInformation | None = None
    deptor: AccountInformation | None = None
    creditor: AccountInformation | None = None
    valuta_date: str | None = None
    direct_debit_creditor_id: str | None = None
    direct_debit_mandate_id: str | None = None
    end_to_end_reference: str | None = None
    new_transaction: bool = False
    remittance_info: str | None = None
    transaction_type: EnumText | None = None


class AccountTransactions(ComdirectBaseModel):
    """List of account transactions."""

    paging: dict
    values: list[AccountTransaction]
    aggregated: dict | None = None


class DepotTransaction(ComdirectBaseModel):
    """Depot transaction model."""

    transaction_id: str | None = None
    booking_status: str | None = None  # BOOKED, NOTBOOKED
    booking_date: date | None = None
    settlement_date: datetime | None = None
    business_date: date | None = None
    quantity: dict | None = None  # AmountValue
    instrument_id: str | None = None
    instrument: dict | None = None  # Instrument (optional)
    execution_price: dict | None = None  # AmountValue
    transaction_value: dict | None = None  # AmountValue
    transaction_direction: str | None = None  # IN, OUT
    transaction_type: str | None = None  # BUY, SELL, TRANSFER_IN, TRANSFER_OUT, OTHER
    fx_rate: dict | None = None  # FXRateEUR


class DepotTransactions(ComdirectBaseModel):
    """List of depot transactions."""

    paging: dict
    values: list[DepotTransaction]
    aggregated: dict | None = None
