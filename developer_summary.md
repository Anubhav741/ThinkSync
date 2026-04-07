--------------
### Summary of What Was Covered vs What Was Added

| Area                                    | Previously Covered | Now Added/Enhanced |
| --------------------------------------- | :---: | :---: |
| Core Problem & Deployment Fix           | ✅ | — |
| Runtime Correction (Docker → Python)    | ✅ | — |
| UI Visibility (Gradio + Log Streaming)  | ✅ | — |
| Security (Env Variables)                | ✅ | — |
| Portability (Relative Paths)            | ✅ | — |
| System Workflow & Architecture Diagrams | ✅ | — |
| ER Diagram (Basic)                      | ✅ | Enhanced → Full System Model |
| **Reward System Mechanics (+0.5/+0.3/-0.2/-0.1)** | ❌ | ✅ Added |
| **Task Difficulty Matrix (EASY/MEDIUM/HARD details)** | ❌ | ✅ Added |
| **Grading Architecture (Embedding Similarity, Toxicity, Zero-Shot)** | ❌ | ✅ Added |
| **Agent Observation & State Tracking** | ❌ | ✅ Added |
| **Edge Case Escalation Pipeline** | ❌ | ✅ Added |
| **Legal & Bias Risk Management** | ❌ | ✅ Added |
| **Research Use Case Positioning** | ❌ | ✅ Added |
| **Simplified Policy Assumption** | ❌ | ✅ Added |
| **Complete Production Flow (5 Phases)** | ❌ | ✅ Added |
| **Risk Assessment Matrix (Quadrant Chart)** | ❌ | ✅ Added |
| **Value Distribution (Pie Chart)** | ❌ | ✅ Added |
| **OpenEnv Interface (step/reset/state)** | ❌ | ✅ Added |
| **openenv.yaml Configuration** | ❌ | ✅ Added |
| **inference.py Baseline Script** | ❌ | ✅ Added |
| **Normalized Scoring (0.0-1.0)** | ❌ | ✅ Added |
| **Hardware Constraints (2vCPU/8GB)** | ❌ | ✅ Added |

--------------
## 🧠 LLM Integration & Prompt Strategy

To successfully navigate the complex environments modeled in TrustOps-Env, the foundational AI agents must be equipped with specialized system prompts depending on the Difficulty Matrix assigned to the task.

### Zero-Shot System Prompt Injections

| Task Difficulty | Prompt Focus Areas | Target Capabilities |
| --- | --- | --- |
| **EASY** | Binary logic, speed, regex-like matching. | Focuses purely on parsing clear spam patterns or overt policy violations. Fast, deterministic output expected. |
| **MEDIUM** | Platform specific frameworks, conditional logic. | Agent must cross-reference text with simulated Terms of Service. Checks for gray-area violations like low-level toxicity. |
| **HARD** | Cultural reasoning, legal nuance, zero-shot inference. | Highly complex zero-shot analysis. The prompt instructs the agent to act as a *legal analyst*, prioritizing context and demanding an escalation flag if confidence dips below 50%. |

### Real-world Synchronization Mechanics

The bridge between the theoretical AI classification loop and the visual front-end relies entirely on the **Wrapper Synchronization Protocol**:
1. **The Event Emitter**: Normally, heavy LLM inference blocks a Python thread. TrustOps uses a native event emitter that listens to standard output.
2. **The Buffer**: Reasoning logic inside the agent module is captured safely in an asynchronous buffer.
3. **The Flush**: The Gradio generator function `yields` the captured buffer chunks, outputting the reasoning matrix (`[START] > [STEP] > [END]`) without freezing the interface. 

This strict separation ensures that even if HuggingFace Spaces recycles the deployment container, the moderation tasks remain persistent and the UI remains fully responsive.



-----------------
## Coverage Analysis — What Was Documented

> This table maps every topic discussed during project development to its documentation status in this Technical Architecture document.

