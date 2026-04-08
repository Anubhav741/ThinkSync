"""
TrustOps-Env: Observability Dashboard (Stabilized Production Version)
======================================================================
Expert Backend/Frontend Integration for OpenEnv.
Features: 
- Streaming async generators ([START] -> [STEP] -> [END])
- Direct MyEnv (engine.py) binding
- Zero-hardcoding (all via config.py or env)
- Error-resilient workflow
"""

import gradio as gr
import asyncio
import json
import os
from datetime import datetime
from typing import AsyncGenerator, Tuple

from models import (
    Content, Observation, Action, RewardRecord, EscalationTicket,
    ActionType, Difficulty, ContentLabel, CONTENT_BANK
)
from engine import MyEnv, classify_content, grade_action, create_escalation
from config import CONFIG

# ─── Global Environment Instance ───────────────────────────────────────────
# Ensuring singleton pattern for environment persistence
_env_instance = MyEnv()
_env_instance.reset()

# Reactive trackers for UI components (Synced with _env_instance)
escalation_history: list[EscalationTicket] = []
local_reward_history: list[RewardRecord] = []

# ─── Aesthetic Tokens ───────────────────────────────────────────────────────
CUSTOM_CSS = """
:root {
    --bg-primary: #0f172a;
    --accent-blue: #3b82f6;
    --accent-emerald: #10b981;
    --text-primary: #f1f5f9;
}
.gradio-container {
    background: linear-gradient(135deg, #0f172a 0%, #1a1a2e 100%) !important;
    font-family: 'Inter', sans-serif !important;
}
#log-stream textarea {
    background: #0c1222 !important;
    color: #4ade80 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
}
.stat-card {
    background: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid rgba(148, 163, 184, 0.1) !important;
    border-radius: 12px !important;
    padding: 15px !important;
}
"""

# ─── Log Stream Generator ──────────────────────────────────────────────────

async def stream_moderation_step(content: Content) -> AsyncGenerator[Tuple, None]:
    """
    Implements a robust streaming generator that follows the OpenEnv lifecycle.
    Ensures zero blocking of the event loop.
    """
    log = ""
    start_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # [START]
    log += f"{'═'*60}\n"
    log += f"[START] {start_ts} | ID: {content.id} | Level: {content.difficulty.value}\n"
    log += f"Processing: \"{content.text}\"\n"
    log += f"{'─'*60}\n"
    yield log, _build_stats(), _build_queue(), _build_rewards(), _build_escalations()
    await asyncio.sleep(0.4)

    try:
        # [STEP] — Logic Execution
        log += f"[STEP] Running classification engine...\n"
        yield log, _build_stats(), _build_queue(), _build_rewards(), _build_escalations()
        
        # Real logic call
        label, recommended_action, reasoning, confidence, _ = classify_content(content)
        
        # [STEP] — Result Propagation
        log += f"  ├─ 🏷️  Label: {label.value}\n"
        log += f"  ├─ 🎯 Confidence: {confidence:.0%}\n"
        log += f"  └─ ✅ Action: {recommended_action.value.upper()}\n"
        yield log, _build_stats(), _build_queue(), _build_rewards(), _build_escalations()
        await asyncio.sleep(0.4)

        # [STEP] — Environment Interaction
        log += f"[STEP] Advancing environment state...\n"
        action_obj = Action(
            content_id=content.id,
            action_type=recommended_action,
            reasoning_chain=reasoning,
            confidence_score=confidence
        )
        
        # Atomically advance the actual MyEnv
        new_obs, reward_val, is_done, _ = _env_instance.step(action_obj)
        
        # Sync reactive trackers
        reward_record = grade_action(content, recommended_action, reasoning, confidence)
        local_reward_history.append(reward_record)
        
        if recommended_action == ActionType.FLAG:
            esc = create_escalation(content, reasoning)
            escalation_history.append(esc)
            log += f"  🏳️ Escalation created: {esc.escalation_id}\n"

        # [END]
        end_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log += f"{'─'*60}\n"
        log += f"[END] {end_ts} | Reward: {reward_val:+.3f} | Cumulative: {new_obs.cumulative_reward:+.3f}\n"
        log += f"{'═'*60}\n"
        
        yield log, _build_stats(), _build_queue(), _build_rewards(), _build_escalations()
        
    except Exception as e:
        log += f"\n❌ CRITICAL FAULT: {str(e)}\n"
        yield log, _build_stats(), _build_queue(), _build_rewards(), _build_escalations()

