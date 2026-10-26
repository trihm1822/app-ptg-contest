"""Unit tests for Normalized Token Comparator complying with ADR-003 and ADR-006."""

from ptg.core.comparator import compare_outputs, normalize_lines, tokenize_output


def test_tokenize_output():
    """Verify whitespace splitting handles multiple spaces, tabs, and newlines."""
    text = " 42   hello\tworld \n\n 100 \n"
    tokens = tokenize_output(text)
    assert tokens == ["42", "hello", "world", "100"]


def test_normalize_lines():
    """Verify carriage returns and trailing lines are removed."""
    text = "line1  \r\nline2\t \r\nline3\r\n\r\n"
    lines = normalize_lines(text)
    assert lines == ["line1", "line2", "line3"]


def test_compare_outputs_exact_match():
    """Exact identical outputs match."""
    out1 = "1 2\n3 4\n"
    out2 = "1 2\n3 4\n"
    is_match, detail = compare_outputs(out1, out2)
    assert is_match is True
    assert detail is None


def test_compare_outputs_whitespace_normalization():
    """Outputs differing only by spaces and trailing newlines match in token mode."""
    out1 = "1  2 \n3 4\n\n"
    out2 = "1 2\n3   4"
    is_match, detail = compare_outputs(out1, out2, token_mode=True)
    assert is_match is True
    assert detail is None


def test_compare_outputs_token_value_mismatch():
    """Outputs differing in token values report mismatch with context."""
    expected = "1 2 3 4 5"
    actual = "1 2 99 4 5"
    is_match, detail = compare_outputs(expected, actual, token_mode=True)
    assert is_match is False
    assert "Token mismatch at token #3" in detail
    assert "expected '3', got '99'" in detail


def test_compare_outputs_token_count_mismatch():
    """Outputs with different number of tokens report count mismatch."""
    expected = "1 2 3 4"
    actual = "1 2 3"
    is_match, detail = compare_outputs(expected, actual, token_mode=True)
    assert is_match is False
    assert "Token count mismatch: expected 4 tokens, got 3 tokens" in detail


def test_compare_outputs_line_mode():
    """Test line-by-line comparison mode."""
    exp = "first line\nsecond line"
    act = "first line\ndifferent line"
    is_match, detail = compare_outputs(exp, act, token_mode=False)
    assert is_match is False
    assert "Line mismatch at line #2" in detail


def test_compare_outputs_strict_bytes_mode():
    """In strict mode, trailing space difference must fail."""
    out1 = "1 2 3\n"
    out2 = "1 2 3 \n"  # trailing space
    # In standard token mode, they match
    match_token, _ = compare_outputs(out1, out2, token_mode=True, strict_bytes=False)
    assert match_token is True

    # In strict bytes mode, they must report mismatch
    match_strict, detail = compare_outputs(out1, out2, strict_bytes=True)
    assert match_strict is False
    assert "Strict byte mismatch" in detail
