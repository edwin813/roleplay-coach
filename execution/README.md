# Execution Scripts

This directory contains deterministic Python scripts that do the actual work. These are Layer 3 of the architecture.

## Principles

1. **Deterministic** - Same inputs = same outputs
2. **Testable** - Can be run standalone
3. **Reliable** - Handle errors gracefully
4. **Fast** - Optimize for performance
5. **Documented** - Clear docstrings and type hints

## Script Template

```python
"""
Brief description of what this script does.
"""
import os
from dotenv import load_dotenv
from typing import Any, Dict, List

load_dotenv()

def main(param1: str, param2: int = 10) -> Dict[str, Any]:
    """
    Main function that does the work.

    Args:
        param1: Description of parameter
        param2: Description with default value

    Returns:
        Dictionary with results and status

    Raises:
        ValueError: If inputs are invalid
        APIError: If external API fails
    """
    # Validate inputs
    if not param1:
        raise ValueError("param1 is required")

    # Do the work
    results = []

    # Return structured output
    return {
        "success": True,
        "results": results,
        "count": len(results)
    }

if __name__ == "__main__":
    # Example usage
    result = main("example")
    print(result)
```

## Environment Variables

All scripts should use `python-dotenv` to load environment variables from `.env`:

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("API_KEY")
```

## Error Handling

Return structured results that indicate success/failure:

```python
{
    "success": True/False,
    "data": {...},
    "error": "Error message if failed",
    "metadata": {"processed": 100, "failed": 5}
}
```

## Testing

Scripts should be runnable standalone for testing:

```bash
python execution/script_name.py
```
