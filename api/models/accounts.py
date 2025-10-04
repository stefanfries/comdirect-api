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

from pydantic import BaseModel
from pydantic_extra_types.currency_code import ISO4217


class Paging(BaseModel):
    """Paging information for paginated responses."""

    index: int
    matches: int


class AccountType(BaseModel):
    """Type of the account."""

    key: str
    text: str


class CreditLimit(BaseModel):
    """Credit limit information."""

    value: Decimal
    unit: ISO4217


class Account(BaseModel):
    """Information about a Comdirect bank account."""

    accountId: str
    accountDisplayId: str
    currency: str
    clientId: str
    accountType: AccountType
    iban: str
    bic: str
    creditLimit: CreditLimit


class Balance(BaseModel):
    """Information about a bank account balance."""

    value: Decimal
    unit: ISO4217


class BalanceEUR(BaseModel):
    """Information about a bank account balance in EUR."""

    value: Decimal
    unit: ISO4217 = ISO4217("EUR")


class AvailableCashAmount(BaseModel):
    """Information about the available cash amount."""

    value: Decimal
    unit: ISO4217


class AvailableCashAmountEUR(BaseModel):
    """Information about the available cash amount in EUR."""

    value: Decimal
    unit: ISO4217 = ISO4217("EUR")


class AccountBalance(BaseModel):
    """A single account balance entry."""

    account: Account
    accountId: str
    balance: Balance
    balanceEUR: BalanceEUR
    availableCashAmount: AvailableCashAmount
    availableCashAmountEUR: AvailableCashAmountEUR


class AccountBalances(BaseModel):
    """Account balances response model."""

    paging: Paging
    values: list[AccountBalance]
