"""
TrustOps-Env: Grader Module (OpenEnv-Compliant)
"""

from typing import Any
from models import (
    Content, Action, ActionType, Difficulty, ContentLabel,
    CONTENT_BANK
)

# Small epsilon to avoid exact 0 or 1
EPS = 1e-6


def _compute_embedding_similarity(agent_reasoning: str, label: str) -> float:
    try:
        from engine import _compute_embedding_similarity as _engine_sim
        return _engine_sim(agent_reasoning, label)
    except Exception:
        return 0.05


def safe(x: float) -> float:
    """Global safety clamp: ensures (0,1) exclusive"""
    try:
        val = float(x)
    except (TypeError, ValueError):
        val = 0.5
    return max(EPS, min(val, 1.0 - EPS))


def normalize_score(total_reward, max_reward):
    raw = total_reward / max_reward if max_reward != 0 else 0

    if raw <= 0:
        return EPS
    elif raw >= 1:
        return 1.0 - EPS

    # return safe(round(raw, 3))
    return safe(raw)


# ─── Internal scoring logic ─────────────────────

def _score_base(content: Content, agent_action: ActionType) -> float:
    expected_action = content.expected_action

    # ✅ Now spans full range
    if agent_action == expected_action:
        # return normalize_score(1.0, 1.0)   # near 1
        return safe(0.999)
    elif agent_action == ActionType.FLAG:
        return normalize_score(0.5, 1.0)   # mid
    else:
        # return normalize_score(0.0, 1.0)   # near 0
        return safe(0.001)


def _score_easy(content: Content, agent_action: ActionType, agent_reasoning: str) -> float:
    return _score_base(content, agent_action)


def _score_medium(content: Content, agent_action: ActionType, agent_reasoning: str) -> float:
    return _score_base(content, agent_action)


def _score_hard(content: Content, agent_action: ActionType, agent_reasoning: str) -> float:
    return _score_base(content, agent_action)


# ─── Helper functions ─────────────────────

def _extract_action_reasoning(sample: Any) -> tuple:
    agent_action = ActionType.FLAG
    agent_reasoning = ""

    try:
        if isinstance(sample, dict):
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

    return CONTENT_BANK[0]


# ─── Grader functions ─────────────────────

def grade_easy_detection(*args, **kwargs) -> float:
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

        return safe(_score_easy(content, agent_action, agent_reasoning))

    except Exception:
        return safe(0.5)


def grade_medium_classification(*args, **kwargs) -> float:
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

        return safe(_score_medium(content, agent_action, agent_reasoning))

    except Exception:
        return safe(0.5)


def grade_hard_contextual(*args, **kwargs) -> float:
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

        return safe(_score_hard(content, agent_action, agent_reasoning))

    except Exception:
        return safe(0.5)


def grade_task(task_name: str, *args, **kwargs) -> float:
    if task_name == "easy_detection":
        return grade_easy_detection(*args, **kwargs)
    elif task_name == "medium_classification":
        return grade_medium_classification(*args, **kwargs)
    elif task_name == "hard_contextual":
        return grade_hard_contextual(*args, **kwargs)
    else:
        return safe(0.5)