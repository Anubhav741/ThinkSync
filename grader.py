"""
TrustOps-Env: Grader Module (OpenEnv-Compliant)
=================================================
Each grader function follows the OpenEnv standard signature:
    def grade(sample: dict, item: Any) -> float

Returns an integer 0 or 1.

Also provides legacy 4-arg versions for internal inference.py use.
"""

from typing import Any
from models import (
    Content, Action, ActionType, Difficulty, ContentLabel,
    CONTENT_BANK
)

# Inline similarity computation to avoid circular import issues
def _compute_embedding_similarity(agent_reasoning: str, label: str) -> float:
    """Lightweight word-overlap similarity proxy."""
    try:
        from engine import _compute_embedding_similarity as _engine_sim
        return _engine_sim(agent_reasoning, label)
    except Exception:
        return 0.05


def safe(x: float) -> float:
    """Global safety clamp."""
    try:
        val = float(x)
    except (TypeError, ValueError):
        val = 0.5
    return 1 if val >= 0.5 else 0


def normalize_score(total_reward, max_reward):
    raw = total_reward / max_reward
    if raw > 0:
        return 1
    return 0


# ─── Internal scoring logic (shared by both interfaces) ─────────────────────

def _score_base(content: Content, agent_action: ActionType) -> int:
    expected_action = content.expected_action
    
    if agent_action == expected_action:
        return 1
    else:
        return 0

def _score_easy(content: Content, agent_action: ActionType, agent_reasoning: str) -> int:
    return _score_base(content, agent_action)

def _score_medium(content: Content, agent_action: ActionType, agent_reasoning: str) -> float:
    return _score_base(content, agent_action)

def _score_hard(content: Content, agent_action: ActionType, agent_reasoning: str) -> float:
    return _score_base(content, agent_action)


# ─── Helper: extract action/reasoning from sample dict ──────────────────────

def _extract_action_reasoning(sample: Any) -> tuple:
    """
    Extracts (ActionType, reasoning_str) from whatever OpenEnv passes.
    Handles dict, Action object, or raw string.
    """
    agent_action = ActionType.FLAG  # safe default
    agent_reasoning = ""

    try:
        if isinstance(sample, dict):
            # Try various key names OpenEnv might use
            raw_action = sample.get("action_type",
                         sample.get("action",
                         sample.get("output",
                         sample.get("response", "flag"))))
            if isinstance(raw_action, dict):
                raw_action = raw_action.get("action_type", "flag")
            raw_action = str(raw_action).lower().strip()
            if raw_action in ("approve", "remove", "flag"):
                agent_action = ActionType(raw_action)

            agent_reasoning = str(sample.get("reasoning_chain",
                                 sample.get("reasoning",
                                 sample.get("explanation",
                                 sample.get("output", "")))))
        elif hasattr(sample, "action_type"):
            agent_action = sample.action_type
            agent_reasoning = getattr(sample, "reasoning_chain", "")
        elif isinstance(sample, str):
            agent_reasoning = sample
    except Exception:
        pass

    return agent_action, agent_reasoning


def _extract_content(item: Any) -> Content:
    """
    Extracts a Content object from whatever OpenEnv passes as the item.
    """
    if isinstance(item, Content):
        return item
    if isinstance(item, dict):
        try:
            return Content(**item)
        except Exception:
            return Content(
                id=str(item.get("id", "unknown")),
                text=str(item.get("text", item.get("content", ""))),
                difficulty=Difficulty(item.get("difficulty", "EASY")),
                expected_label=ContentLabel(item.get("expected_label", "SAFE")),
                expected_action=ActionType(item.get("expected_action", "approve")),
            )
    # Fallback
    return CONTENT_BANK[0]


# ═══════════════════════════════════════════════════════════════════════════
# OpenEnv-standard grader functions: grade(sample, item) -> float
# These are what openenv.yaml points to.
# ═══════════════════════════════════════════════════════════════════════════

