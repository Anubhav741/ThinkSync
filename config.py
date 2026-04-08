import yaml
import os

def load_config():
    """
    Loads environment-driven configurations with zero hardcoding in logic.
    Values can be overridden via environment variables or openenv.yaml.
    """
    
    # ── Expert Reasoning Embeddings (Simulated) ──
    # Default reasoning for grading similarity logic
    EXPERT_REASONING = {
        "SPAM": os.getenv("REASONING_SPAM", "Content exhibits classic spam indicators: all-caps text, excessive punctuation, urgency language, and suspicious URLs."),
        "SAFE": os.getenv("REASONING_SAFE", "Content is benign personal expression with no policy violations, harmful intent, or misleading information."),
        "ABUSIVE": os.getenv("REASONING_ABUSIVE", "Content contains direct personal attacks, dehumanizing language, or explicit threats targeting an individual."),
        "CONTEXT-DEPENDENT": os.getenv("REASONING_CONTEXT", "Content uses aggressive or violent language but within a clearly non-harmful context like gaming or humor."),
        "AMBIGUOUS": os.getenv("REASONING_AMBIGUOUS", "Content uses language that could be interpreted as threatening but requires more context for binary classification."),
        "CODED-LANGUAGE": os.getenv("REASONING_CODED", "Content employs metaphorical phrases that may function as dog-whistles or veiled hate speech."),
        "WHISTLEBLOWER": os.getenv("REASONING_WHISTLEBLOWER", "Content appears to contain leaked confidential information exposing potential misconduct.")
    }

    # ── Spam Detection Patterns ──
    SPAM_PATTERNS = [
        r"buy\s+(cheap|free|now)",
        r"click\s+here",
        r"free\s+(iphone|gift|money|prize)",
        r"send\s+(your|ur)\s+(credit\s+card|bank|password)",
        r"(💰|🎁|🎯){2,}",
        r"!!!+",
        r"(follow(ers)?|likes?|subscribers?)\s*(for\s*)?(free|cheap|sale|now)",
    ]

    # ── Abuse Detection Patterns ──
    ABUSE_PATTERNS = [
        r"worthless\s+(excuse|human|person|piece)",
        r"everyone\s+hates\s+you",
        r"(should|need\s+to)\s+(just\s+)?(disappear|die|kill)",
        r"(scum|trash|garbage|waste)\s+of\s+(a\s+)?(human|person|society)",
    ]

    # ── Contextual Signals (Softeners) ──
    THREAT_SOFTENERS = [
        r"(chess|game|tournament|match|contest|competition)",
        r"(😂|🤣|😄|😆|lol|lmao|haha|jk|just\s+kidding)",
        r"(sports?|team|season|play(ing|s)?|score)",
    ]

    # ── Thresholds ──
    SPAM_THRESHOLD = float(os.getenv("SPAM_THRESHOLD", "0.4"))
    ABUSE_THRESHOLD = float(os.getenv("ABUSE_THRESHOLD", "0.3"))
    SAFE_MAX_TOXICITY = float(os.getenv("SAFE_MAX_TOXICITY", "0.05"))

    return {
        "expert_reasoning": EXPERT_REASONING,
        "spam_patterns": SPAM_PATTERNS,
        "abuse_patterns": ABUSE_PATTERNS,
        "threat_softeners": THREAT_SOFTENERS,
        "spam_threshold": SPAM_THRESHOLD,
        "abuse_threshold": ABUSE_THRESHOLD,
        "safe_max_threshold": SAFE_MAX_TOXICITY
    }

CONFIG = load_config()
