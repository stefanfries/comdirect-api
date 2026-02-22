"""Base models and utilities for Comdirect API models."""

# Only expose top-level response models that are returned by public client methods
from .accounts import AccountBalances
from .depots import AccountDepots, DepotPosition, DepotPositions
from .instruments import Instruments
from .messages import Documents
from .transactions import AccountTransactions, DepotTransactions

__all__ = [
    # Main response models returned by client methods
    "AccountBalances",      # from get_account_balances()
    "AccountTransactions",  # from get_account_transactions()
    "AccountDepots",        # from get_account_depots()
    "DepotPositions",       # from get_depot_positions()
    "DepotPosition",        # from get_depot_position()
    "DepotTransactions",    # from get_depot_transactions()
    "Instruments",          # from get_instrument()
    "Documents",            # from get_documents()
]

