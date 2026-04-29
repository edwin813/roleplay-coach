"""
Unit tests for text filtering utilities.

Tests the clean_text_for_speech function to ensure it correctly removes
stage directions and formatting markers while preserving legitimate text.
"""
import pytest
from text_filters import clean_text_for_speech


def test_asterisk_actions():
    """Test removal of *action* markers"""
    input_text = "Hello *pauses* there"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "*" not in result
    assert "Hello" in result
    assert "there" in result


def test_bracketed_directions():
    """Test removal of [action] markers"""
    input_text = "I think [thinking] okay"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "[" not in result
    assert "]" not in result
    assert "I think" in result
    assert "okay" in result


def test_dashed_emphasis():
    """Test removal of --emotion-- markers"""
    input_text = "I --really-- disagree"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "--really--" not in result
    assert "disagree" in result


def test_parenthetical_at_start():
    """Test removal of (emotion) at start of response"""
    input_text = "(nervously) I'm not sure"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "(nervously)" not in result
    assert "I'm not sure" in result


def test_parenthetical_mid_sentence_adverb():
    """Test removal of mid-sentence adverb stage directions"""
    input_text = "I was thinking (nervously) about this"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "(nervously)" not in result
    assert "thinking" in result
    assert "about" in result


def test_preserves_legitimate_parentheses():
    """Ensure legitimate parens in speech are kept"""
    input_text = "We offer three benefits (life, health, and dental)"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert result == input_text  # Should be unchanged


def test_preserves_hyphens_in_words():
    """Ensure compound words with hyphens remain intact"""
    input_text = "My sister-in-law told me about this"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "sister-in-law" in result


def test_preserves_numbers_with_dashes():
    """Ensure number ranges like 2-3 weeks remain"""
    input_text = "It will take 2-3 weeks to process"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "2-3" in result


def test_multiple_patterns_combined():
    """Test text with multiple types of stage directions"""
    input_text = "*pauses* Well [thinking] I'm --really-- not sure (nervously)"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "*" not in result
    assert "[" not in result
    assert "--really--" not in result
    assert "(nervously)" not in result
    assert "Well" in result
    assert "I'm" in result
    assert "not sure" in result


def test_cleans_excessive_whitespace():
    """Ensure multiple spaces are collapsed after filtering"""
    input_text = "Hello  *pauses*  there"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "  " not in result  # No double spaces
    assert "Hello there" in result


def test_empty_string():
    """Handle edge case of empty input"""
    result = clean_text_for_speech("", log_changes=False)
    assert result == ""


def test_only_stage_directions():
    """Handle text that's entirely stage directions"""
    input_text = "*pauses* [thinking]"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert result.strip() == ""


def test_real_world_example_1():
    """Test with realistic AI-generated response"""
    input_text = "Um, *nervous laugh* yeah I think [pauses to think] my sister mentioned something about this --hesitantly-- but I'm not really sure what it's about?"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "*" not in result
    assert "[" not in result
    assert "--" not in result
    assert "Um," in result
    assert "yeah I think" in result
    assert "my sister mentioned" in result
    assert "not really sure" in result


def test_real_world_example_2():
    """Test with another realistic scenario"""
    input_text = "Well [aside] I guess that makes sense. *clears throat* When would this start?"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "[aside]" not in result
    assert "*clears throat*" not in result
    assert "Well" in result
    assert "I guess that makes sense" in result
    assert "When would this start?" in result


def test_preserves_math_expressions():
    """Ensure math-like expressions aren't broken"""
    input_text = "The cost is $25-30 per month for 3-5 years"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "$25-30" in result
    assert "3-5" in result


def test_action_words_removal():
    """Test removal of common action words in parentheses"""
    test_cases = [
        ("I agree (sighs) with that", "I agree  with that"),
        ("Let me think (pauses) about it", "Let me think  about it"),
        ("Well (thinks) maybe", "Well  maybe"),
    ]
    for input_text, expected_contains in test_cases:
        result = clean_text_for_speech(input_text, log_changes=False)
        assert "(sighs)" not in result
        assert "(pauses)" not in result
        assert "(thinks)" not in result


def test_preserves_legitimate_brackets_in_context():
    """Ensure brackets used legitimately aren't removed incorrectly"""
    # Note: Our filter removes ALL bracketed content, which is intentional
    # for stage directions. If legitimate brackets are needed, this test
    # documents the behavior.
    input_text = "The plan [ABC123] is available"
    result = clean_text_for_speech(input_text, log_changes=False)
    # This WILL be filtered out - stage directions take precedence
    assert "[ABC123]" not in result


def test_none_input():
    """Test handling of None input"""
    result = clean_text_for_speech(None, log_changes=False)
    assert result is None


def test_whitespace_only():
    """Test handling of whitespace-only input"""
    result = clean_text_for_speech("   ", log_changes=False)
    assert result.strip() == ""


def test_complex_nested_formatting():
    """Test complex nested and overlapping formatting"""
    input_text = "*[nervously thinking]* I --um-- don't know"
    result = clean_text_for_speech(input_text, log_changes=False)
    assert "*" not in result
    assert "[" not in result
    assert "--um--" not in result
    assert "I" in result
    assert "don't know" in result


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
