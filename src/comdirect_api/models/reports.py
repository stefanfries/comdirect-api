"""
Pydantic models for the Comdirect Reports API (Resource 10).

Covers the /reports/participants/{participantId}/v1/allbalances endpoint which
returns aggregated balances across all comdirect products (accounts, cards,
depots, loans, fixed-term savings).
"""

from decimal import Decimal

from .accounts import AccountBalance, Paging
from .base import AmountValue, ComdirectBaseModel


class BalanceAggregation(ComdirectBaseModel):
    """Aggregated balances across all reported products."""

    balance_eur: AmountValue | None = None
    available_cash_amount_eur: AmountValue | None = None


class VisaCardImage(ComdirectBaseModel):
    """Visa card image/design details."""

    visa_card_image_id: str | None = None
    image_description: str | None = None
    image_base_filename: str | None = None


class Card(ComdirectBaseModel):
    """Visa card static data."""

    card_id: str | None = None
    client_id: str | None = None
    participant_id: str | None = None
    card_type: dict | None = None           # EnumText {key, text}
    holder_name: str | None = None
    settlement_account_id: str | None = None
    card_display_id: str | None = None
    card_validity: str | None = None
    card_image: VisaCardImage | None = None
    primary_account_number_suffix: str | None = None
    card_limit: AmountValue | None = None
    status: str | None = None


class CardBalance(ComdirectBaseModel):
    """Balance information for a Visa card product."""

    card_id: str | None = None
    card: Card | None = None
    balance: AmountValue | None = None
    available_cash_amount: AmountValue | None = None


class InstallmentLoan(ComdirectBaseModel):
    """Installment loan static data."""

    installment_loan_id: str | None = None
    product_display_id: str | None = None
    credit_amount: AmountValue | None = None
    net_credit_amount: AmountValue | None = None
    paid_out_amount: AmountValue | None = None
    installment_amount: AmountValue | None = None
    contract_period_in_months: int | None = None
    effective_interest: Decimal | None = None
    nominal_interest: Decimal | None = None
    contract_conclusion_date: str | None = None


class InstallmentLoanBalance(ComdirectBaseModel):
    """Balance information for an installment loan product."""

    installment_loan_id: str | None = None
    installment_loan: InstallmentLoan | None = None
    balance: AmountValue | None = None


class FixedTermSavings(ComdirectBaseModel):
    """Balance information for a fixed-term savings product."""

    fixed_term_savings_id: str | None = None
    savings_amount: AmountValue | None = None
    interest_rate: AmountValue | None = None
    fixed_term_savings_type: str | None = None
    fixed_term_savings_display_name: str | None = None
    contract_period_in_months: int | None = None
    creation_date: str | None = None
    expiration_date: str | None = None
    prolongation_amount: AmountValue | None = None
    extendable: bool | None = None


class ProductBalance(ComdirectBaseModel):
    """Balance for a single comdirect product (account, card, depot, loan, or savings)."""

    product_id: str | None = None
    product_type: str | None = None         # ACCOUNT, CARD, DEPOT, LOAN, SAVINGS
    target_client_id: str | None = None
    client_connection_type: str | None = None  # CURRENT_CLIENT, OTHER_COMDIRECT
    balance: (
        AccountBalance | CardBalance | InstallmentLoanBalance | FixedTermSavings | dict | None
    ) = None


class AllBalances(ComdirectBaseModel):
    """Response model for GET /reports/participants/user/v1/allbalances."""

    paging: Paging
    aggregated: BalanceAggregation | None = None
    values: list[ProductBalance]
