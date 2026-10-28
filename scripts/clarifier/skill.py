"""Verify canonical skill bytes and native load evidence. Serves task 11 and R1."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import constants as c
from errors import SkillError, guarded
from recording import Session, sha, write_bytes
from staging import read_safe


@dataclass(frozen=True)
class LoadedSkill:
    """Verified canonical text and its native adapter path."""
    path: Path
    text: str
    sha256: str


@guarded(SkillError, "Cannot load verified canonical skill")
def load_verified(session: Session, workspace: Path) -> LoadedSkill:
    """Copy hash-verified canonical bytes to the native path or raise SkillError."""
    data = read_safe(session.root, c.SKILL_PATH.as_posix(), c.MAX_SKILL_BYTES)
    digest = sha(data)
    if digest != session.config["skill_sha256"]:
        raise SkillError("Canonical skill hash mismatch")
    path = workspace / c.NATIVE_SKILL_PATH
    path.parent.mkdir(parents=True, exist_ok=False)
    write_bytes(path, data)
    session.record.update(skill_loaded_path=str(path), skill_sha256=digest)
    return LoadedSkill(path, data.decode("utf-8"), digest)


@guarded(SkillError, "Malformed native instruction envelope")
def loaded_skill(incoming: dict[str, Any], skill: str) -> str:
    """Return one exact native skill match or raise SkillError for ambiguity."""
    candidates = [incoming.get("instructions", "")]
    candidates.extend(content.get("text", "") for item in incoming.get("input", [])
                      if item.get("role") == "developer" and item.get("type", "message") == "message"
                      for content in item.get("content", []) if isinstance(content, dict))
    matched = [text for text in candidates if text == skill or text == skill.strip()]
    if len(matched) != 1:
        raise SkillError("Codex did not load exactly one canonical instruction file (outer whitespace may be trimmed)")
    return matched[0]


def native_probe(incoming: dict[str, Any], canonical: str) -> dict[str, Any]:
    """Return content hashes and structure without retaining implicit host text."""
    native = incoming.get("instructions", "")
    return {
        "top_level_keys": sorted(incoming),
        "input_structure": [{"type": item.get("type"), "role": item.get("role"),
            "content": [{"type": part.get("type"), "length": len(part.get("text", "")),
                "equals_canonical": part.get("text") == canonical,
                "equals_trimmed": part.get("text") == canonical.strip(),
                "contains_canonical": canonical.strip() in part.get("text", "")}
                for part in item.get("content", []) if isinstance(part, dict)]}
            for item in incoming.get("input", [])],
        "native_instruction_sha256": sha(native.encode()),
        "native_length": len(native), "canonical_length": len(canonical),
        "exact_match": native == canonical, "trimmed_match": native == canonical.strip(),
        "contains_canonical": canonical in native,
        "contains_trimmed_canonical": canonical.strip() in native,
    }


def loader_evidence(incoming: dict[str, Any], canonical: str) -> dict[str, Any]:
    """Return verified native loading evidence or raise SkillError."""
    return {
        "mechanism": "Codex model_instructions_file; exact developer message after native outer-whitespace trimming",
        "loaded_content_sha256": sha(loaded_skill(incoming, canonical).encode()),
        "canonical_trimmed_sha256": sha(canonical.strip().encode()),
        "canonical_content_sha256": sha(canonical.encode()), "native_prompt_matched": True,
        "discarded_native_tool_types": [tool.get("name", tool.get("type")) for tool in incoming.get("tools", [])],
        "discarded_additional_tools_items": sum(item.get("type") == "additional_tools" for item in incoming.get("input", [])),
        "outbound_tools": [], "implicit_host_context_forwarded": False,
    }
