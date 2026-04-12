"""
TrustOps-Env: Grader Module (OpenEnv-Compliant)
=================================================
Each grader function follows the OpenEnv standard signature:
    def grade(sample: dict, item: Any) -> float

Returns a float strictly within (0.01, 0.99).

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


def safe_score(x: float) -> float:
    """Global safety clamp — guarantees output is strictly within (0.05, 0.49)
    as requested to keep scores away from 1.0 and up to 0.5."""
    try:
        val = float(x)
    except (TypeError, ValueError):
        val = 0.25
    return max(0.05, min(val, 0.49))


# ─── Internal scoring logic (shared by both interfaces) ─────────────────────

def _score_easy(content: Content, agent_action: ActionType,
                agent_reasoning: str) -> float:
    expected_action = content.expected_action
    c_score = 0.20 if agent_action == expected_action else 0.05
    a_score = 0.15 if agent_action == expected_action else 0.05
    r_score = 0.02
    toxic_words = ["toxic", "abusive", "hate", "spam", "violation", "harmful", "unsafe"]
    if any(word in agent_reasoning.lower() for word in toxic_words):
        r_score = 0.10
    penalty = 0.0
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.15
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.08
    return safe_score(c_score + a_score + r_score + penalty)


def _score_medium(content: Content, agent_action: ActionType,
                  agent_reasoning: str) -> float:
    expected_action = content.expected_action
    expected_label = content.expected_label
    c_score = 0.20 if agent_action == expected_action else 0.05
    a_score = 0.15 if agent_action == expected_action else 0.05
    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.20, 0.15
    r_score = 0.02
    context_words = ["context", "sarcastic", "satire", "frustration", "harassment", "humor", "joke"]
    if any(word in agent_reasoning.lower() for word in context_words):
        r_score += 0.04
    similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
    r_score += round(min(0.04, similarity * 0.08), 3)
    r_score = min(0.10, r_score)
    penalty = 0.0
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.15
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.08
    return safe_score(c_score + a_score + r_score + penalty)


def _score_hard(content: Content, agent_action: ActionType,
                agent_reasoning: str) -> float:
    expected_action = content.expected_action
    expected_label = content.expected_label
    c_score = 0.20 if agent_action == expected_action else 0.05
    a_score = 0.15 if agent_action == expected_action else 0.05
    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.20, 0.15
    r_score = 0.02
    hard_words = ["grooming", "radicalization", "pattern", "history", "subtle",
                  "manipulation", "coded", "leaked", "whistleblower"]
    if any(word in agent_reasoning.lower() for word in hard_words):
        r_score += 0.04
    similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
    r_score += round(min(0.04, similarity * 0.12), 3)
    r_score = min(0.10, r_score)
    penalty = 0.0
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.15
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.08
    return safe_score(c_score + a_score + r_score + penalty)


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

def grade_easy_detection(*args, **kwargs) -> float:
    """
    OpenEnv grader for easy_detection.
    Accepts: (sample, item) OR (content, agent_action, agent_reasoning, agent_confidence)
    Returns: float in (0.01, 0.99)
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
                return safe_score(0.5)
        else:
            return safe_score(0.5)

        return _score_easy(content, agent_action, agent_reasoning)
    except Exception:
        return safe_score(0.5)


def grade_medium_classification(*args, **kwargs) -> float:
    """
    OpenEnv grader for medium_classification.
    Accepts: (sample, item) OR (content, agent_action, agent_reasoning, agent_confidence)
    Returns: float in (0.01, 0.99)
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
                return safe_score(0.5)
        else:
            return safe_score(0.5)

        return _score_medium(content, agent_action, agent_reasoning)
    except Exception:
        return safe_score(0.5)


def grade_hard_contextual(*args, **kwargs) -> float:
    """
    OpenEnv grader for hard_contextual.
    Accepts: (sample, item) OR (content, agent_action, agent_reasoning, agent_confidence)
    Returns: float in (0.01, 0.99)
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
                return safe_score(0.5)
        else:
            return safe_score(0.5)

        return _score_hard(content, agent_action, agent_reasoning)
    except Exception:
        return safe_score(0.5)


# ─── Unified dispatcher ─────────────────────────────────────────────────────

def grade_task(task_name: str, *args, **kwargs) -> float:
    """Routes to the correct grading function by task name."""
    if task_name == "easy_detection":
        return grade_easy_detection(*args, **kwargs)
    elif task_name == "medium_classification":
        return grade_medium_classification(*args, **kwargs)
    elif task_name == "hard_contextual":
        return grade_hard_contextual(*args, **kwargs)
    else:
        return safe_score(0.5)
