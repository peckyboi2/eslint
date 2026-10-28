"""Pure preview routing with no public-write interface. Serves task 13 and R1."""
import re
from typing import TypedDict

import constants as c
from errors import ValidationError
from validation import ModelResult, parse_and_validate


class PreviewRoute(TypedDict, total=False):
    """A trusted, publicly silent preview envelope."""
    mode: str
    public_actions: list
    preview_comment: str | None
    source_issue: int
    repository_id: int
    repository: str
    posting_target: None
    valid: bool
    decision: str
    validated_output: ModelResult
    error: str


def silent_envelope() -> PreviewRoute:
    """Return a fresh envelope bound to the trusted preview identity."""
    return {"mode": "preview", "public_actions": [], "preview_comment": None,
            "source_issue": c.SOURCE_ISSUE, "repository_id": c.REPOSITORY_ID,
            "repository": c.REPOSITORY, "posting_target": None}


def rejected(error: ValidationError) -> PreviewRoute:
    """Return a publicly silent invalid-result envelope."""
    return {**silent_envelope(), "valid": False, "decision": "invalid", "error": str(error)}


def attributed_comment(comment: str, run_id: str, model: str) -> str:
    """Return bounded attribution or raise ValidationError for unsafe identity."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run_id + model):
        raise ValidationError("Unsafe trusted attribution")
    text = comment + f"\n\n**Created by AI (OpenAI Codex, {model}).**\nPreview run: `{run_id}`."
    if len(text) > c.MAX_COMMENT_CHARS:
        raise ValidationError("Attributed comment exceeds limit")
    return text


def route_result(result: ModelResult, run_id: str, model: str) -> PreviewRoute:
    """Return the validated preview route or raise ValidationError for attribution."""
    route = silent_envelope()
    route.update({"valid": True, "decision": result[c.DECISION], "validated_output": result})
    if result[c.DECISION] == c.CLARIFY:
        comment = result[c.CLARIFICATION]
        if comment is None:
            raise ValidationError("Invalid clarification")
        route["preview_comment"] = attributed_comment(comment, run_id, model)
    return route


def route(raw: str, run_id: str, model: str) -> PreviewRoute:
    """Return a preview route, including a silent rejection for invalid output."""
    try:
        return route_result(parse_and_validate(raw), run_id, model)
    except ValidationError as error:
        return rejected(error)