# ─── UI Data Builders (Directly from _env_instance) ─────────────────────────

def _build_stats() -> str:
    state = _env_instance.state()
    avg = state.cumulative_reward / max(state.step_count, 1)
    return f"""
<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px;">
    <div class="stat-card"><b>Processed:</b> {state.step_count}</div>
    <div class="stat-card"><b>Reward:</b> {state.cumulative_reward:+.3f}</div>
    <div class="stat-card"><b>Avg:</b> {avg:+.3f}</div>
</div>
"""

def _build_queue() -> str:
    state = _env_instance.state()
    if not state.content_queue: return "📭 Empty"
    items = []
    for c in state.content_queue[:5]:
        items.append(f"- `[{c.id}]` {c.text[:40]}...")
    return "\n".join(items)

def _build_rewards() -> str:
    if not local_reward_history: return "No data."
    rows = []
    for r in reversed(local_reward_history[-10:]):
        rows.append(f"| {r.task_id} | {r.total_score:+.2f} | {r.penalty_type} |")
    return "| ID | Score | Penalty |\n|---|---|---|\n" + "\n".join(rows)

def _build_escalations() -> str:
    if not escalation_history: return "No escalations."
    return "\n".join([f"- **{e.escalation_id}**: {e.reason}" for e in reversed(escalation_history[-5:])])

# ─── Button Handlers ────────────────────────────────────────────────────────

async def handle_next_step():
    state = _env_instance.state()
    if not state.content_queue:
        yield "🏁 Episode complete.", _build_stats(), _build_queue(), _build_rewards(), _build_escalations()
        return
    
    content = state.content_queue[0]
    async for update in stream_moderation_step(content):
        yield update

async def handle_run_all():
    while _env_instance.state().content_queue:
        async for update in handle_next_step():
            yield update
        await asyncio.sleep(0.5)

def handle_reset():
    _env_instance.reset()
    global local_reward_history, escalation_history
    local_reward_history = []
    escalation_history = []
    return "🔄 Environment Reset.", _build_stats(), _build_queue(), _build_rewards(), _build_escalations()

# ─── Gradio App Definition ──────────────────────────────────────────────────

with gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Base()) as app:
    gr.Markdown("# 🛡️ TrustOps-Env Stability Controller")
    
    with gr.Row():
        metrics = gr.HTML(_build_stats())
        
    with gr.Row():
        with gr.Column(scale=3):
            logs = gr.Textbox(label="Live Observability Log", lines=25, interactive=False, elem_id="log-stream")
            with gr.Row():
                next_btn = gr.Button("▶️ Step")
                all_btn = gr.Button("⚡ Run All")
                reset_btn = gr.Button("Reset")
        
        with gr.Column(scale=2):
            with gr.Tab("📅 Queue"):
                queue = gr.Markdown(_build_queue())
            with gr.Tab("🏆 Rewards"):
                rewards = gr.Markdown(_build_rewards())
            with gr.Tab("🏳️ Escalations"):
                escalations = gr.Markdown(_build_escalations())

    outputs = [logs, metrics, queue, rewards, escalations]
    
    next_btn.click(handle_next_step, outputs=outputs)
    all_btn.click(handle_run_all, outputs=outputs)
    reset_btn.click(handle_reset, outputs=outputs)

if __name__ == "__main__":
    app.queue()
    app.launch(
        server_name=os.getenv("SERVER_HOST", "0.0.0.0"),
        server_port=int(os.getenv("PORT", "7860")),
        show_error=True
    )
