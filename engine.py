"""
TrustOps-Env: Classification & Grading Engine
==============================================
Implements the multi-layered evaluation pipeline:
  Layer 1 → Content Classification (EASY/MEDIUM/HARD heuristics)
  Layer 2 → Action Grading (+0.5 / +0.3 / +0.2 reward matrix)
  Layer 3 → Embedding Similarity (simulated cosine similarity for reasoning quality)
  Layer 4 → Penalty Computation (-0.2 False Negative / -0.1 False Positive)

Security: All external API access through os.getenv("HF_TOKEN").
"""

import os
import re
import math
import random
from typing import Tuple, Dict, List
from models import (
    Content, Action, RewardRecord, EscalationTicket,
    ActionType, Difficulty, ContentLabel, EscalationStatus
)

# ─── Secure Environment ─────────────────────────────────────────────────────
HF_TOKEN = os.getenv("HF_TOKEN", "")

# ─── Expert Reasoning Embeddings (Simulated) ────────────────────────────────
# In production, these would be real sentence-transformer embeddings.
# Here we store reference reasoning strings per label for similarity scoring.
EXPERT_REASONING: Dict[str, str] = {
    "SPAM": "Content exhibits classic spam indicators: all-caps text, excessive punctuation, urgency language, and suspicious URLs. Binary classification with high confidence.",
    "SAFE": "Content is benign personal expression with no policy violations, harmful intent, or misleading information. Standard safe-to-publish classification.",
    "ABUSIVE": "Content contains direct personal attacks, dehumanizing language, or explicit threats targeting an individual. Violates hate speech and harassment policies.",
    "CONTEXT-DEPENDENT": "Content uses aggressive or violent language but within a clearly non-harmful context such as gaming, sports, or humor. Requires contextual interpretation of tone and intent.",
    "AMBIGUOUS": "Content uses language that could be interpreted as threatening or harmful but may also be colloquial slang, sports terminology, or cultural expression. Insufficient context for confident binary classification. Escalation recommended.",
    "CODED-LANGUAGE": "Content employs metaphorical or coded phrases that may function as dog-whistles or veiled hate speech to in-group audiences while appearing benign to outsiders. Requires specialized cultural and linguistic analysis.",
    "WHISTLEBLOWER": "Content appears to contain leaked confidential information exposing potential misconduct. Legal and ethical analysis required — content may be critically important public interest material or may violate privacy and confidentiality laws."
}


# ─── Spam Detection Patterns ────────────────────────────────────────────────
SPAM_PATTERNS = [
    r"buy\s+(cheap|free|now)",
    r"click\s+here",
    r"free\s+(iphone|gift|money|prize)",
    r"send\s+(your|ur)\s+(credit\s+card|bank|password)",
    r"(💰|🎁|🎯){2,}",
    r"!!!+",
    r"(follow(ers)?|likes?|subscribers?)\s*(for\s*)?(free|cheap|sale|now)",
]

ABUSE_PATTERNS = [
    r"worthless\s+(excuse|human|person|piece)",
    r"everyone\s+hates\s+you",
    r"(should|need\s+to)\s+(just\s+)?(disappear|die|kill)",
    r"(scum|trash|garbage|waste)\s+of\s+(a\s+)?(human|person|society)",
]

THREAT_SOFTENERS = [
    r"(chess|game|tournament|match|contest|competition)",
    r"(😂|🤣|😄|😆|lol|lmao|haha|jk|just\s+kidding)",
    r"(sports?|team|season|play(ing|s)?|score)",
]


def _compute_spam_score(text: str) -> float:
    """Returns 0.0–1.0 spam probability based on pattern matching."""
    text_lower = text.lower()
    hits = sum(1 for p in SPAM_PATTERNS if re.search(p, text_lower))
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    exclaim_ratio = text.count("!") / max(len(text), 1)
    
    score = min(1.0, (hits * 0.25) + (caps_ratio * 0.3) + (exclaim_ratio * 0.5))
    return round(score, 3)


def _compute_toxicity_score(text: str) -> float:
    """Simulated toxicity baseline — in production this would call HF Toxicity Model."""
    text_lower = text.lower()
    hits = sum(1 for p in ABUSE_PATTERNS if re.search(p, text_lower))
    
    # Check for aggressive vocabulary
    aggressive_words = ["hate", "destroy", "kill", "die", "hurt", "attack", "fight", "loser", "idiot", "stupid", "worthless"]
    word_hits = sum(1 for w in aggressive_words if w in text_lower)
    
    # Check for softeners that reduce toxicity
    softener_hits = sum(1 for p in THREAT_SOFTENERS if re.search(p, text_lower))
    
    raw = min(1.0, (hits * 0.35) + (word_hits * 0.08))
    softened = max(0.0, raw - (softener_hits * 0.15))
    return round(softened, 3)


