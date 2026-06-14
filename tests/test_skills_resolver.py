"""Tests for codedjinn/skills/resolver.py."""

import pytest

from codedjinn.skills.loader import SKILL_FILENAME
from codedjinn.skills.resolver import resolve_skill


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(skills_dir, name, *, steps=3, extra_commands=None, body="Strategy."):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    cmds = extra_commands or []
    cmd_lines = "".join(f"  - {c}\n" for c in cmds)
    if not cmd_lines:
        cmd_lines = "  []\n"
    content = (
        f"---\n"
        f"name: {name}\n"
        f"title: {name.capitalize()}\n"
        f"steps: {steps}\n"
        f"extra_commands:\n{cmd_lines}"
        f"---\n\n"
        f"{body}\n"
    )
    (skill_dir / SKILL_FILENAME).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Basic resolution
# ---------------------------------------------------------------------------


def test_leading_slash_matches_known_skill(tmp_path):
    _write_skill(tmp_path, "search")
    clean, skill = resolve_skill("/search find readme", tmp_path)
    assert clean == "find readme"
    assert skill is not None
    assert skill.name == "search"


def test_paths_in_body_untouched(tmp_path):
    _write_skill(tmp_path, "search")
    clean, skill = resolve_skill("/search in /myfolder", tmp_path)
    # /myfolder is non-leading so it should stay in clean query
    assert "/myfolder" in clean
    assert skill is not None


def test_inline_slash_skill_matches_known_skill(tmp_path):
    _write_skill(tmp_path, "search")
    query = "please /search in /myfolder"
    clean, skill = resolve_skill(query, tmp_path)
    assert clean == "please in /myfolder"
    assert skill is not None
    assert skill.name == "search"


def test_unknown_leading_skill_warns_and_returns_unchanged(tmp_path, capsys):
    _write_skill(tmp_path, "search")
    query = "/typo query here"
    clean, skill = resolve_skill(query, tmp_path)
    assert clean == query
    assert skill is None
    captured = capsys.readouterr()
    assert "unknown skill directive" in captured.err
    assert "/typo" in captured.err


def test_empty_query_returns_none(tmp_path):
    clean, skill = resolve_skill("", tmp_path)
    assert clean == ""
    assert skill is None


def test_all_directive_query_returns_empty_clean(tmp_path):
    _write_skill(tmp_path, "search")
    clean, skill = resolve_skill("/search", tmp_path)
    assert clean == ""
    assert skill is not None
    assert skill.name == "search"


# ---------------------------------------------------------------------------
# Empty skills dir
# ---------------------------------------------------------------------------


def test_empty_skills_dir_no_crash(tmp_path):
    empty_dir = tmp_path / "skills"
    clean, skill = resolve_skill("/search find me", empty_dir)
    # /search is first token but unknown — should warn and return unchanged
    assert skill is None


# ---------------------------------------------------------------------------
# Multiple leading skills (merge)
# ---------------------------------------------------------------------------


def test_multiple_leading_skills_merged(tmp_path):
    _write_skill(tmp_path, "search", steps=5, extra_commands=["rg"], body="Search strategy.")
    _write_skill(tmp_path, "debug", steps=3, extra_commands=["fd"], body="Debug strategy.")

    clean, skill = resolve_skill("/search /debug find X", tmp_path)

    assert clean == "find X"
    assert skill is not None
    # steps: first (search) wins
    assert skill.steps == 5
    # extra_commands: union
    assert "rg" in skill.extra_commands
    assert "fd" in skill.extra_commands
    # description: both present
    assert "Search strategy." in skill.description
    assert "Debug strategy." in skill.description
    # name: joined
    assert skill.name == "search+debug"
