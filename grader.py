"""
TrustOps-Env: Grader Module
============================
Provides 3 separate grading functions — one per task.
All scores are clamped to (0.01, 0.99) to satisfy OpenEnv Phase 2 validation.
"""

from models import (
    Content, Action, ActionType, Difficulty, ContentLabel, RewardRecord,
    CONTENT_BANK
)
from engine import _compute_embedding_similarity


def _clamp(score: float) -> float:
    """Clamp score to strictly (0.01, 0.99) — never 0.0 or 1.0."""
    return max(0.01, min(score, 0.99))


def grade_easy_detection(content: Content, agent_action: ActionType,
                         agent_reasoning: str, agent_confidence: float) -> RewardRecord:
    """
    Grader for Task 1: easy_detection (Simple Toxicity Detection).
    Rule-based label matching — no reasoning eval.
    """
    expected_action = content.expected_action

    # Classification score (+0.5)
    c_score = 0.5 if agent_action == expected_action else 0.0

    # Action score (+0.3)
    a_score = 0.3 if agent_action == expected_action else 0.0

    # Reasoning quality (+0.2)
    r_score = 0.0
    toxic_words = ["toxic", "abusive", "hate", "spam", "violation", "harmful", "unsafe"]
    if any(word in agent_reasoning.lower() for word in toxic_words):
        r_score = 0.2

    # Penalty
    penalty = 0.0
    penalty_type = "none"
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.2
        penalty_type = "false_negative"
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.1
        penalty_type = "false_positive"

    total = _clamp(c_score + a_score + r_score + penalty)

    return RewardRecord(
        task_id=content.id,
        classification_score=c_score,
        action_score=a_score,
        reasoning_score=r_score,
        penalty_applied=penalty,
        total_score=total,
        penalty_type=penalty_type
    )


def grade_medium_classification(content: Content, agent_action: ActionType,
                                agent_reasoning: str, agent_confidence: float) -> RewardRecord:
    """
    Grader for Task 2: medium_classification (Contextual Sentiment Analysis).
    Policy-matching + initial reasoning assessment.
    """
    expected_action = content.expected_action
    expected_label = content.expected_label

    # Classification score (+0.5)
    c_score = 0.5 if agent_action == expected_action else 0.0

    # Action score (+0.3)
    a_score = 0.3 if agent_action == expected_action else 0.0

    # Flag on genuinely ambiguous content earns full marks
    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.5, 0.3

    # Reasoning quality (+0.2)
    r_score = 0.0
    context_words = ["context", "sarcastic", "satire", "frustration", "harassment", "humor", "joke"]
    if any(word in agent_reasoning.lower() for word in context_words):
        r_score += 0.1
    similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
    r_score += round(min(0.1, similarity * 0.15), 3)
    r_score = min(0.2, r_score)

    # Penalty
    penalty = 0.0
    penalty_type = "none"
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.2
        penalty_type = "false_negative"
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.1
        penalty_type = "false_positive"

    total = _clamp(c_score + a_score + r_score + penalty)

    return RewardRecord(
        task_id=content.id,
        classification_score=c_score,
        action_score=a_score,
        reasoning_score=r_score,
        penalty_applied=penalty,
        total_score=total,
        penalty_type=penalty_type
    )


def grade_hard_contextual(content: Content, agent_action: ActionType,
                          agent_reasoning: str, agent_confidence: float) -> RewardRecord:
    """
    Grader for Task 3: hard_contextual (Multi-Turn Moderation / Coded Language).
    Full embedding similarity evaluation.
    """
    expected_action = content.expected_action
    expected_label = content.expected_label

    # Classification score (+0.5)
    c_score = 0.5 if agent_action == expected_action else 0.0

    # Action score (+0.3)
    a_score = 0.3 if agent_action == expected_action else 0.0

    # Flag on genuinely ambiguous content earns full marks
    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.5, 0.3

    # Reasoning quality (+0.2)
    r_score = 0.0
    hard_words = ["grooming", "radicalization", "pattern", "history", "subtle",
                  "manipulation", "coded", "leaked", "whistleblower"]
    if any(word in agent_reasoning.lower() for word in hard_words):
        r_score += 0.1
    similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
    r_score += round(min(0.1, similarity * 0.25), 3)
    r_score = min(0.2, r_score)

    # Penalty
    penalty = 0.0
    penalty_type = "none"
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.2
        penalty_type = "false_negative"
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.1
        penalty_type = "false_positive"

    total = _clamp(c_score + a_score + r_score + penalty)

    return RewardRecord(
        task_id=content.id,
        classification_score=c_score,
        action_score=a_score,
        reasoning_score=r_score,
        penalty_applied=penalty,
        total_score=total,
        penalty_type=penalty_type
    )


def grade_task(task_name: str, content: Content, agent_action: ActionType,
               agent_reasoning: str, agent_confidence: float) -> RewardRecord:
    """Unified dispatcher — routes to the correct grading function by task name."""
    if task_name == "easy_detection":
        return grade_easy_detection(content, agent_action, agent_reasoning, agent_confidence)
    elif task_name == "medium_classification":
        return grade_medium_classification(content, agent_action, agent_reasoning, agent_confidence)
    elif task_name == "hard_contextual":
        return grade_hard_contextual(content, agent_action, agent_reasoning, agent_confidence)
    else:
        raise ValueError(f"Unknown task: {task_name}")