def _compute_embedding_similarity(agent_reasoning: str, label: str) -> float:
    """
    Simulated cosine similarity between agent reasoning and expert reasoning.
    In production: encode both with sentence-transformers, compute cosine similarity.
    Here we use word-overlap as a lightweight proxy.
    """
    if label not in EXPERT_REASONING:
        return 0.0
    
    expert = EXPERT_REASONING[label].lower().split()
    agent_words = agent_reasoning.lower().split()
    
    if not agent_words:
        return 0.0
    
    # Jaccard-like similarity with position weighting
    expert_set = set(expert)
    agent_set = set(agent_words)
    intersection = expert_set & agent_set
    union = expert_set | agent_set
    
    jaccard = len(intersection) / max(len(union), 1)
    
    # Boost for key technical terms
    key_terms = {"policy", "classification", "confidence", "context", "escalation",
                 "harmful", "safe", "reasoning", "analysis", "nuance", "cultural",
                 "coded", "satirical", "threat", "spam", "violation", "pattern"}
    term_bonus = sum(0.03 for t in key_terms if t in agent_set)
    
    similarity = min(1.0, jaccard + term_bonus)
    return round(similarity, 3)


# ─── Classification Engine ──────────────────────────────────────────────────

def classify_content(content: Content) -> Tuple[ContentLabel, ActionType, str, float, Dict]:
    """
    Multi-layer classification pipeline.
    
    Returns:
        (label, recommended_action, reasoning_chain, confidence, metrics_dict)
    
    Pipeline:
        1. Spam scoring (Rule-based / Regex)
        2. Toxicity baseline (Simulated HF Model)
        3. Contextual softener analysis
        4. Difficulty-aware decision routing
    """
    text = content.text
    text_lower = text.lower()
    
    spam_score = _compute_spam_score(text)
    toxicity_score = _compute_toxicity_score(text)
    softener_hits = sum(1 for p in THREAT_SOFTENERS if re.search(p, text_lower))
    
    metrics = {
        "spam_probability": spam_score,
        "toxicity_baseline": toxicity_score,
        "softener_signals": softener_hits,
        "text_length": len(text),
        "caps_ratio": round(sum(1 for c in text if c.isupper()) / max(len(text), 1), 3),
    }
    
    # ── EASY: Spam Detection ──
    if spam_score > 0.4:
        reasoning = (
            f"[Rule-Based Grader] Spam probability: {spam_score:.1%}. "
            f"Content exhibits classic spam indicators — urgency language, excessive punctuation, "
            f"suspicious link patterns. Binary classification with high confidence. "
            f"Action: REMOVE (policy violation — spam)."
        )
        return ContentLabel.SPAM, ActionType.REMOVE, reasoning, 0.95, metrics
    
    # ── EASY: Clear Safe Content ──
    if toxicity_score < 0.05 and spam_score < 0.1 and not content.has_nuance:
        reasoning = (
            f"[Rule-Based Grader] Toxicity baseline: {toxicity_score:.1%}, Spam: {spam_score:.1%}. "
            f"Content is benign personal expression with no policy violations or harmful intent. "
            f"Standard safe-to-publish classification. Action: APPROVE."
        )
        return ContentLabel.SAFE, ActionType.APPROVE, reasoning, 0.92, metrics
    
    # ── MEDIUM: Clear Abuse ──
    if toxicity_score > 0.3 and softener_hits == 0:
        reasoning = (
            f"[Policy-Matching Grader] Toxicity baseline: {toxicity_score:.1%}. "
            f"Content contains direct personal attacks or dehumanizing language with zero contextual softeners. "
            f"Violates hate speech and harassment policies. "
            f"Cross-referenced against platform Terms of Service. Action: REMOVE."
        )
        return ContentLabel.ABUSIVE, ActionType.REMOVE, reasoning, 0.85, metrics
    
    # ── MEDIUM: Satire / Sarcasm with softeners ──
    if toxicity_score > 0.1 and softener_hits >= 1:
        confidence = 0.65 + (softener_hits * 0.08)
        if confidence > 0.75:
            reasoning = (
                f"[Policy-Matching Grader] Toxicity: {toxicity_score:.1%}, Softeners detected: {softener_hits}. "
                f"Content uses aggressive or violent language but within a clearly non-harmful context "
                f"(gaming, sports, humor). Contextual interpretation of tone and intent confirms satire. "
                f"Action: APPROVE (context-dependent safe)."
            )
            return ContentLabel.CONTEXT_DEPENDENT, ActionType.APPROVE, reasoning, round(confidence, 2), metrics
        else:
            reasoning = (
                f"[Policy-Matching Grader] Toxicity: {toxicity_score:.1%}, Softeners: {softener_hits}. "
                f"Aggressive language detected with partial contextual softeners. "
                f"Confidence ({confidence:.0%}) is below the decision threshold for binary action. "
                f"Borderline content on policy boundary — escalation recommended. "
                f"Action: FLAG (insufficient confidence for safe binary decision)."
            )
            return ContentLabel.CONTEXT_DEPENDENT, ActionType.FLAG, reasoning, round(confidence, 2), metrics
    
    # ── HARD: Coded Language / Metaphorical threats ──
    coded_indicators = ["poison", "clean house", "hunt", "cook them", "take them out", "deal with them"]
    if any(ind in text_lower for ind in coded_indicators):
        reasoning = (
            f"[Embedding Similarity Grader] Content employs metaphorical or coded phrases that may "
            f"function as veiled hate speech or colloquial slang. Toxicity baseline: {toxicity_score:.1%}. "
            f"Insufficient context for confident binary classification. "
            f"Deep contextual reasoning required — cultural sensitivity analysis needed. "
            f"Confidence below 50% threshold. Action: FLAG (strategic escalation)."
        )
        # Check for specific coded language vs ambiguous
        if any(w in text_lower for w in ["poison", "clean house"]):
            return ContentLabel.CODED_LANGUAGE, ActionType.FLAG, reasoning, 0.35, metrics
        return ContentLabel.AMBIGUOUS, ActionType.FLAG, reasoning, 0.40, metrics
    
    # ── HARD: Whistleblower Content ──
    whistleblower_indicators = ["leaked", "internal documents", "cover", "violations", "expose", "whistleblow"]
    if any(ind in text_lower for ind in whistleblower_indicators):
        reasoning = (
            f"[Embedding Similarity Grader] Content appears to contain leaked confidential information "
            f"exposing potential misconduct. Legal and ethical analysis required — content may be "
            f"critically important public interest material OR may violate privacy and confidentiality laws. "
            f"Binary approve/remove carries extreme risk. Action: FLAG (legal escalation required)."
        )
        return ContentLabel.WHISTLEBLOWER, ActionType.FLAG, reasoning, 0.30, metrics
    
    # ── Fallback: Low-confidence safe ──
    reasoning = (
        f"[Rule-Based Grader] No strong signals detected. Spam: {spam_score:.1%}, "
        f"Toxicity: {toxicity_score:.1%}. Content appears benign but may warrant further "
        f"monitoring. Action: APPROVE (default safe classification)."
    )
    return ContentLabel.SAFE, ActionType.APPROVE, reasoning, 0.70, metrics


