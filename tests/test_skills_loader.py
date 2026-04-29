"""Tests for codedjinn/skills/loader.py."""

import pytest

from codedjinn.skills.loader import (
    SKILL_FILENAME,
    load_all_skill_names,
    load_skill,
    _parse_frontmatter,
)


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------


def test_parse_frontmatter_missing_opening_fence():
    with pytest.raises(ValueError, match="must begin with a YAML frontmatter block"):
        _parse_frontmatter("name: foo\n---\nbody", "foo")


def test_parse_frontmatter_missing_closing_fence():
    with pytest.raises(ValueError, match="not closed"):
        _parse_frontmatter("---\nname: foo\n", "foo")


def test_parse_frontmatter_bare_string_raises():
    with pytest.raises(ValueError, match="frontmatter must be a YAML mapping"):
        _parse_frontmatter("---\njust a string\n---\nbody", "foo")


def test_parse_frontmatter_list_raises():
    with pytest.raises(ValueError, match="frontmatter must be a YAML mapping"):
        _parse_frontmatter("---\n- item1\n- item2\n---\nbody", "foo")


def test_parse_frontmatter_valid():
    data, body = _parse_frontmatter("---\nname: foo\nsteps: 3\n---\nsome body", "foo")
    assert data["name"] == "foo"
    assert data["steps"] == 3
    assert body == "some body"


# ---------------------------------------------------------------------------
# load_skill — missing directory / file
# ---------------------------------------------------------------------------


def test_load_skill_missing_directory(tmp_path):
    result = load_skill("nosuchskill", tmp_path)
    assert result is None


def test_load_skill_missing_skill_md(tmp_path):
    (tmp_path / "myskill").mkdir()
    result = load_skill("myskill", tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# load_skill — well-formed SKILL.md
# ---------------------------------------------------------------------------


def _write_skill(skills_dir, name, *, steps=3, extra_commands=None, title=None, body="A strategy."):
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    cmds = extra_commands or []
    cmd_lines = "".join(f"  - {c}\n" for c in cmds)
    if not cmd_lines:
        cmd_lines = "  []\n"
    content = (
        f"---\n"
        f"name: {name}\n"
        f"title: {title or name.capitalize()}\n"
        f"steps: {steps}\n"
        f"extra_commands:\n{cmd_lines}"
        f"---\n\n"
        f"{body}\n"
    )
    (skill_dir / SKILL_FILENAME).write_text(content, encoding="utf-8")


def test_load_skill_valid(tmp_path):
    _write_skill(tmp_path, "search", steps=5, extra_commands=["rg"], body="Deep search strategy.")
    skill = load_skill("search", tmp_path)
    assert skill is not None
    assert skill.name == "search"
    assert skill.steps == 5
    assert skill.extra_commands == ["rg"]
    assert "Deep search strategy." in skill.description


# ---------------------------------------------------------------------------
# load_skill — schema violations
# ---------------------------------------------------------------------------


def test_load_skill_steps_out_of_range(tmp_path):
    _write_skill(tmp_path, "toobig", steps=11)
    with pytest.raises(ValueError, match="steps.*must be between"):
        load_skill("toobig", tmp_path)


def test_load_skill_unknown_extra_command(tmp_path):
    _write_skill(tmp_path, "badcmd", extra_commands=["nonexistent"])
    with pytest.raises(ValueError, match="unknown extra_command"):
        load_skill("badcmd", tmp_path)


def test_load_skill_extra_commands_not_list(tmp_path):
    skill_dir = tmp_path / "badlist"
    skill_dir.mkdir()
    content = (
        "---\n"
        "name: badlist\n"
        "steps: 2\n"
        "extra_commands: rg\n"
        "---\n\n"
        "body\n"
    )
    (skill_dir / SKILL_FILENAME).write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="extra_commands.*must be a list"):
        load_skill("badlist", tmp_path)


def test_load_skill_name_mismatch_raises(tmp_path):
    skill_dir = tmp_path / "myskill"
    skill_dir.mkdir()
    content = (
        "---\n"
        "name: differentname\n"
        "steps: 2\n"
        "extra_commands:\n  []\n"
        "---\n\n"
        "body\n"
    )
    (skill_dir / SKILL_FILENAME).write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="myskill"):
        load_skill("myskill", tmp_path)


# ---------------------------------------------------------------------------
# load_all_skill_names
# ---------------------------------------------------------------------------


def test_load_all_skill_names_returns_sorted(tmp_path):
    for name in ("zebra", "alpha", "mango"):
        _write_skill(tmp_path, name)
    names = load_all_skill_names(tmp_path)
    assert names == ["alpha", "mango", "zebra"]


def test_load_all_skill_names_ignores_dirs_without_skill_md(tmp_path):
    _write_skill(tmp_path, "valid")
    (tmp_path / "nofile").mkdir()  # dir without SKILL.md
    names = load_all_skill_names(tmp_path)
    assert names == ["valid"]


def test_load_all_skill_names_bootstraps_missing_dir(tmp_path):
    missing = tmp_path / "newdir" / "skills"
    # Must not raise even though the directory doesn't exist yet.
    names = load_all_skill_names(missing)
    assert names == []
    assert missing.is_dir()
