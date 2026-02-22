"""
Examples of different logging configurations for the Comdirect API client.
"""

import asyncio
import logging

from comdirect_api.client import ComdirectClient


# Example 1: Basic INFO level logging (default, shows workflow steps)
def example_basic_logging():
    """Shows authentication progress and important events."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


# Example 2: DEBUG level logging (shows detailed API responses and data)
def example_debug_logging():
    """Shows detailed debugging information including API responses."""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


# Example 3: WARNING+ only (minimal output, only errors and warnings)
def example_minimal_logging():
    """Shows only warnings and errors."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
    )


# Example 4: Suppress httpx logs, keep only comdirect_api logs
def example_suppress_httpx():
    """Shows comdirect_api logs but suppresses verbose httpx HTTP request logs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Suppress httpx INFO logs (only show warnings/errors)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# Example 5: Log to file instead of console
def example_file_logging():
    """Logs to a file for later review."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename="comdirect_api.log",
        filemode="a",  # append mode
    )


# Example 6: Both console and file logging
def example_dual_logging():
    """Logs to both console and file simultaneously."""
    import sys

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_format)

    # File handler
    file_handler = logging.FileHandler("comdirect_api.log")
    file_handler.setLevel(logging.DEBUG)  # More detail in file
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


async def main():
    """Example usage with logging."""

    # Choose one of the logging configurations above
    example_suppress_httpx()  # Recommended: cleaner output

    # Use the client
    client = await ComdirectClient.create()
    print(f"\nClient ready! ID: {client.client_id}\n")

    # Get account balances
    balances = await client.get_account_balances()
    print(f"Retrieved {len(balances.values)} accounts")


if __name__ == "__main__":
    asyncio.run(main())
