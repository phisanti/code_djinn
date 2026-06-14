from __future__ import annotations

import sys
from pathlib import Path

from codedjinn.skills.loader import SkillConfig, load_skill, load_all_skill_names


def resolve_skill(query: str, skills_dir: Path) -> tuple[str, SkillConfig | None]:
    """Parse skill directives from *query* and return the cleaned query
    plus a merged SkillConfig (or None if no skill was found).

    Parsing rules
    -------------
    1. Load all known skill names from *skills_dir*.
    2. Split the query on whitespace and inspect each token.
    3. A token is a skill directive when it starts with ``/`` AND ``token[1:]``
       matches a known skill name (case-sensitive).
    4. Known skill directives are removed from the clean query no matter where
       they appear, so "please /search find X" activates the search skill.
    5. If the FIRST token starts with ``/`` but does NOT match a known skill,
       emit a warning to stderr and return the original query unchanged with None.
    6. Unknown non-leading ``/word`` tokens are left untouched so absolute paths
       and ordinary text are not mangled.
    7. Multiple skills: max of all ``steps`` values; union
       ``extra_commands`` (deduped, order-preserved); concatenate ``description``
       strings with ``"\\n"``.
    8. Return ``(clean_query, skill_or_None)``.
    """
    tokens = query.split()

    if not tokens:
        return query, None

    # Load known names once; an empty or missing dir is handled gracefully by
    # load_all_skill_names (expected to return an empty collection).
    known_names: set[str] = set(load_all_skill_names(skills_dir))

    directive_tokens: list[str] = []
    body_tokens: list[str] = []

    for i, token in enumerate(tokens):
        if not token.startswith("/"):
            body_tokens.append(token)
            continue

        skill_name = token[1:]

        if skill_name in known_names:
            directive_tokens.append(skill_name)
            continue

        if i == 0:
            print(f"[djinn] unknown skill directive: {token}", file=sys.stderr)
            return query, None

        body_tokens.append(token)

    if not directive_tokens:
        return query, None

    clean_query = " ".join(body_tokens)

    # Load and merge skills.
    merged: SkillConfig | None = None
    for name in directive_tokens:
        skill = load_skill(name, skills_dir)
        if skill is None:
            continue
        if merged is None:
            merged = skill
        else:
            merged = _merge(merged, skill)

    return clean_query, merged


def _merge(base: SkillConfig, other: SkillConfig) -> SkillConfig:
    """Merge *other* into *base*, returning a new synthetic SkillConfig.

    Merge rules:
    - steps: max of both (more skills = more reasoning budget).
    - extra_commands: union, insertion order preserved, no duplicates.
    - description: concatenated with newline; empty strings are treated as
      falsy so a blank body does not insert a bare newline separator.
    - name/title: joined with '+' (e.g. 'search+deep').

    The result exists only in memory for the current request.
    """
    # Deduplicate extra_commands while preserving insertion order.
    seen: set[str] = set(base.extra_commands)
    merged_extra = list(base.extra_commands)
    for cmd in other.extra_commands:
        if cmd not in seen:
            seen.add(cmd)
            merged_extra.append(cmd)

    description = (
        base.description + "\n" + other.description
        if base.description and other.description
        else base.description or other.description
    )

    return SkillConfig(
        name=f"{base.name}+{other.name}",
        title=f"{base.title}+{other.title}",
        steps=max(base.steps, other.steps),
        extra_commands=merged_extra,
        description=description,
    )
