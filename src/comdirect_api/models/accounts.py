"""
This module defines Pydantic models for representing Comdirect bank account information,
including account details, balances, available cash amounts, and pagination for API responses.
Classes:
    Paging: Paging information for paginated responses.
    AccountType: Type of the account.
    CreditLimit: Credit limit information.
    Account: Information about a Comdirect bank account.
    Balance: Information about a bank account balance.
    BalanceEUR: Information about a bank account balance in EUR.
    AvailableCashAmount: Information about the available cash amount.
    AvailableCashAmountEUR: Information about the available cash amount in EUR.
    Value: A single account balance entry.
    AccountBalances: Account balances response model.
"""

from decimal import Decimal

from pydantic import Field
from pydantic_extra_types.currency_code import ISO4217

from . import ComdirectBaseModel


class Paging(ComdirectBaseModel):
    """Paging information for paginated responses."""

    index: int
    matches: int


class AccountType(ComdirectBaseModel):
    """Type of the account."""

    key: str
    text: str


class CreditLimit(ComdirectBaseModel):
    """Credit limit information."""

    value: Decimal
    unit: ISO4217


class Account(ComdirectBaseModel):
    """Information about a Comdirect bank account."""

    account_id: str
    account_display_id: str
    currency: str
    client_id: str
    account_type: AccountType
    iban: str
    bic: str
    credit_limit: CreditLimit


class Balance(ComdirectBaseModel):
    """Information about a bank account balance."""

    value: Decimal
    unit: ISO4217


class BalanceEUR(ComdirectBaseModel):
    """Information about a bank account balance in EUR."""

    value: Decimal
    unit: ISO4217 = ISO4217("EUR")


class AvailableCashAmount(ComdirectBaseModel):
    """Information about the available cash amount."""

    value: Decimal
    unit: ISO4217


class AvailableCashAmountEUR(ComdirectBaseModel):
    """Information about the available cash amount in EUR."""

    value: Decimal
    unit: ISO4217 = ISO4217("EUR")


class AccountBalance(ComdirectBaseModel):
    """A single account balance entry."""

    account: Account
    account_id: str
    balance: Balance
    balance_eur: BalanceEUR = Field(alias="balanceEUR")
    available_cash_amount: AvailableCashAmount
    available_cash_amount_eur: AvailableCashAmountEUR = Field(alias="availableCashAmountEUR")


class AccountBalances(ComdirectBaseModel):
    """Account balances response model."""

    paging: Paging
    values: list[AccountBalance]
