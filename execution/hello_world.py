"""
Hello World - Example execution script demonstrating the architecture.
"""
import os
import sys
from typing import Dict, Any

# Load environment variables if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed yet, that's okay for this example

def generate_greeting(name: str, language: str = "en") -> Dict[str, Any]:
    """
    Generate a greeting in the specified language.

    Args:
        name: Person or entity to greet
        language: Language code (en, es, fr, de)

    Returns:
        Dictionary with greeting and metadata

    Raises:
        ValueError: If name is empty
    """
    # Validate inputs
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")

    # Greeting templates
    greetings = {
        "en": f"Hello, {name}!",
        "es": f"¡Hola, {name}!",
        "fr": f"Bonjour, {name}!",
        "de": f"Guten Tag, {name}!",
    }

    # Get greeting or default to English
    greeting = greetings.get(language.lower(), greetings["en"])
    used_language = language.lower() if language.lower() in greetings else "en"

    result = {
        "success": True,
        "greeting": greeting,
        "name": name,
        "language": used_language,
        "fallback_used": used_language != language.lower()
    }

    print(f"✓ {greeting}")
    return result

def main():
    """Example usage when run as script."""
    if len(sys.argv) < 2:
        print("Usage: python hello_world.py <name> [language]")
        sys.exit(1)

    name = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "en"

    try:
        result = generate_greeting(name, language)
        if result["fallback_used"]:
            print(f"⚠ Warning: Language '{sys.argv[2]}' not supported, used English")
        return result
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
