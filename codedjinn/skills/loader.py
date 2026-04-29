from dataclasses import dataclass
from pathlib import Path

import yaml

# Registry of commands skills can unlock for ObserveExecutor beyond the baseline
# SAFE_COMMANDS allowlist. Key = name used in SKILL.md extra_commands list.
# Value = regex matched against command.strip().lower(). Unknown names in a
# skill file raise ValueError at load time; unknown names passed to
# ObserveExecutor.__init__ are silently ignored (validated upstream by loader).
EXTRA_COMMANDS_REGISTRY: dict[str, str] = {
    "rg": r"^rg\s+",
    "fd": r"^fd\s+",
    "bat": r"^bat\s+",
    "jq": r"^jq\s+",
}

SKILL_FILENAME = "SKILL.md"


@dataclass
class SkillConfig:
    name: str
    title: str
    steps: int
    extra_commands: list[str]
    description: str


def _parse_frontmatter(content: str, name: str) -> tuple[dict, str]:
    """Split SKILL.md into (frontmatter_dict, body_str).

    Expects the file to start with a --- fence, have a closing --- fence,
    and have optional markdown body after it.
    """
    if not content.startswith("---"):
        raise ValueError(
            f"Skill '{name}': SKILL.md must begin with a YAML frontmatter block (---)"
        )

    close = content.find("\n---", 3)
    if close == -1:
        raise ValueError(
            f"Skill '{name}': SKILL.md frontmatter block is not closed (missing closing ---)"
        )

    frontmatter_str = content[3:close].strip()
    body = content[close + 4:].strip()  # skip '\n---'

    try:
        data = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError as exc:
        raise ValueError(f"Skill '{name}': malformed YAML frontmatter — {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(
            f"Skill '{name}': frontmatter must be a YAML mapping, "
            f"got {type(data).__name__ if data is not None else 'empty'}"
        )

    return data, body


def load_skill(name: str, skills_dir: Path) -> SkillConfig | None:
    """Load a skill from <skills_dir>/<name>/SKILL.md.

    Returns None if the skill directory or SKILL.md does not exist.
    Raises ValueError for schema violations: malformed YAML, non-mapping
    frontmatter, name mismatch, out-of-range steps, or unknown extra_commands.

    Side effect: always bootstraps skills_dir via mkdir(parents=True,
    exist_ok=True) — callers must not rely on directory non-existence as a
    signal that no skills are configured.
    """
    skills_dir.mkdir(parents=True, exist_ok=True)

    skill_file = skills_dir / name / SKILL_FILENAME
    if not skill_file.exists():
        return None

    content = skill_file.read_text(encoding="utf-8")
    data, body = _parse_frontmatter(content, name)

    frontmatter_name = data.get("name")
    if frontmatter_name and str(frontmatter_name) != name:
        raise ValueError(
            f"Skill '{name}': frontmatter 'name: {frontmatter_name}' does not match "
            f"the directory name '{name}'. Rename the directory or update the frontmatter. "
            f"Skills are invoked as /{name} (the directory name)."
        )

    raw_steps = data.get("steps", 0)
    try:
        steps = int(raw_steps)
    except (TypeError, ValueError):
        raise ValueError(f"Skill '{name}': 'steps' must be an integer, got {raw_steps!r}")
    if not 0 <= steps <= 10:
        raise ValueError(f"Skill '{name}': 'steps' must be between 0 and 10, got {steps}")

    raw_extra = data.get("extra_commands") or []
    if not isinstance(raw_extra, list):
        raise ValueError(
            f"Skill '{name}': 'extra_commands' must be a list, got {type(raw_extra).__name__}"
        )
    extra_commands: list[str] = [str(c) for c in raw_extra]
    for cmd in extra_commands:
        if cmd not in EXTRA_COMMANDS_REGISTRY:
            raise ValueError(
                f"Skill '{name}': unknown extra_command '{cmd}'. "
                f"Known commands: {sorted(EXTRA_COMMANDS_REGISTRY)}"
            )

    return SkillConfig(
        name=name,
        title=str(data.get("title") or name),
        steps=steps,
        extra_commands=extra_commands,
        description=body,
    )


def load_all_skill_names(skills_dir: Path) -> list[str]:
    """Return names of all skills (subdirs containing SKILL.md) in skills_dir.

    Always bootstraps the skills directory.
    """
    skills_dir.mkdir(parents=True, exist_ok=True)
    return sorted(
        d.name for d in skills_dir.iterdir()
        if d.is_dir() and (d / SKILL_FILENAME).exists()
    )
