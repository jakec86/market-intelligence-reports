"""Skill guardrail compliance tests.

These tests read skill .md files as raw text and assert that required safety
guardrails are present and no dangerous patterns (e.g. 'sort sheet') exist.

If a test fails, the fix is to edit the relevant .md file in ~/.claude/commands/
and add or correct the guardrail text.
"""
from pathlib import Path
import pytest

SKILLS_DIR = Path.home() / ".claude/commands"


def _read_skill(filename: str) -> str:
    path = SKILLS_DIR / filename
    assert path.exists(), f"Skill file not found: {path}"
    return path.read_text()


# ── FM-7: Sort-range guardrail — PB report skills ─────────────────────────────

@pytest.mark.parametrize("skill_file", [
    "nalley-pb-report.md",
    "hendricks-pb-report.md",
])
def test_pb_skill_says_sort_range_not_sort_sheet(skill_file):
    """PB report skills must instruct 'Sort range Ax:Jy', never 'Sort sheet'.

    'Sort sheet' moves the header row into data — a known past incident.
    The guardrail must explicitly say 'Sort range' to override the UI default.
    """
    text = _read_skill(skill_file).lower()
    assert "sort range" in text, (
        f"{skill_file}: missing 'Sort range' guardrail — "
        "add an explicit 'Sort range A4:L...' instruction to prevent header corruption"
    )
    assert "sort sheet" not in text, (
        f"{skill_file}: contains dangerous 'Sort sheet' instruction — "
        "replace with 'Sort range Ax:Jy (data rows only)'"
    )


# ── FM-8: HTML email guardrail — all email-drafting skills ────────────────────

@pytest.mark.parametrize("skill_file", [
    "nalley-pb-report.md",
    "hendricks-pb-report.md",
    "sonic-monthly-report.md",
    "aca-monthly-report.md",
    "ep-review-report.md",
])
def test_email_skill_specifies_html_not_plain_text(skill_file):
    """Email-drafting skills must specify HTML format and must not mention plain text.

    Plain text fallback strips all formatting and hyperlinks — a known past incident.
    """
    text = _read_skill(skill_file).lower()
    assert "html" in text, (
        f"{skill_file}: no HTML email requirement found — "
        "add an explicit instruction to use HTML-formatted email body"
    )
    assert "plain text" not in text, (
        f"{skill_file}: contains 'plain text' — remove or replace with 'HTML'"
    )
