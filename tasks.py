"""
TrustOps-Env: Task Registry
============================
Explicitly defines and registers all 3 tasks for OpenEnv Phase 2 validation.
Each task loads its own dataset subset, runs independently, and produces its own score.

Tasks:
  1. easy_detection       — Simple toxicity / spam detection (EASY tier)
  2. medium_classification — Contextual sentiment analysis (MEDIUM tier)
  3. hard_contextual      — Multi-turn moderation / coded language (HARD tier)
"""

from typing import List, Dict, Any
from models import Content, Difficulty, CONTENT_BANK
from grader import grade_easy_detection, grade_medium_classification, grade_hard_contextual


# ─── Dataset Subsets ─────────────────────────────────────────────────────────

def get_easy_dataset() -> List[Content]:
    """Returns EASY-tier content items."""
    return [c for c in CONTENT_BANK if c.difficulty == Difficulty.EASY]


def get_medium_dataset() -> List[Content]:
    """Returns MEDIUM-tier content items."""
    return [c for c in CONTENT_BANK if c.difficulty == Difficulty.MEDIUM]


def get_hard_dataset() -> List[Content]:
    """Returns HARD-tier content items."""
    return [c for c in CONTENT_BANK if c.difficulty == Difficulty.HARD]


# ─── Task Definitions ───────────────────────────────────────────────────────

TASK_REGISTRY: Dict[str, Dict[str, Any]] = {
    "easy_detection": {
        "id": "easy_detection",
        "name": "Easy Detection",
        "description": "Simple toxicity and spam detection",
        "difficulty": "EASY",
        "dataset_loader": get_easy_dataset,
        "grader": grade_easy_detection,
    },
    "medium_classification": {
        "id": "medium_classification",
        "name": "Medium Classification",
        "description": "Contextual sentiment analysis — sarcasm vs harassment",
        "difficulty": "MEDIUM",
        "dataset_loader": get_medium_dataset,
        "grader": grade_medium_classification,
    },
    "hard_contextual": {
        "id": "hard_contextual",
        "name": "Hard Contextual",
        "description": "Multi-turn moderation with coded language detection",
        "difficulty": "HARD",
        "dataset_loader": get_hard_dataset,
        "grader": grade_hard_contextual,
    },
}


def list_tasks() -> List[str]:
    """Returns all registered task IDs for validator discovery."""
    return list(TASK_REGISTRY.keys())


def get_task(task_id: str) -> Dict[str, Any]:
    """Returns task definition by ID."""
    if task_id not in TASK_REGISTRY:
        raise ValueError(f"Unknown task: {task_id}. Available: {list_tasks()}")
    return TASK_REGISTRY[task_id]


def get_all_tasks() -> Dict[str, Dict[str, Any]]:
    """Returns the full task registry."""
    return TASK_REGISTRY
