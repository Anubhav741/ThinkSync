"""
TrustOps-Env: Grader Module
============================
Provides 3 separate grading functions — one per task.
Each function returns a FLOAT score strictly within (0.01, 0.99).
OpenEnv calls these directly — they MUST return float, not objects.
"""

from models import (
    Content, Action, ActionType, Difficulty, ContentLabel,
    CONTENT_BANK
)
from engine import _compute_embedding_similarity


def safe_score(x: float) -> float:
    """Global safety clamp — guarantees output is strictly within (0.01, 0.99).
    No value may EVER be 0.0 or 1.0."""
    return max(0.01, min(float(x), 0.99))


def grade_easy_detection(content: Content, agent_action: ActionType,
                         agent_reasoning: str, agent_confidence: float) -> float:
    """
    Grader for Task 1: easy_detection (Simple Toxicity Detection).
    Returns: float score in (0.01, 0.99)
    """
    expected_action = content.expected_action

    c_score = 0.45 if agent_action == expected_action else 0.1
    a_score = 0.28 if agent_action == expected_action else 0.05

    r_score = 0.02
    toxic_words = ["toxic", "abusive", "hate", "spam", "violation", "harmful", "unsafe"]
    if any(word in agent_reasoning.lower() for word in toxic_words):
        r_score = 0.18

    penalty = 0.0
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.15
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.08

    return safe_score(c_score + a_score + r_score + penalty)


def grade_medium_classification(content: Content, agent_action: ActionType,
                                agent_reasoning: str, agent_confidence: float) -> float:
    """
    Grader for Task 2: medium_classification (Contextual Sentiment Analysis).
    Returns: float score in (0.01, 0.99)
    """
    expected_action = content.expected_action
    expected_label = content.expected_label

    c_score = 0.45 if agent_action == expected_action else 0.1
    a_score = 0.28 if agent_action == expected_action else 0.05

    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.45, 0.28

    r_score = 0.02
    context_words = ["context", "sarcastic", "satire", "frustration", "harassment", "humor", "joke"]
    if any(word in agent_reasoning.lower() for word in context_words):
        r_score += 0.08
    similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
    r_score += round(min(0.08, similarity * 0.15), 3)
    r_score = min(0.18, r_score)

    penalty = 0.0
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.15
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.08

    return safe_score(c_score + a_score + r_score + penalty)


def grade_hard_contextual(content: Content, agent_action: ActionType,
                          agent_reasoning: str, agent_confidence: float) -> float:
    """
    Grader for Task 3: hard_contextual (Multi-Turn Moderation / Coded Language).
    Returns: float score in (0.01, 0.99)
    """
    expected_action = content.expected_action
    expected_label = content.expected_label

    c_score = 0.45 if agent_action == expected_action else 0.1
    a_score = 0.28 if agent_action == expected_action else 0.05

    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.45, 0.28

    r_score = 0.02
    hard_words = ["grooming", "radicalization", "pattern", "history", "subtle",
                  "manipulation", "coded", "leaked", "whistleblower"]
    if any(word in agent_reasoning.lower() for word in hard_words):
        r_score += 0.08
    similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
    r_score += round(min(0.08, similarity * 0.25), 3)
    r_score = min(0.18, r_score)

    penalty = 0.0
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.15
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.08

    return safe_score(c_score + a_score + r_score + penalty)


def grade_task(task_name: str, content: Content, agent_action: ActionType,
               agent_reasoning: str, agent_confidence: float) -> float:
    """Unified dispatcher — routes to the correct grading function by task name."""
    if task_name == "easy_detection":
        return grade_easy_detection(content, agent_action, agent_reasoning, agent_confidence)
    elif task_name == "medium_classification":
        return grade_medium_classification(content, agent_action, agent_reasoning, agent_confidence)
    elif task_name == "hard_contextual":
        return grade_hard_contextual(content, agent_action, agent_reasoning, agent_confidence)
    else:
        return safe_score(0.5)
