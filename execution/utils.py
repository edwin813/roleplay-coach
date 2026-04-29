"""
Shared utilities for execution scripts.
"""
import os
import json
from typing import Any, Dict
from datetime import datetime
from pathlib import Path

def get_tmp_dir() -> Path:
    """Get the .tmp directory, creating it if needed."""
    tmp_dir = Path(__file__).parent.parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    return tmp_dir

def save_intermediate(data: Any, filename: str) -> str:
    """
    Save intermediate data to .tmp directory.

    Args:
        data: Data to save (will be JSON serialized if dict/list)
        filename: Name of file to create

    Returns:
        Path to saved file
    """
    tmp_dir = get_tmp_dir()
    filepath = tmp_dir / filename

    if isinstance(data, (dict, list)):
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        with open(filepath, 'w') as f:
            f.write(str(data))

    return str(filepath)

def load_intermediate(filename: str) -> Any:
    """
    Load intermediate data from .tmp directory.

    Args:
        filename: Name of file to load

    Returns:
        Loaded data (parsed as JSON if possible)
    """
    tmp_dir = get_tmp_dir()
    filepath = tmp_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Intermediate file not found: {filename}")

    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(filepath, 'r') as f:
            return f.read()

def create_result(success: bool, data: Any = None, error: str = None, **metadata) -> Dict[str, Any]:
    """
    Create a standardized result dictionary.

    Args:
        success: Whether operation succeeded
        data: Result data if successful
        error: Error message if failed
        **metadata: Additional metadata fields

    Returns:
        Standardized result dictionary
    """
    result = {
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if data is not None:
        result["data"] = data

    if error:
        result["error"] = error

    if metadata:
        result["metadata"] = metadata

    return result

def log_execution(directive_name: str, result: Dict[str, Any]) -> None:
    """
    Log execution results (can be extended to write to file, send to Slack, etc).

    Args:
        directive_name: Name of directive being executed
        result: Result dictionary from execution
    """
    status = "✓" if result.get("success") else "✗"
    timestamp = result.get("timestamp", datetime.utcnow().isoformat())

    print(f"{status} [{timestamp}] {directive_name}")

    if not result.get("success") and result.get("error"):
        print(f"  Error: {result['error']}")

    # Future: Write to log file, send to Slack, etc.
