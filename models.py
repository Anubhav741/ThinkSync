"""
TrustOps-Env: Data Models
=========================
Strict BaseModel (Pydantic) class hierarchy powering the moderation simulation.
Architecture Layers: Content → Observation → Action → RewardRecord → EscalationTicket

These models are the connective tissue of the entire pipeline:
- Content feeds into the Observation content_queue.
- Agent reads Observation, outputs Action.
- Grader evaluates Action, produces RewardRecord.
- Flag actions route through EscalationTicket.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime
import uuid


# ─── Enumerations ────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    APPROVE = "approve"
    REMOVE  = "remove"
    FLAG    = "flag"


class Difficulty(str, Enum):
    EASY   = "EASY"
    MEDIUM = "MEDIUM"
    HARD   = "HARD"


class ContentLabel(str, Enum):
    SAFE              = "SAFE"
    SPAM              = "SPAM"
    ABUSIVE           = "ABUSIVE"
    CONTEXT_DEPENDENT = "CONTEXT-DEPENDENT"
    AMBIGUOUS         = "AMBIGUOUS"
    CODED_LANGUAGE    = "CODED-LANGUAGE"
    WHISTLEBLOWER     = "WHISTLEBLOWER"


class EscalationStatus(str, Enum):
    PENDING  = "Pending"
    REVIEWED = "Reviewed"
    RESOLVED = "Resolved"


# ─── Core Data Models ────────────────────────────────────────────────────────

class Content(BaseModel):
    """Foundational data unit — every post entering the moderation pipeline."""
    id: str = Field(description="Unique post identifier")
    text: str = Field(description="The content text to be moderated")
    difficulty: Difficulty = Field(default=Difficulty.EASY, description="Assigned difficulty tier")
    expected_label: ContentLabel = Field(default=ContentLabel.SAFE, description="Ground-truth label for grading")
    expected_action: ActionType = Field(default=ActionType.APPROVE, description="Ideal action for this content")
    has_nuance: bool = Field(default=False, description="Whether content requires contextual reasoning")
    language_type: str = Field(default="direct", description="direct / coded / satirical")


class Observation(BaseModel):
    """Full environment state visible to the agent at any step."""
    content: str = Field(default="", description="The current content text to evaluate")
    id: str = Field(default="", description="The current content ID")
    content_queue: List[Content] = Field(default_factory=list, description="Posts awaiting moderation")
    moderation_log: List[Dict] = Field(default_factory=list, description="History of all decisions and reasoning")
    step_count: int = Field(default=0, description="Steps completed in current episode")
    cumulative_reward: float = Field(default=0.01, description="Running reward total")
    episode_active: bool = Field(default=True, description="Whether the episode is still running")
    done: bool = Field(default=False, description="Whether the episode has ended")
    metadata: Dict = Field(default_factory=dict)


class Action(BaseModel):
    """Structured output the agent produces after evaluating a Content item."""
    content_id: str = Field(description="References Content.id")
    action_type: ActionType = Field(description="approve / remove / flag")
    reasoning_chain: str = Field(default="", description="Step-by-step justification")
    confidence_score: float = Field(default=0.5, ge=0.01, le=0.99, description="Agent self-reported confidence")


class RewardRecord(BaseModel):
    """Structured reward breakdown computed by the Grader for a single task."""
    reward_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_id: str
    classification_score: float = Field(default=0.1, description="Classification accuracy score")
    action_score: float = Field(default=0.05, description="Action correctness score")
    reasoning_score: float = Field(default=0.02, description="Reasoning quality score")
    penalty_applied: float = Field(default=-0.01, description="Penalty for errors")
    total_score: int = Field(default=0, description="Net reward for this step, strictly 0 or 1")
    penalty_type: str = Field(default="none", description="none / false_negative / false_positive")


class EscalationTicket(BaseModel):
    """Created when agent flags content for human review."""
    escalation_id: str = Field(default_factory=lambda: f"ESC-{str(uuid.uuid4())[:6].upper()}")
    task_id: str
    content_text: str
    reason: str = Field(default="Low confidence / edge case")
    status: EscalationStatus = Field(default=EscalationStatus.PENDING)
    escalated_at: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# ─── Content Bank (Simulation Dataset) ──────────────────────────────────────

CONTENT_BANK: List[Content] = [
    # ── EASY Tier ──
    Content(
        id="E001", text="BUY CHEAP FOLLOWERS NOW!!! 💰💰💰 CLICK HERE!!!",
        difficulty=Difficulty.EASY, expected_label=ContentLabel.SPAM,
        expected_action=ActionType.REMOVE, has_nuance=False
    ),
    Content(
        id="E002", text="Had a great lunch today — the new café around the corner is amazing.",
        difficulty=Difficulty.EASY, expected_label=ContentLabel.SAFE,
        expected_action=ActionType.APPROVE, has_nuance=False
    ),
    Content(
        id="E003", text="FREE iPhone 16! Just send your credit card details to this link!!! 🎁🎁🎁",
        difficulty=Difficulty.EASY, expected_label=ContentLabel.SPAM,
        expected_action=ActionType.REMOVE, has_nuance=False
    ),
    Content(
        id="E004", text="Just finished reading a fascinating book about quantum computing.",
        difficulty=Difficulty.EASY, expected_label=ContentLabel.SAFE,
        expected_action=ActionType.APPROVE, has_nuance=False
    ),
    # ── MEDIUM Tier ──
    Content(
        id="M001", text="You're a worthless excuse for a human being and everyone hates you.",
        difficulty=Difficulty.MEDIUM, expected_label=ContentLabel.ABUSIVE,
        expected_action=ActionType.REMOVE, has_nuance=False
    ),
    Content(
        id="M002", text="I'm going to absolutely DESTROY you... in this chess game tonight 😂",
        difficulty=Difficulty.MEDIUM, expected_label=ContentLabel.CONTEXT_DEPENDENT,
        expected_action=ActionType.APPROVE, has_nuance=True, language_type="satirical"
    ),
    Content(
        id="M003", text="Your argument is so bad it physically hurts me to read it — try again, genius.",
        difficulty=Difficulty.MEDIUM, expected_label=ContentLabel.CONTEXT_DEPENDENT,
        expected_action=ActionType.FLAG, has_nuance=True, language_type="satirical"
    ),
    Content(
        id="M004", text="People like you should just disappear from the internet forever.",
        difficulty=Difficulty.MEDIUM, expected_label=ContentLabel.ABUSIVE,
        expected_action=ActionType.REMOVE, has_nuance=False
    ),
    # ── HARD Tier ──
    Content(
        id="H001", text="We're going to cook them tonight — can't wait for the big game!",
        difficulty=Difficulty.HARD, expected_label=ContentLabel.AMBIGUOUS,
        expected_action=ActionType.FLAG, has_nuance=True, language_type="coded"
    ),
    Content(
        id="H002", text="Those people have been poisoning the well for years and we need to clean house.",
        difficulty=Difficulty.HARD, expected_label=ContentLabel.CODED_LANGUAGE,
        expected_action=ActionType.FLAG, has_nuance=True, language_type="coded"
    ),
    Content(
        id="H003", text="LEAKED: Internal documents show executives covered up safety violations for 3 years.",
        difficulty=Difficulty.HARD, expected_label=ContentLabel.WHISTLEBLOWER,
        expected_action=ActionType.FLAG, has_nuance=True, language_type="direct"
    ),
    Content(
        id="H004", text="Let's go hunt them down after the tournament is over 🎯",
        difficulty=Difficulty.HARD, expected_label=ContentLabel.AMBIGUOUS,
        expected_action=ActionType.FLAG, has_nuance=True, language_type="coded"
    ),
]
