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
    unit: str


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
    unit: str


class BalanceEUR(BaseModel):
    """Information about a bank account balance in EUR."""

    value: Decimal
    unit: str


class AvailableCashAmount(BaseModel):
    """Information about the available cash amount."""

    value: Decimal
    unit: str


class AvailableCashAmountEUR(BaseModel):
    """Information about the available cash amount in EUR."""

    value: Decimal
    unit: str


class Value(BaseModel):
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
    values: list[Value]
