"""
TrustOps-Env: Baseline Inference
=================================
Uses the OpenAI-compatible client to call Qwen2.5-72B-Instruct via HuggingFace Router.
Emits [START], [STEP], and [END] logs for OpenEnv evaluation.
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

from engine import MyEnv
from models import Action, ActionType

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


def build_user_prompt(content_text: str, difficulty: str) -> str:
    instruction = TASK_INSTRUCTIONS.get(difficulty, TASK_INSTRUCTIONS["EASY"])
    return f"{instruction}\n\nContent to moderate:\n\"{content_text}\""


def parse_agent_response(response_text: str) -> dict:
    """Parse JSON from the model response, with fallback."""
    try:
        # Try to extract JSON block if wrapped in markdown
        if "```" in response_text:
            start = response_text.find("{")
            end   = response_text.rfind("}") + 1
            response_text = response_text[start:end]
        return json.loads(response_text)
    except (json.JSONDecodeError, ValueError):
        # Fallback: flag with low confidence
        return {
            "action_type": "flag",
            "reasoning_chain": f"Failed to parse model response: {response_text[:200]}",
            "confidence_score": 0.1
        }


def run_inference():
    """Main inference loop: reset env, run episode, log [START]/[STEP]/[END]."""
    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN,
    )

    env = MyEnv()
    obs = env.reset()

    total_tasks  = len(obs.content_queue)
    episode_start = time.time()

    print(f"[START] TrustOps-Env inference started. Tasks: {total_tasks}, Model: {MODEL_NAME}")

    step_num = 0
    while obs.episode_active and obs.content_queue:
        content = obs.content_queue[0]

        user_prompt = build_user_prompt(content.text, content.difficulty.value)

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

        action = Action(
            content_id       = content.id,
            action_type      = action_type,
            reasoning_chain  = parsed.get("reasoning_chain", ""),
            confidence_score = float(parsed.get("confidence_score", 0.5)),
        )

        obs, reward, done, _ = env.step(action)
        step_num += 1

        elapsed = round(time.time() - episode_start, 2)

        print(
            f"[STEP] step={step_num} | task_id={content.id} | difficulty={content.difficulty.value} "
            f"| action={action.action_type.value} | expected={content.expected_action.value} "
            f"| reward={reward:.3f} | cumulative={obs.cumulative_reward:.3f} | elapsed={elapsed}s"
        )

        # Safety valve: < 20 minutes runtime
        if elapsed > 1100:
            print(f"[STEP] TIMEOUT: elapsed {elapsed}s > 1100s limit. Stopping early.")
            break

    elapsed_total = round(time.time() - episode_start, 2)
    steps_done    = obs.step_count
    total_reward  = obs.cumulative_reward
    avg_reward    = round(total_reward / max(steps_done, 1), 4)

    print(
        f"[END] steps={steps_done} | total_reward={total_reward:.3f} "
        f"| avg_reward={avg_reward} | elapsed={elapsed_total}s"
    )

    return {
        "steps":        steps_done,
        "total_reward": total_reward,
        "avg_reward":   avg_reward,
        "elapsed_s":    elapsed_total,
    }


if __name__ == "__main__":
    results = run_inference()
