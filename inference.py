"""
TrustOps-Env: Baseline Inference
=================================
Uses the OpenAI-compatible client to call Qwen2.5-72B-Instruct via HuggingFace Router.
Emits [START], [STEP], and [END] logs for OpenEnv evaluation.
Runs ALL 3 tasks sequentially: easy_detection → medium_classification → hard_contextual.
Runtime target: < 20 minutes.
"""

import os
import time
import json
import warnings
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except ImportError:
    pass

from openai import OpenAI

from models import Action, ActionType, Difficulty, Content
from tasks import list_tasks, get_task, TASK_REGISTRY

# ─── API Configuration (all values read from environment — never hardcoded) ───
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN",     "")  # Required — set via env var or HF Spaces Secret

# ─── Prompts ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are TrustOps-Agent, an expert content moderation AI.

Your task is to evaluate a piece of content and decide ONE of these actions:
- approve: Content is safe and should be published.
- remove: Content clearly violates policy (spam, direct abuse, hate speech).
- flag: Content is ambiguous, context-dependent, or requires human review.

Respond ONLY with a valid JSON object in this exact format:
{
  "action_type": "<approve|remove|flag>",
  "reasoning_chain": "<your step-by-step reasoning>",
  "confidence_score": <float between 0.0 and 1.0>
}
"""

TASK_INSTRUCTIONS = {
    "EASY": """Task 1 - Simple Toxicity Detection:
Analyze the text for clear-cut spam or direct abusive content.
Look for: ALL CAPS urgency, excessive punctuation, suspicious links, direct personal attacks.""",

    "MEDIUM": """Task 2 - Contextual Sentiment Analysis:
Distinguish between sarcastic frustration (allow) and targeted harassment (block).
Context matters: jokes, gaming references, and humor emojis suggest non-harmful intent.
Consider: Is this contextually sarcastic, or is it directed harassment?""",

    "HARD": """Task 3 - Multi-Turn Moderation / Coded Language:
Analyze for subtle grooming, radicalization patterns, or coded language.
Look for: metaphors that could be veiled threats, leaked sensitive information,
dog-whistle terminology, or cumulative manipulation patterns.
When uncertain, flag for human review."""
}


def safe(x: float) -> float:
    """Global safety clamp."""
    try:
        val = float(x)
    except (TypeError, ValueError):
        val = 0.5
    return max(0.01, min(val, 0.99))


def build_user_prompt(content_text: str, difficulty: str) -> str:
    instruction = TASK_INSTRUCTIONS.get(difficulty, TASK_INSTRUCTIONS["EASY"])
    return f"{instruction}\n\nContent to moderate:\n\"{content_text}\""


def parse_agent_response(response_text: str) -> dict:
    """Parse JSON from the model response, with fallback."""
    try:
        if not response_text or not response_text.strip():
            raise ValueError("Empty response")
        if "```" in response_text:
            start = response_text.find("{")
            end   = response_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON block found in markdown")
            response_text = response_text[start:end]
        parsed = json.loads(response_text)
        # Validate it's a dict with at least action_type
        if not isinstance(parsed, dict):
            raise ValueError(f"Parsed result is {type(parsed).__name__}, not dict")
        return parsed
    except (json.JSONDecodeError, ValueError, TypeError):
        return {
            "action_type": "flag",
            "reasoning_chain": f"Failed to parse model response: {str(response_text)[:200]}",
            "confidence_score": 0.1
        }


def run_single_task(task_name: str, client: OpenAI) -> dict:
    """
    Run a single task: load dataset, process each item, call grader, return score.
    Emits [START], [STEP], [END] logs.
    """
    task_def = get_task(task_name)
    dataset = task_def["dataset_loader"]()
    grader_fn = task_def["grader"]
    difficulty = task_def["difficulty"]
    total_items = len(dataset)

    task_start = time.time()
    print(f"[START]")

    # Edge case: empty dataset — return safe default
    if total_items == 0:
        print(f"[END]")
        return {"steps": []}

    steps_data = []
    step_num = 0

    for content in dataset:
        content_text = content.text
        content_id = content.id
        difficulty_val = content.difficulty.value

        user_prompt = build_user_prompt(content_text, difficulty_val)

        # ── Call model ──
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            raw_text = response.choices[0].message.content.strip()
        except Exception as e:
            raw_text = json.dumps({
                "action_type": "flag",
                "reasoning_chain": f"API error: {str(e)}",
                "confidence_score": 0.1
            })

        parsed = parse_agent_response(raw_text)

        # Sanitize action_type
        try:
            action_type = ActionType(parsed.get("action_type", "flag"))
        except ValueError:
            action_type = ActionType.FLAG

        action_obj = Action(
            content_id       = content_id,
            action_type      = action_type,
            reasoning_chain  = parsed.get("reasoning_chain", ""),
            confidence_score = float(parsed.get("confidence_score", 0.5)),
        )

        # ── Grade with task-specific grader (returns float) ──
        reward_score = safe(grader_fn(
            content=content,
            agent_action=action_obj.action_type,
            agent_reasoning=action_obj.reasoning_chain,
            agent_confidence=action_obj.confidence_score
        ))
        reward_score = max(0.01, min(0.99, reward_score))
        steps_data.append({"step": step_num, "reward": round(reward_score, 2)})

        print(f"[STEP] step={step_num} reward={reward_score:.2f}")

    print(f"[END]")
    
    if not steps_data:
        task_score = 0.5
    else:
        task_score = sum(s["reward"] for s in steps_data) / len(steps_data)
        
    task_score = max(0.01, min(0.99, task_score))

    return {
        "score": task_score,
        "steps": steps_data
    }


def run_inference():
    """Main inference loop: runs ALL 3 registered tasks sequentially."""
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN,
    )

    all_tasks = list_tasks()
    total_start = time.time()

    print(f"[START]")

    # Edge case: no tasks registered
    if not all_tasks:
        print(f"[END]")
        return {"tasks": {}}

    results = {}
    for task_name in all_tasks:
        result = run_single_task(task_name, client)
        results[task_name] = result

    print(f"[END]")
    
    if not results:
        overall_score = 0.5
    else:
        overall_score = sum(r["score"] for r in results.values()) / len(results)
        
    overall_score = max(0.01, min(0.99, overall_score))

    return {
        "score": overall_score,
        "tasks": results
    }


if __name__ == "__main__":
    results = run_inference()
