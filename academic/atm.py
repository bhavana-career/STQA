"""Exercise 4: ATM Withdrawal Black-Box Model.

Models bank account balance, per-transaction limits, daily withdrawal limits,
multiples-of-100 rule, and PIN attempt lockout.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class ATMError(Exception):
    """Base exception for ATM withdrawal failures."""
    pass


class InvalidPINError(ATMError):
    """Raised on incorrect PIN entry."""
    pass


class CardLockedError(ATMError):
    """Raised when card has been locked after maximum consecutive invalid attempts."""
    pass


class InsufficientFundsError(ATMError):
    """Raised when requested amount exceeds account balance."""
    pass


class DailyLimitExceededError(ATMError):
    """Raised when withdrawal would exceed 24-hour daily limit."""
    pass


class InvalidAmountError(ATMError):
    """Raised when withdrawal amount is not a positive multiple of 100 or violates txn bounds."""
    pass


@dataclass
class Account:
    account_number: str
    pin: str
    balance: int
    daily_withdrawn: int = 0
    failed_pin_attempts: int = 0
    is_locked: bool = False


class ATMController:
    """Controls ATM operations, limits, and PIN verification."""

    MIN_TXN_AMOUNT: int = 100
    MAX_TXN_AMOUNT: int = 10000
    DAILY_LIMIT: int = 20000
    MAX_PIN_ATTEMPTS: int = 3

    def __init__(self, account: Account) -> None:
        self.account = account

    def verify_pin(self, entered_pin: str) -> bool:
        """Verify entered PIN with lockout protection."""
        if self.account.is_locked:
            raise CardLockedError("Account is locked due to too many failed PIN attempts.")

        if entered_pin == self.account.pin:
            self.account.failed_pin_attempts = 0
            return True

        self.account.failed_pin_attempts += 1
        if self.account.failed_pin_attempts >= self.MAX_PIN_ATTEMPTS:
            self.account.is_locked = True
            raise CardLockedError("Card locked: 3 consecutive failed PIN attempts.")
        raise InvalidPINError(
            f"Invalid PIN. Remaining attempts: {self.MAX_PIN_ATTEMPTS - self.account.failed_pin_attempts}"
        )

    def withdraw(self, amount: int, entered_pin: str) -> int:
        """Process ATM withdrawal with full validation of PIN, bounds, balance, and limits.

        Returns:
            int: New account balance upon successful withdrawal.
        """
        # 1. Verify PIN
        self.verify_pin(entered_pin)

        # 2. Check amount validity
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise InvalidAmountError("Withdrawal amount must be a whole integer.")

        if amount < self.MIN_TXN_AMOUNT:
            raise InvalidAmountError(f"Minimum withdrawal amount is Rs. {self.MIN_TXN_AMOUNT}.")

        if amount > self.MAX_TXN_AMOUNT:
            raise InvalidAmountError(f"Maximum withdrawal per transaction is Rs. {self.MAX_TXN_AMOUNT}.")

        if amount % 100 != 0:
            raise InvalidAmountError("Withdrawal amount must be in multiples of Rs. 100.")

        # 3. Check account balance
        if amount > self.account.balance:
            raise InsufficientFundsError(
                f"Insufficient balance: requested Rs. {amount}, available Rs. {self.account.balance}."
            )

        # 4. Check daily limit
        if self.account.daily_withdrawn + amount > self.DAILY_LIMIT:
            remaining = self.DAILY_LIMIT - self.account.daily_withdrawn
            raise DailyLimitExceededError(
                f"Daily limit exceeded. Remaining daily allowance: Rs. {remaining}."
            )

        # 5. Execute transaction atomically
        self.account.balance -= amount
        self.account.daily_withdrawn += amount
        return self.account.balance
