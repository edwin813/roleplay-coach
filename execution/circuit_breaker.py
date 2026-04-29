"""
Circuit breaker pattern to prevent cascading failures when API is consistently down.

A circuit breaker prevents overwhelming a failing service by "opening" the circuit
after a threshold of failures, rejecting requests until the service has time to recover.
"""
import time
import logging
from enum import Enum
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"       # Normal operation, requests allowed
    OPEN = "open"           # Too many failures, reject all requests
    HALF_OPEN = "half_open" # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent overwhelming a failing API.

    States:
    - CLOSED: Normal operation, all requests go through
    - OPEN: Too many failures detected, reject all requests immediately
    - HALF_OPEN: After recovery timeout, allow limited requests to test if service recovered

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        >>> def api_call():
        ...     return client.messages.create(...)
        >>> result = breaker.call(api_call)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit (default: 5)
            recovery_timeout: Seconds to wait before attempting recovery (default: 60.0)
            success_threshold: Consecutive successes needed to close circuit from half-open (default: 2)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

        logger.info(f"🔌 Circuit breaker initialized (threshold={failure_threshold}, timeout={recovery_timeout}s)")

    def call(self, func: Callable[..., T]) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute (should be a callable with no arguments)

        Returns:
            Result of function execution

        Raises:
            Exception: If circuit is OPEN or if function raises exception
        """
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"🔄 Circuit breaker transitioning to HALF_OPEN (testing recovery)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                time_remaining = self.recovery_timeout - (time.time() - self.last_failure_time)
                logger.warning(
                    f"⛔ Circuit breaker is OPEN. API unavailable. "
                    f"Retry in {time_remaining:.0f}s."
                )
                raise Exception(
                    f"Circuit breaker is OPEN. API is unavailable. "
                    f"Please wait {time_remaining:.0f} seconds before retrying."
                )

        try:
            result = func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call - reset failure count and potentially close circuit."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            logger.info(
                f"✅ Circuit breaker: Success in HALF_OPEN state "
                f"({self.success_count}/{self.success_threshold})"
            )

            if self.success_count >= self.success_threshold:
                logger.info(f"✅ Circuit breaker transitioning to CLOSED (service recovered)")
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def _on_failure(self):
        """Handle failed call - increment failure count and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.warning(
            f"❌ Circuit breaker: Failure #{self.failure_count}/{self.failure_threshold}"
        )

        if self.failure_count >= self.failure_threshold:
            logger.error(
                f"🚨 Circuit breaker transitioning to OPEN "
                f"(threshold {self.failure_threshold} exceeded)"
            )
            self.state = CircuitState.OPEN

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"🔄 Circuit breaker manually reset to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def get_state(self) -> str:
        """Get current state of circuit breaker."""
        return self.state.value

    def __repr__(self) -> str:
        """String representation of circuit breaker."""
        return (
            f"CircuitBreaker(state={self.state.value}, "
            f"failures={self.failure_count}/{self.failure_threshold}, "
            f"successes={self.success_count}/{self.success_threshold})"
        )