# ─── Grading Pipeline ───────────────────────────────────────────────────────

def grade_action(
    content: Content,
    agent_action: ActionType,
    agent_reasoning: str,
    agent_confidence: float
) -> RewardRecord:
    """
    Multi-layered evaluation pipeline.
    
    Tier-aware grading:
      EASY   → Rule-based label matching (no reasoning eval)
      MEDIUM → Policy-matching + initial reasoning assessment
      HARD   → Full embedding similarity evaluation
    
    Returns a complete RewardRecord.
    """
    difficulty = content.difficulty
    expected_action = content.expected_action
    expected_label = content.expected_label
    
    # ── Classification Score (+0.5) ──
    # SECURITY FIX: Removed the flag-everything hack.
    classification_correct = (agent_action == expected_action)
    c_score = 0.5 if classification_correct else 0.0
    
    # ── Action Score (+0.3) ──
    action_correct = (agent_action == expected_action)
    a_score = 0.3 if action_correct else 0.0
    
    # Flag on genuinely ambiguous content earns full marks
    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.5, 0.3
    
    # ── Reasoning Quality Score (+0.2) ──
    r_score = 0.0
    
    # ENHANCED TASK & GRADER LOGIC
    # Final decision gives c_score(0.5) + a_score(0.3) = 0.8
    if difficulty == Difficulty.EASY:
        # Task 1 (Easy): Simple Toxicity Detection
        # +0.2 partial reward for correctly identifying toxic/abusive flags in reasoning.
        toxic_words = ["toxic", "abusive", "hate", "spam", "violation"]
        word_found = any(word in agent_reasoning.lower() for word in toxic_words)
        if word_found:
            r_score = 0.2

    elif difficulty == Difficulty.MEDIUM:
        # Task 2 (Medium): Contextual Sentiment Analysis
        # Agent must distinguish between "sarcastic frustration" (allow) and "targeted harassment" (block).
        # We give partial points based on capturing context in the reasoning.
        context_words = ["context", "sarcastic", "satire", "frustration", "harassment", "humor", "joke"]
        if any(word in agent_reasoning.lower() for word in context_words):
             r_score += 0.1
        similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
        r_score += round(min(0.1, similarity * 0.15), 3)
        r_score = min(0.2, r_score)

    elif difficulty == Difficulty.HARD:
        # Task 3 (Hard): Multi-Turn Moderation
        # Agent must analyze conversation history to find subtle grooming or radicalization patterns.
        # We check for deeper reasoning analysis.
        hard_words = ["grooming", "radicalization", "pattern", "history", "subtle", "manipulation", "coded", "leaked", "whistleblower"]
        if any(word in agent_reasoning.lower() for word in hard_words):
             r_score += 0.1
        similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
        r_score += round(min(0.1, similarity * 0.25), 3)
        r_score = min(0.2, r_score)

    # ── Penalty Computation ──
    penalty = 0.0
    penalty_type = "none"
    
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.2  # FALSE NEGATIVE — most dangerous failure
        penalty_type = "false_negative"
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.1  # FALSE POSITIVE — user trust erosion
        penalty_type = "false_positive"
    
    total = round(c_score + a_score + r_score + penalty, 3)
    
    return RewardRecord(
        task_id=content.id,
        classification_score=c_score,
        action_score=a_score,
        reasoning_score=r_score,
        penalty_applied=penalty,
        total_score=total,
        penalty_type=penalty_type
    )


