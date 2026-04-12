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
from typing import Tuple, Dict, List, Any, Union
from models import (
    Content, Action, RewardRecord, EscalationTicket,
    ActionType, Difficulty, ContentLabel, EscalationStatus
)

# ─── Secure Environment ─────────────────────────────────────────────────────
from config import CONFIG

# ─── Secure Environment ─────────────────────────────────────────────────────
HF_TOKEN = os.getenv("HF_TOKEN", "")

# ─── Configuration Proxies ───
EXPERT_REASONING = CONFIG["expert_reasoning"]
SPAM_PATTERNS   = CONFIG["spam_patterns"]
ABUSE_PATTERNS  = CONFIG["abuse_patterns"]
THREAT_SOFTENERS = CONFIG["threat_softeners"]


def _compute_spam_score(text: str) -> float:
    """Returns 0.0–1.0 spam probability based on pattern matching."""
    text_lower = text.lower()
    hits = sum(1 for p in SPAM_PATTERNS if re.search(p, text_lower))
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    exclaim_ratio = text.count("!") / max(len(text), 1)
    
    score = min(0.99, (hits * 0.25) + (caps_ratio * 0.3) + (exclaim_ratio * 0.5))
    return round(max(0.01, score), 3)


def _compute_toxicity_score(text: str) -> float:
    """Simulated toxicity baseline — in production this would call HF Toxicity Model."""
    text_lower = text.lower()
    hits = sum(1 for p in ABUSE_PATTERNS if re.search(p, text_lower))
    
    # Check for aggressive vocabulary
    aggressive_words = ["hate", "destroy", "kill", "die", "hurt", "attack", "fight", "loser", "idiot", "stupid", "worthless"]
    word_hits = sum(1 for w in aggressive_words if w in text_lower)
    
    # Check for softeners that reduce toxicity
    softener_hits = sum(1 for p in THREAT_SOFTENERS if re.search(p, text_lower))
    
    raw = min(0.99, (hits * 0.35) + (word_hits * 0.08))
    softened = max(0.01, raw - (softener_hits * 0.15))
    return round(softened, 3)


