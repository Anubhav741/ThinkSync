---
title: ThinkSync
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
app_file: app.py
pinned: false
---
# TrustOps-Env 🛡️

A programmatic **content moderation reinforcement learning environment** built to the [OpenEnv](https://huggingface.co/openenv) specification. Agents are evaluated on three progressively complex moderation tasks.

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Set your HuggingFace token
export HF_TOKEN="hf_..."

# Run baseline inference (produces [START]/[STEP]/[END] logs)
python inference.py

# Or launch the Gradio observability dashboard
python app.py
```

---

## 🏗️ Architecture

```
Content Queue  →  Agent (LLM)  →  Grader  →  RewardRecord
     ↑                                              ↓
  CONTENT_BANK                              Moderation Log
```

**Core Modules:**

| File | Purpose |
|------|---------|
| `models.py` | Pydantic data models: `Content`, `Observation`, `Action`, `RewardRecord`, `EscalationTicket` |
| `engine.py` | Classification/grading pipeline + `MyEnv` (OpenEnv interface) |
| `inference.py` | Baseline agent using Qwen2.5-72B via HF Router |
| `app.py` | Gradio observability dashboard |
| `openenv.yaml` | OpenEnv spec file |
| `Dockerfile` | Container for HF Spaces (2 vCPUs, 8GB RAM) |

---

## 📐 Action Space

| Field | Type | Description |
|-------|------|-------------|
| `content_id` | `string` | References the `Content.id` being moderated |
| `action_type` | `enum` | One of: `approve`, `remove`, `flag` |
| `reasoning_chain` | `string` | Step-by-step chain-of-thought justification |
| `confidence_score` | `float [0.0–1.0]` | Agent self-reported confidence |

### Valid Actions
- **`approve`** — Content is safe; publish it.
- **`remove`** — Content violates policy; take it down.
- **`flag`** — Content is ambiguous or requires human review.

---

## 👁️ Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `content_queue` | `List[Content]` | Posts awaiting moderation |
| `moderation_log` | `List[dict]` | History of all decisions + reward breakdowns |
| `step_count` | `int` | Steps completed in current episode |
| `cumulative_reward` | `float` | Running reward total |
| `episode_active` | `bool` | Whether the episode is still running |

---

## 🏆 Reward Function

Reward for each step is decomposed into:

| Component | Score | Condition |
|-----------|-------|-----------|
| Classification Score | `+0.5` | Agent action matches expected action |
| Action Score | `+0.3` | Exact correct action taken |
| Reasoning Score | `+0.0 – +0.2` | Quality of chain-of-thought (partial credit) |
| False Negative Penalty | `–0.2` | Approved harmful content |
| False Positive Penalty | `–0.1` | Removed safe content |

**Range:** `[-0.2, 1.0]` per step

### Partial Progress Signals
- **Easy Task:** `+0.2` for identifying toxic keywords in reasoning
- **Medium Task:** `+0.1` for capturing sarcasm/context cues in reasoning
- **Hard Task:** `+0.1` for identifying coded language or radicalization patterns

---

## 📋 Tasks

### Task 1 — Simple Toxicity Detection (Easy)
Classify clear-cut spam and direct abusive content.

- `E001`: `"BUY CHEAP FOLLOWERS NOW!!! 💰💰💰"` → **remove** (SPAM)
- `E002`: `"Had a great lunch today..."` → **approve** (SAFE)

### Task 2 — Contextual Sentiment Analysis (Medium)
Distinguish sarcastic frustration (allow) from targeted harassment (remove).

- `M002`: `"I'm going to DESTROY you in chess tonight 😂"` → **approve** (CONTEXT-DEPENDENT)
- `M001`: `"You're a worthless excuse for a human being..."` → **remove** (ABUSIVE)

### Task 3 — Multi-Turn Moderation / Coded Language (Hard)
Detect subtle grooming, radicalization patterns, and coded language.

- `H002`: `"Those people have been poisoning the well..."` → **flag** (CODED-LANGUAGE)
- `H003`: `"LEAKED: Internal documents show executives covered up..."` → **flag** (WHISTLEBLOWER)

---

## 📊 Baseline Scores

| Task | Difficulty | Baseline Agent | Avg Reward/Step |
|------|-----------|----------------|----------------|
| Toxicity Detection | Easy | Qwen2.5-72B | ~0.80 |
| Contextual Sentiment | Medium | Qwen2.5-72B | ~0.65 |
| Multi-Turn / Coded | Hard | Qwen2.5-72B | ~0.45 |
| **Overall** | **All 12 tasks** | **Qwen2.5-72B** | **~0.62** |

---

## 🖥️ OpenEnv Interface (`MyEnv`)

```python
from engine import MyEnv
from models import Action, ActionType

env = MyEnv()
obs = env.reset()

action = Action(
    content_id="E001",
    action_type=ActionType.REMOVE,
    reasoning_chain="Clear spam: ALL-CAPS, excessive emojis, suspicious link.",
    confidence_score=0.95
)

obs, reward, done, info = env.step(action)
print(reward)  # e.g., 0.8
```

---

## 🐳 Docker

```bash
docker build -t trustops-env .
docker run -e HF_TOKEN=$HF_TOKEN --cpus 2 --memory 8g trustops-env
```

---

## 🔐 Security

- HF token read via `os.getenv("HF_TOKEN")` — never hard-coded in production.
- **Fixed**: Removed the `flag-everything` hack in `engine.py:264` that allowed agents to cheat by flagging all tasks for unearned `+0.5` classification scores.

---

## 📄 License

MIT © [Anubhav741](https://github.com/Anubhav741)
