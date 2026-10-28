"""Pure strict JSON and decision validation. Serves tasks 08, 13 and R1."""
import json
import re
import unicodedata
from typing import Any, Literal, TypedDict

import constants as c
from errors import ValidationError, guarded


class ModelResult(TypedDict):
    """The sole model-controlled result; target identity is excluded."""
    decision: Literal["clarify", "no_action", "human_review"]
    rationale: str
    clarification: str | None


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Return unique JSON properties or raise ValidationError on duplicates."""
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValidationError("Duplicate JSON property")
        obj[key] = value
    return obj


def reject_constant(value: str) -> None:
    """Raise ValidationError for nonfinite JSON constants."""
    raise ValidationError("Nonfinite JSON")


@guarded(ValidationError, "Malformed JSON")
def parse_json(raw: str) -> Any:
    """Return strict JSON data or raise ValidationError for malformed JSON."""
    try:
        return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except json.JSONDecodeError as error:
        raise ValidationError(str(error)) from None


def safe_text(value: Any, limit: int) -> bool:
    """Return whether text is bounded, nonblank and free of hidden controls."""
    return bool(isinstance(value, str) and 0 < len(value) <= limit and value.strip()
                and not any(unicodedata.category(ch) in ("Cc", "Cf", "Cs") and ch != "\n" for ch in value))


def validate_clarification(comment: Any) -> None:
    """Raise ValidationError for unsafe or oversized clarification wording."""
    if not safe_text(comment, c.MAX_CLARIFICATION_CHARS):
        raise ValidationError("Invalid clarification")
    visible = re.sub(r"`[^`\n]+`", "", comment)
    if ("@" in visible or "```" in comment or "<" in comment or ">" in comment
            or re.search(r"https?://|www\.|\]\(", comment, re.I)):
        raise ValidationError("Unsafe mention/link/markup in clarification")


@guarded(ValidationError, "Invalid output encoding or structure")
def parse_and_validate(raw: str) -> ModelResult:
    """Return one bounded schema result or raise ValidationError, failing closed."""
    if len(raw.encode("utf-8")) > c.MAX_OUTPUT_BYTES:
        raise ValidationError("Output exceeds byte limit")
    obj = parse_json(raw)
    if not isinstance(obj, dict) or set(obj) != c.RESULT_KEYS:
        raise ValidationError("Expected exactly one decision object with no extra fields")
    if obj[c.DECISION] not in c.ALLOWED_DECISIONS:
        raise ValidationError("Unsupported decision")
    if not safe_text(obj[c.RATIONALE], c.MAX_RATIONALE_CHARS):
        raise ValidationError("Invalid rationale")
    if obj[c.DECISION] == c.CLARIFY:
        validate_clarification(obj[c.CLARIFICATION])
    elif obj[c.CLARIFICATION] is not None:
        raise ValidationError("Silent decisions cannot have clarification text")
    return obj