def _compute_embedding_similarity(agent_reasoning: str, label: str) -> float:
    """
    Simulated cosine similarity between agent reasoning and expert reasoning.
    In production: encode both with sentence-transformers, compute cosine similarity.
    Here we use word-overlap as a lightweight proxy.
    """
    if label not in EXPERT_REASONING:
        return 0.01
    
    expert = EXPERT_REASONING[label].lower().split()
    agent_words = agent_reasoning.lower().split()
    
    if not agent_words:
        return 0.01
    
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
    
    similarity = min(0.99, jaccard + term_bonus)
    return round(max(0.01, similarity), 3)


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
    if spam_score > CONFIG["spam_threshold"]:
        reasoning = (
            f"[Rule-Based Grader] Spam probability: {spam_score:.1%}. "
            f"Content exhibits classic spam indicators — urgency language, excessive punctuation, "
            f"suspicious link patterns. Binary classification with high confidence. "
            f"Action: REMOVE (policy violation — spam)."
        )
        return ContentLabel.SPAM, ActionType.REMOVE, reasoning, 0.95, metrics
    
    # ── EASY: Clear Safe Content ──
    if toxicity_score < CONFIG["safe_max_threshold"] and spam_score < 0.1 and not content.has_nuance:
        reasoning = (
            f"[Rule-Based Grader] Toxicity baseline: {toxicity_score:.1%}, Spam: {spam_score:.1%}. "
            f"Content is benign personal expression with no policy violations or harmful intent. "
            f"Standard safe-to-publish classification. Action: APPROVE."
        )
        return ContentLabel.SAFE, ActionType.APPROVE, reasoning, 0.92, metrics
    
    # ── MEDIUM: Clear Abuse ──
    if toxicity_score > CONFIG["abuse_threshold"] and softener_hits == 0:
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
    
    # ── Classification Score
    # SECURITY FIX: Removed the flag-everything hack.
    classification_correct = (agent_action == expected_action)
    c_score = 0.45 if classification_correct else 0.1
    
    # ── Action Score
    action_correct = (agent_action == expected_action)
    a_score = 0.28 if action_correct else 0.05
    
    # Flag on genuinely ambiguous content earns marks
    if expected_action == ActionType.FLAG and agent_action == ActionType.FLAG:
        c_score, a_score = 0.45, 0.28
    
    # ── Reasoning Quality Score
    r_score = 0.02
    
    # ENHANCED TASK & GRADER LOGIC
    if difficulty == Difficulty.EASY:
        toxic_words = ["toxic", "abusive", "hate", "spam", "violation"]
        word_found = any(word in agent_reasoning.lower() for word in toxic_words)
        if word_found:
            r_score = 0.18

    elif difficulty == Difficulty.MEDIUM:
        context_words = ["context", "sarcastic", "satire", "frustration", "harassment", "humor", "joke"]
        if any(word in agent_reasoning.lower() for word in context_words):
             r_score += 0.08
        similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
        r_score += round(min(0.08, similarity * 0.15), 3)
        r_score = min(0.18, r_score)

    elif difficulty == Difficulty.HARD:
        hard_words = ["grooming", "radicalization", "pattern", "history", "subtle", "manipulation", "coded", "leaked", "whistleblower"]
        if any(word in agent_reasoning.lower() for word in hard_words):
             r_score += 0.08
        similarity = _compute_embedding_similarity(agent_reasoning, expected_label.value)
        r_score += round(min(0.08, similarity * 0.25), 3)
        r_score = min(0.18, r_score)

    # ── Penalty Computation ──
    penalty = 0.0
    penalty_type = "none"
    
    if expected_action == ActionType.REMOVE and agent_action == ActionType.APPROVE:
        penalty = -0.15  # FALSE NEGATIVE — most dangerous failure
        penalty_type = "false_negative"
    elif expected_action == ActionType.APPROVE and agent_action == ActionType.REMOVE:
        penalty = -0.08  # FALSE POSITIVE — user trust erosion
        penalty_type = "false_positive"
    
    total = round(c_score + a_score + r_score + penalty, 3)
    # MANDATORY CLAMP — never return exactly 0.0 or 1.0
    total = max(0.01, min(float(total), 0.99))
    
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
    OpenEnv-compliant class that wraps the moderation engine.
    Implements reset(), step(action), and state().
    """
    def __init__(self):
        self._state = Observation()
        self._is_done = False

    def reset(self) -> Dict:
        """Resets the environment and returns the initial state formatted for OpenEnv."""
        self._state = Observation(
            id=CONTENT_BANK[0].id,
            content=CONTENT_BANK[0].text,
            content_queue=list(CONTENT_BANK),
            moderation_log=[],
            step_count=0,
            cumulative_reward=0.0,
            episode_active=True,
            done=False,
            metadata={"version": "1.0.0"}
        )
        self._is_done = False
        return {"observation": self._state.model_dump() if hasattr(self._state, "model_dump") else self._state.dict()}

    def step(self, action: Any) -> Dict:
        """
        Takes an Action (dict or object) and advances the environment.
        Returns: { "observation": ..., "reward": ..., "done": ..., "info": ... }
        """
        from models import Action, ActionType
        
        # Convert dict input to Action if necessary
        if isinstance(action, dict):
            try:
                action_obj = Action(**action)
            except:
                action_obj = Action(
                    content_id=action.get("content_id", ""),
                    action_type=ActionType(action.get("action_type", "flag")),
                    reasoning_chain=action.get("reasoning_chain", ""),
                    confidence_score=float(action.get("confidence_score", 0.5))
                )
        else:
            action_obj = action

        if not self._state.episode_active or not self._state.content_queue:
            self._state.done = True
            print(f"[END] success=True total_steps={self._state.step_count} final_score={self._state.cumulative_reward:.3f}")
            return {
                "observation": self._state.model_dump() if hasattr(self._state, "model_dump") else self._state.dict(),
                "reward": 0.01,
                "done": True,
                "info": {}
            }

        reward_score = 0.01
        content = next((c for c in self._state.content_queue if c.id == action_obj.content_id), None)
        
        if content:
            reward_rec = grade_action(
                content=content,
                agent_action=action_obj.action_type,
                agent_reasoning=action_obj.reasoning_chain,
                agent_confidence=action_obj.confidence_score
            )
            reward_score = reward_rec.total_score
            self._state.cumulative_reward += reward_score
            self._state.step_count += 1
            _action_data = action_obj.model_dump() if hasattr(action_obj, "model_dump") else action_obj.dict()
            _reward_data = reward_rec.model_dump() if hasattr(reward_rec, "model_dump") else reward_rec.dict()
            self._state.moderation_log.append({"action": _action_data, "reward": _reward_data})
            self._state.content_queue = [c for c in self._state.content_queue if c.id != content.id]

        # Update next observation
        if self._state.content_queue:
            self._state.id = self._state.content_queue[0].id
            self._state.content = self._state.content_queue[0].text
        else:
            self._state.id = ""
            self._state.content = ""
            self._state.done = True
            self._state.episode_active = False
            print(f"[END] success=True total_steps={self._state.step_count} final_score={self._state.cumulative_reward:.3f}")

        # MANDATORY: clamp reward to (0.01, 0.99) — never 0.0 or 1.0
        clamped_reward = max(0.01, min(float(reward_score), 0.99))
        return {
            "observation": self._state.model_dump() if hasattr(self._state, "model_dump") else self._state.dict(),
            "reward": clamped_reward,
            "done": bool(self._state.done),
            "info": {}
        }

    def state(self) -> Observation:
        """Returns the current structural state for UI dashboard purposes."""
        return self._state