| Topic                                                  | Covered In Sources | Documented Here | Mermaid Visual |
| ------------------------------------------------------ | :---: | :---: | :---: |
| **Data Models (Content, Observation, Action)**         | ✅ | ✅ | ✅ ER + Flowchart |
| **Content Object (id, text) — BaseModel**              | ✅ | ✅ | ✅ ER Diagram |
| **Observation Model (content_queue, moderation_log)**  | ✅ | ✅ | ✅ ER + Sequence |
| **Action Model (content_id, action_type)**             | ✅ | ✅ | ✅ Flowchart |
| **Data Model Interconnection**                         | ✅ | ✅ | ✅ Flow Diagram |
| **Data Models — Architectural Significance**           | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Content as Core Computational Loop**                 | ✅ | ✅ | ✅ Loop Diagram (NEW) |
| **Action Space — Approve**                             | ✅ | ✅ | ✅ Flowchart |
| **Action Space — Remove**                              | ✅ | ✅ | ✅ Flowchart |
| **Action Space — Flag (Escalation)**                   | ✅ | ✅ | ✅ Flowchart |
| **Action Space — Comparative Risk Profile**            | ✅ | ✅ | ✅ Bar Chart |
| **EASY Task: Spam Filtering**                          | ✅ | ✅ | ✅ Flowchart |
| **MEDIUM Task: Borderline Abuse**                      | ✅ | ✅ | ✅ Flowchart |
| **HARD Task: Contextual Nuance**                       | ✅ | ✅ | ✅ Flowchart |
| **Task Difficulty Progression**                        | ✅ | ✅ | ✅ XY Chart |
| **Grading Pipeline (Rule-based / Policy / Embedding)** | ✅ | ✅ | ✅ Flowchart |
| **Grading Tier Selection Logic**                       | ✅ | ✅ | ✅ Table |
| **Model Integration (Toxicity, Zero-Shot, Pretrained)**| ✅ | ✅ | ✅ Flowchart |
| **Embedding Similarity Grading**                       | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Reasoning Quality Evaluation (+0.2)**                | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Content Flow — End-to-End Pipeline**                 | ✅ | ✅ | ✅ Flowchart |
| **Observation Lifecycle — Sequence**                   | ✅ | ✅ | ✅ Sequence Diagram |
| **Infrastructure — Initial Failure**                   | ✅ | ✅ | ✅ Before/After (NEW) |
| **Python Runtime (sdk:python vs sdk:gradio)**          | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Gradio UI Framework (Wrapper Function)**             | ✅ | ✅ | ✅ Flowchart (NEW) |
| **HuggingFace Spaces Integration (Dual Role)**        | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Infrastructure Dependency Chain (5 Layers)**         | ✅ | ✅ | ✅ Bottom-up Flow (NEW) |
| **Security Incident (GitHub Secret Scanning)**         | ✅ | ✅ | — (in text) |
| **Secure API Access (os.getenv)**                      | ✅ | ✅ | ✅ (in HF Integration) |
| **Simplified Policy Assumption**                       | ✅ | ✅ | — (in text) |
| **Reward System — Full Deep-Dive**                     | ✅ | ✅ | ✅ Multiple (NEW) |
| **Classification Accuracy (+0.5)**                     | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Action Correctness (+0.3)**                          | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Reasoning Quality (+0.2) — Embedding Similarity**    | ✅ | ✅ | ✅ Flowchart (NEW) |
| **False Negative Penalty (-0.2) — Asymmetric Design**  | ✅ | ✅ | ✅ Flowchart (NEW) |
| **Reward Interaction Matrix (+1.0 max)**               | ✅ | ✅ | ✅ XY Chart (NEW) |
| **Full System ER Diagram**                             | ✅ | ✅ | ✅ ER Diagram |

---

## 🤖 Baseline Inference Specification (`inference.py`)

A mandatory component of the TrustOps-Env submission is the `inference.py` script. This script serves as the **reproducible baseline** for agent performance evaluation.

### OpenAI Client Integration
The script must utilize the native `OpenAI` client for all LLM interactions, pulling configuration from the standardized environment variables:
- `API_BASE_URL`: The endpoint host.
- `MODEL_NAME`: The specific model ID (e.g., Qwen2.5-72B).
- `HF_TOKEN`: The API key for authentication.

```python
from openai import OpenAI
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
```

### Strict STDOUT Logging Format
To pass automated scoring, the script must emit exactly three line types in this order:
1. **`[START]`**: Emitted once at episode beginning.
2. **`[STEP]`**: Emitted after every `env.step()`, tracking action, reward, and done status.
3. **`[END]`**: Emitted once after `env.close()`, providing final success status and normalized score.

---

## 🛠️ Setup & Validation Usage

Before final submission, developers must verify their environment and inference script using the following standardized tools.

### 1. Environment Validation
Run the core validator to ensure Pydantic model compliance and OpenEnv API adherence:
```bash
pip install openenv-core
openenv validate
```

### 2. Submission Pre-check
Execute the automated validation script to ping the HF Space and verify the Docker build:
```bash
./validate-submission.sh <HF_SPACE_URL>
```

### 3. Local Baseline Execution
Run the inference script locally to ensure scores are generated and logs follow the required format:
```bash
python inference.py
```

> **Validation Constraint:** The inference script must complete within **20 minutes** on a machine with **2 vCPUs** and **8 GB RAM** to be considered valid for the competition scoring pipeline.
