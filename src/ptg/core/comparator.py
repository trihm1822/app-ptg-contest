"""Output comparator with whitespace and token-by-token normalization per ADR-003."""

from typing import List, Optional, Tuple


def tokenize_output(text: str) -> List[str]:
    """Split text into tokens separated by any whitespace (spaces, tabs, newlines)."""
    return text.strip().split()


def normalize_lines(text: str) -> List[str]:
    """Split text into lines with carriage returns stripped and trailing spaces trimmed."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()]
    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def compare_outputs(
    expected: str,
    actual: str,
    token_mode: bool = True,
) -> Tuple[bool, Optional[str]]:
    """Compare two program outputs complying with ADR-003.

    Args:
        expected: Oracle / brute-force output string.
        actual: Candidate / optimized output string.
        token_mode: If True, compares token-by-token. If False, compares line-by-line.

    Returns:
        Tuple of (is_match: bool, mismatch_detail: Optional[str]).
    """
    if token_mode:
        exp_tokens = tokenize_output(expected)
        act_tokens = tokenize_output(actual)

        if exp_tokens == act_tokens:
            return True, None

        # Detect where they diverge
        min_len = min(len(exp_tokens), len(act_tokens))
        for idx in range(min_len):
            if exp_tokens[idx] != act_tokens[idx]:
                return False, (
                    f"Token mismatch at token #{idx + 1}: "
                    f"expected '{exp_tokens[idx]}', got '{act_tokens[idx]}'. "
                    f"Context: expected='...{' '.join(exp_tokens[max(0, idx-2):idx+3])}...', "
                    f"actual='...{' '.join(act_tokens[max(0, idx-2):idx+3])}...'"
                )

        if len(exp_tokens) != len(act_tokens):
            return False, (
                f"Token count mismatch: expected {len(exp_tokens)} tokens, "
                f"got {len(act_tokens)} tokens. "
                f"Next expected token: '{exp_tokens[min_len]}' "
                if len(exp_tokens) > min_len else
                f"Unexpected extra token: '{act_tokens[min_len]}'"
            )

        return False, "Outputs differ"

    else:
        exp_lines = normalize_lines(expected)
        act_lines = normalize_lines(actual)

        if exp_lines == act_lines:
            return True, None

        min_len = min(len(exp_lines), len(act_lines))
        for idx in range(min_len):
            if exp_lines[idx] != act_lines[idx]:
                return False, (
                    f"Line mismatch at line #{idx + 1}:\n"
                    f"  Expected: {exp_lines[idx]}\n"
                    f"  Got:      {act_lines[idx]}"
                )

        if len(exp_lines) != len(act_lines):
            return False, (
                f"Line count mismatch: expected {len(exp_lines)} lines, "
                f"got {len(act_lines)} lines."
            )

        return False, "Outputs differ"