# ─── Escalation Pipeline ────────────────────────────────────────────────────

def create_escalation(content: Content, reasoning: str) -> EscalationTicket:
    """Creates an escalation ticket when agent flags content for human review."""
    
    if content.expected_label == ContentLabel.WHISTLEBLOWER:
        reason = "Legal/ethical review required — potential whistleblower material"
    elif content.expected_label == ContentLabel.CODED_LANGUAGE:
        reason = "Coded language analysis required — potential veiled hate speech"
    elif content.expected_label == ContentLabel.AMBIGUOUS:
        reason = "Low confidence on ambiguous content — cultural/contextual nuance"
    elif content.expected_label == ContentLabel.CONTEXT_DEPENDENT:
        reason = "Borderline content on policy boundary — satire vs threat ambiguity"
    else:
        reason = "Agent confidence below decision threshold"
    
    return EscalationTicket(
        task_id=content.id,
        content_text=content.text,
        reason=reason
    )


# ─── OpenEnv Interface ──────────────────────────────────────────────────────

from models import Observation, CONTENT_BANK

class MyEnv:
    """
    OpenEnv compatible class that wraps the moderation engine.
    Implements reset(), step(action), and state().
    """
    def __init__(self):
        self._state = Observation()
        self._is_done = False

    def reset(self) -> Observation:
        """Resets the environment and returns the initial state."""
        self._state = Observation(
            content_queue=list(CONTENT_BANK),
            moderation_log=[],
            step_count=0,
            cumulative_reward=0.0,
            episode_active=True
        )
        self._is_done = False
        return self._state

    def step(self, action: Action) -> Tuple[Observation, float, bool, Dict]:
        """
        Takes an Action object (Pydantic model) and advances the environment.
        Returns: (state, reward_score, done, info_dict)
        """
        if not self._state.episode_active or not self._state.content_queue:
            self._is_done = True
            self._state.episode_active = False
            return self._state, 0.0, True, {}

        # Default reward if content is invalid
        reward_score = 0.0

        content = next((c for c in self._state.content_queue if c.id == action.content_id), None)
        if content:
            # Grade action
            reward: RewardRecord = grade_action(
                content=content,
                agent_action=action.action_type,
                agent_reasoning=action.reasoning_chain,
                agent_confidence=action.confidence_score
            )
            reward_score = reward.total_score
            self._state.cumulative_reward += reward_score
            self._state.step_count += 1
            self._state.moderation_log.append({"action": action.dict(), "reward": reward.dict()})
            
            # Remove from queue
            self._state.content_queue = [c for c in self._state.content_queue if c.id != content.id]
        
        if not self._state.content_queue:
            self._state.episode_active = False
            self._is_done = True

        return self._state, reward_score, self._is_done, {}

    def state(self) -> Observation:
        """Returns the current structural state of the environment."""
        return self._state
