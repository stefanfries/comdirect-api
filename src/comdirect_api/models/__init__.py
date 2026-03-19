"""Base models and utilities for Comdirect API models."""

# Only expose top-level response models that are returned by public client methods
from .accounts import AccountBalance, AccountBalances
from .base import AmountValue
from .depots import AccountDepots, DepotPosition, DepotPositions
from .instruments import Instruments
from .messages import Documents
from .orders import Order, Orders
from .reports import AllBalances
from .transactions import AccountTransactions, DepotTransactions

__all__ = [
    # Shared value type used in response fields
    "AmountValue",          # monetary / quantity value with unit
    # Main response models returned by client methods
    "AccountBalance",       # from get_account_balance()
    "AccountBalances",      # from get_account_balances()
    "AccountTransactions",  # from get_account_transactions()
    "AccountDepots",        # from get_account_depots()
    "DepotPositions",       # from get_depot_positions()
    "DepotPosition",        # from get_depot_position()
    "DepotTransactions",    # from get_depot_transactions()
    "Instruments",          # from get_instrument()
    "Documents",            # from get_documents()
    "AllBalances",          # from get_all_balances()
    "Orders",               # from get_depot_orders()
    "Order",                # from get_order()
]

