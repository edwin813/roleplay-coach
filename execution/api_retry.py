"""
API retry utilities with exponential backoff for handling rate limits and overload.

This module provides robust retry logic for Anthropic Claude API calls to handle
temporary failures like 529 Overloaded errors gracefully.
"""
import time
import logging
import random
from typing import Callable, TypeVar
from anthropic import (
    RateLimitError,
    APIStatusError,
    APIConnectionError,
    APITimeoutError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


def with_retry(
    func: Callable[..., T],
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> T:
    """
    Execute function with exponential backoff retry logic.

    This function will retry API calls that fail with rate limit (429) or
    overload (529) errors, using exponential backoff to avoid overwhelming
    the API further.

    Args:
        func: Function to execute (should be a callable with no arguments)
        max_retries: Maximum number of retry attempts (default: 5)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Add randomness to delay to prevent thundering herd (default: True)

    Returns:
        Result of function execution

    Raises:
        Last exception if all retries are exhausted

    Example:
        >>> def api_call():
        ...     return client.messages.create(...)
        >>> result = with_retry(api_call, max_retries=5)
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except (RateLimitError, APIStatusError) as e:
            # Check if it's a 529 error or rate limit
            if hasattr(e, 'status_code') and e.status_code in [429, 529]:
                last_exception = e

                if attempt == max_retries:
                    logger.error(f"❌ Max retries ({max_retries}) exhausted for API call")
                    raise

                # Calculate delay with exponential backoff
                delay = min(initial_delay * (exponential_base ** attempt), max_delay)

                # Add jitter to prevent thundering herd
                if jitter:
                    delay = delay * (0.5 + random.random())

                logger.warning(
                    f"⚠️  API overload (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Retrying in {delay:.2f}s... Error: {str(e)}"
                )

                time.sleep(delay)
            else:
                # Not a retryable error, raise immediately
                raise
        except (APIConnectionError, APITimeoutError) as e:
            # Network errors are also retryable
            last_exception = e

            if attempt == max_retries:
                logger.error(f"❌ Max retries ({max_retries}) exhausted for API call")
                raise

            delay = min(initial_delay * (exponential_base ** attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"⚠️  API connection error (attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {delay:.2f}s... Error: {str(e)}"
            )

            time.sleep(delay)
        except Exception as e:
            # Non-retryable error
            logger.error(f"❌ Non-retryable error in API call: {str(e)}")
            raise

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception


def classify_api_error(error: Exception) -> dict:
    """
    Classify API error type for user-friendly messaging.

    This function examines an exception and returns a structured
    classification to help with error handling and user communication.

    Args:
        error: Exception raised by API call

    Returns:
        Dictionary with error classification:
            - type: 'rate_limit', 'overload', 'timeout', 'connection', 'unknown'
            - retryable: bool (whether error can be retried)
            - user_message: str (user-friendly message)
            - technical_message: str (for logging)

    Example:
        >>> try:
        ...     result = api_call()
        ... except Exception as e:
        ...     info = classify_api_error(e)
        ...     logger.error(info['technical_message'])
        ...     notify_user(info['user_message'])
    """
    if isinstance(error, RateLimitError):
        return {
            'type': 'rate_limit',
            'retryable': True,
            'user_message': 'API rate limit reached. Please wait a moment and try again.',
            'technical_message': str(error)
        }

    if isinstance(error, APIStatusError):
        if hasattr(error, 'status_code') and error.status_code == 529:
            return {
                'type': 'overload',
                'retryable': True,
                'user_message': 'AI service is temporarily overloaded. Your session will retry automatically.',
                'technical_message': f"529 Overloaded: {str(error)}"
            }
        elif hasattr(error, 'status_code') and error.status_code == 429:
            return {
                'type': 'rate_limit',
                'retryable': True,
                'user_message': 'Too many requests. Please wait a moment.',
                'technical_message': f"429 Rate Limit: {str(error)}"
            }

    if isinstance(error, APITimeoutError):
        return {
            'type': 'timeout',
            'retryable': True,
            'user_message': 'Request timed out. Retrying...',
            'technical_message': str(error)
        }

    if isinstance(error, APIConnectionError):
        return {
            'type': 'connection',
            'retryable': True,
            'user_message': 'Connection error. Please check your internet connection.',
            'technical_message': str(error)
        }

    return {
        'type': 'unknown',
        'retryable': False,
        'user_message': 'An unexpected error occurred. Please try again.',
        'technical_message': str(error)
    }
