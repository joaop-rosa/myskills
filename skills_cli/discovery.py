"""Descoberta de skills no repositório e parsing de frontmatter YAML."""

from __future__ import annotations

import re
from pathlib import Path

from skills_cli.models import SKILLS_DIR, SkillEntry, SkillMetadata


def _extract_frontmatter_block(content: str) -> str:
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    return match.group(1) if match else ""


def _collect_indented_lines(rest_of_text: str, initial_line: str) -> str:
    lines: list[str] = [initial_line] if initial_line else []
    for raw_line in rest_of_text.splitlines():
        if raw_line.startswith(("  ", "\t")):
            lines.append(raw_line.strip())
        elif raw_line.strip():
            break
    return " ".join(lines).strip().strip("'\"")


def _extract_description(frontmatter_text: str) -> str:
    match = re.search(
        r"^description:\s*(?:>-\s*|\|\s*)?(.*)",
        frontmatter_text,
        re.MULTILINE,
    )
    if not match:
        return ""
    return _collect_indented_lines(frontmatter_text[match.end():], match.group(1).strip())


def parse_frontmatter(skill_md_path: Path) -> SkillMetadata:
    """Extrai nome e descrição do frontmatter YAML de um arquivo SKILL.md.

    Exemplo:
        >>> meta = parse_frontmatter(Path("skills/git-commit/SKILL.md"))
    """
    fallback_name = skill_md_path.parent.name
    if not skill_md_path.is_file():
        return SkillMetadata(name=fallback_name, description="")
    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except OSError:
        return SkillMetadata(name=fallback_name, description="")
    frontmatter_text = _extract_frontmatter_block(content)
    if not frontmatter_text:
        return SkillMetadata(name=fallback_name, description="")
    name_match = re.search(r"^name:\s*([^\n]+)", frontmatter_text, re.MULTILINE)
    parsed_name = name_match.group(1).strip().strip("'\"") if name_match else fallback_name
    return SkillMetadata(name=parsed_name, description=_extract_description(frontmatter_text))


def _build_skill_entry(skill_dir: Path, category: str) -> SkillEntry:
    metadata = parse_frontmatter(skill_dir / "SKILL.md")
    return SkillEntry(
        name=skill_dir.name,
        path=skill_dir,
        category=category,
        description=metadata.description,
    )


def _collect_group_entries(group_dir: Path) -> list[SkillEntry]:
    entries: list[SkillEntry] = []
    for child in sorted(group_dir.iterdir()):
        if child.is_dir() and not child.name.startswith(".") and (child / "SKILL.md").is_file():
            entries.append(_build_skill_entry(child, group_dir.name))
    return entries


def _collect_entries_from_subdir(candidate: Path) -> list[SkillEntry]:
    if not candidate.is_dir() or candidate.name.startswith("."):
        return []
    if (candidate / "SKILL.md").is_file():
        return [_build_skill_entry(candidate, "custom")]
    return _collect_group_entries(candidate)


def _register_skill(
    entries_by_name: dict[str, SkillEntry],
    skill_entry: SkillEntry,
    skills_dir: Path,
) -> None:
    existing = entries_by_name.get(skill_entry.name)
    if existing is not None:
        raise ValueError(
            f"Duplicate skill name {skill_entry.name!r} found at {skill_entry.path} "
            f"(already registered at {existing.path}); expected unique skill names across {skills_dir}"
        )
    entries_by_name[skill_entry.name] = skill_entry


def discover_repo_skills(skills_dir: Path = SKILLS_DIR) -> list[SkillEntry]:
    """Descobre skills diretas (`skills/<skill>`) e agrupadas (`skills/<grupo>/<skill>`).

    Exemplo:
        >>> entries = discover_repo_skills()
    """
    if not skills_dir.is_dir():
        return []
    entries_by_name: dict[str, SkillEntry] = {}
    for candidate in sorted(skills_dir.iterdir()):
        for skill_entry in _collect_entries_from_subdir(candidate):
            _register_skill(entries_by_name, skill_entry, skills_dir)
    return sorted(entries_by_name.values(), key=lambda entry: entry.name)


def find_skill_by_name(skill_name: str, skills_dir: Path = SKILLS_DIR) -> SkillEntry | None:
    """Busca uma skill pelo nome do diretório em qualquer categoria do repositório.

    Exemplo:
        >>> entry = find_skill_by_name("expo-router")
    """
    for skill_entry in discover_repo_skills(skills_dir):
        if skill_entry.name == skill_name:
            return skill_entry
    return None