def grade_easy_detection(*args, **kwargs) -> int:
    """
    OpenEnv grader for easy_detection.
    Accepts: (sample, item) OR (content, agent_action, agent_reasoning, agent_confidence)
    Returns: integer 0 or 1
    """
    try:
        if len(args) == 2 and not kwargs:
            # OpenEnv calling convention: grade(sample, item)
            sample, item = args
            content = _extract_content(item)
            agent_action, agent_reasoning = _extract_action_reasoning(sample)
        elif len(args) >= 4 or kwargs:
            # Legacy calling convention from inference.py
            content = args[0] if args else kwargs.get("content", CONTENT_BANK[0])
            agent_action = args[1] if len(args) > 1 else kwargs.get("agent_action", ActionType.FLAG)
            agent_reasoning = args[2] if len(args) > 2 else kwargs.get("agent_reasoning", "")
        elif len(args) == 1:
            # Single dict with everything
            sample = args[0]
            if isinstance(sample, dict):
                content = _extract_content(sample.get("item", sample))
                agent_action, agent_reasoning = _extract_action_reasoning(sample)
            else:
                return safe(0.5)
        else:
            return safe(0.5)

        return _score_easy(content, agent_action, agent_reasoning)
    except Exception:
        return 0


def grade_medium_classification(*args, **kwargs) -> int:
    """
    OpenEnv grader for medium_classification.
    Accepts: (sample, item) OR (content, agent_action, agent_reasoning, agent_confidence)
    Returns: integer 0 or 1
    """
    try:
        if len(args) == 2 and not kwargs:
            sample, item = args
            content = _extract_content(item)
            agent_action, agent_reasoning = _extract_action_reasoning(sample)
        elif len(args) >= 4 or kwargs:
            content = args[0] if args else kwargs.get("content", CONTENT_BANK[0])
            agent_action = args[1] if len(args) > 1 else kwargs.get("agent_action", ActionType.FLAG)
            agent_reasoning = args[2] if len(args) > 2 else kwargs.get("agent_reasoning", "")
        elif len(args) == 1:
            sample = args[0]
            if isinstance(sample, dict):
                content = _extract_content(sample.get("item", sample))
                agent_action, agent_reasoning = _extract_action_reasoning(sample)
            else:
                return safe(0.5)
        else:
            return safe(0.5)

        return _score_medium(content, agent_action, agent_reasoning)
    except Exception:
        return 0


def grade_hard_contextual(*args, **kwargs) -> int:
    """
    OpenEnv grader for hard_contextual.
    Accepts: (sample, item) OR (content, agent_action, agent_reasoning, agent_confidence)
    Returns: integer 0 or 1
    """
    try:
        if len(args) == 2 and not kwargs:
            sample, item = args
            content = _extract_content(item)
            agent_action, agent_reasoning = _extract_action_reasoning(sample)
        elif len(args) >= 4 or kwargs:
            content = args[0] if args else kwargs.get("content", CONTENT_BANK[0])
            agent_action = args[1] if len(args) > 1 else kwargs.get("agent_action", ActionType.FLAG)
            agent_reasoning = args[2] if len(args) > 2 else kwargs.get("agent_reasoning", "")
        elif len(args) == 1:
            sample = args[0]
            if isinstance(sample, dict):
                content = _extract_content(sample.get("item", sample))
                agent_action, agent_reasoning = _extract_action_reasoning(sample)
            else:
                return safe(0.5)
        else:
            return safe(0.5)

        return _score_hard(content, agent_action, agent_reasoning)
    except Exception:
        return 0


# ─── Unified dispatcher ─────────────────────────────────────────────────────

def grade_task(task_name: str, *args, **kwargs) -> int:
    """Routes to the correct grading function by task name."""
    if task_name == "easy_detection":
        return grade_easy_detection(*args, **kwargs)
    elif task_name == "medium_classification":
        return grade_medium_classification(*args, **kwargs)
    elif task_name == "hard_contextual":
        return grade_hard_contextual(*args, **kwargs)
    else:
        return 0
