"""
Text filtering utilities for voice training platform.

Removes stage directions and formatting markers from AI-generated text
before text-to-speech synthesis to prevent unnatural reading of markup.
"""
import re
import logging

logger = logging.getLogger(__name__)


def clean_text_for_speech(text: str, log_changes: bool = True) -> str:
    """
    Remove stage directions and formatting markers from text before TTS.

    This function filters out theatrical formatting that AI models sometimes
    include in responses (like *pauses*, [thinking], --emphatically--, etc.)
    which would otherwise be read verbatim by text-to-speech engines.

    Removes:
        - *action* (asterisk-wrapped actions like *pauses*, *thinking*)
        - [aside] (bracketed stage directions like [aside], [thinking])
        - --emotion-- (dashed emphasis like --emphatically--, --softly--)
        - (nervously) (parenthetical emotions - adverbs only)

    Preserves:
        - Legitimate parentheses: "benefits (life, health, dental)"
        - Hyphens in words: "sister-in-law"
        - Number ranges: "2-3 weeks"

    Args:
        text: Raw text from LLM that may contain stage directions
        log_changes: Whether to log what was filtered (default: True)

    Returns:
        Cleaned text safe for speech synthesis

    Examples:
        >>> clean_text_for_speech("Hello *pauses* there")
        "Hello  there"
        >>> clean_text_for_speech("I think [thinking] okay")
        "I think  okay"
        >>> clean_text_for_speech("We offer benefits (life, health, dental)")
        "We offer benefits (life, health, dental)"
    """
    if not text:
        return text

    original = text

    # Remove asterisk-wrapped actions: *pauses*, *thinking*, *nervous laugh*
    text = re.sub(r'\*[^*]+\*', '', text)

    # Remove bracketed directions: [aside], [thinking], [pauses to think]
    text = re.sub(r'\[[^\]]+\]', '', text)

    # Remove dashed emphasis: --emphatically--, --softly--, --hesitantly--
    text = re.sub(r'--[^-]+--', '', text)

    # Remove parenthetical stage directions at sentence start
    # Matches: (nervously) at start or after period
    text = re.sub(r'(^|\.\s+)\([^)]+\)\s+', r'\1', text)

    # Remove mid-sentence adverb stage directions: (nervously), (softly)
    # Only matches adverbs (words ending in 'ly')
    text = re.sub(r'\s+\([a-zA-Z\s]+ly\)\s+', ' ', text)

    # Remove common action words: (sighs), (pauses), (thinks)
    # Using alternation to match these specific words
    text = re.sub(r'\s+\((sighs?|pauses?|thinks?)\)\s+', ' ', text)

    # Clean up excessive whitespace created by removals
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Log changes for debugging and monitoring
    if log_changes and text != original:
        logger.info(f"🧹 Filtered stage directions from text")
        logger.debug(f"   Original: {original}")
        logger.debug(f"   Cleaned:  {text}")

    return text
