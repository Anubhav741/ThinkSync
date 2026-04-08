"""
TrustOps-Env: Observability Dashboard
======================================
Production-grade Gradio UI implementing the full observability layer
from the Technical Architecture:
  - Real-time [START] → [STEP] → [END] log streaming via async generators
  - Content Queue visualization
  - Live reward/penalty metrics
  - Action Space decision badges
  - Escalation Queue tracker
  - Cumulative performance analytics

Architecture: Backend → Log Wrapper → Gradio Dashboard
"""

import gradio as gr
import asyncio
import json
import os
from datetime import datetime
from models import (
    Content, Observation, Action, RewardRecord, EscalationTicket,
    ActionType, Difficulty, ContentLabel, CONTENT_BANK
)
from engine import classify_content, grade_action, create_escalation


# ─── Global Environment State ───────────────────────────────────────────────

env_state = Observation(
    content_queue=list(CONTENT_BANK),
    moderation_log=[],
    step_count=0,
    cumulative_reward=0.0,
    episode_active=True
)

escalation_queue: list[EscalationTicket] = []
reward_history: list[RewardRecord] = []
processed_content_history: list[dict] = []


# ─── Custom Premium CSS ─────────────────────────────────────────────────────

CUSTOM_CSS = """
/* ── Root Variables ── */
:root {
    --bg-primary: #0f172a;
    --bg-card: #1e293b;
    --bg-card-alt: #1a2332;
    --accent-blue: #3b82f6;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-purple: #a78bfa;
    --accent-cyan: #22d3ee;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --border-subtle: #334155;
    --glass-bg: rgba(30, 41, 59, 0.85);
    --glass-border: rgba(148, 163, 184, 0.15);
}

/* ── Global Overrides ── */
.gradio-container {
    background: linear-gradient(135deg, #0f172a 0%, #1a1a2e 50%, #16213e 100%) !important;
    max-width: 100% !important;
    font-family: 'Inter', 'SF Pro Display', -apple-system, sans-serif !important;
}
.dark {
    --background-fill-primary: var(--bg-primary) !important;
}

/* ── Header ── */
#header-block {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(16, 185, 129, 0.08)) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 16px !important;
    padding: 28px 32px !important;
    margin-bottom: 16px !important;
    backdrop-filter: blur(12px) !important;
}
#header-block h1 {
    background: linear-gradient(135deg, #60a5fa, #34d399, #a78bfa) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
}
#header-block p {
    color: var(--text-secondary) !important;
    font-size: 0.95rem !important;
    margin-top: 6px !important;
}

/* ── Stat Cards ── */
.stat-card {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 14px !important;
    padding: 20px !important;
    backdrop-filter: blur(10px) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stat-card:hover {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.15) !important;
    transform: translateY(-1px) !important;
}

/* ── Buttons ── */
#process-btn {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 14px 24px !important;
    letter-spacing: 0.02em !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35) !important;
}
#process-btn:hover {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5) !important;
    transform: translateY(-2px) !important;
}

#auto-btn {
    background: linear-gradient(135deg, #10b981, #059669) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 14px 24px !important;
    box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35) !important;
    transition: all 0.3s ease !important;
}
#auto-btn:hover {
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5) !important;
    transform: translateY(-2px) !important;
}

#reset-btn {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 14px 24px !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25) !important;
    transition: all 0.3s ease !important;
}
#reset-btn:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
    transform: translateY(-2px) !important;
}

/* ── Log Stream Panel ── */
#log-stream textarea {
    background: #0c1222 !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 12px !important;
    color: #4ade80 !important;
    font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace !important;
    font-size: 0.82rem !important;
    line-height: 1.7 !important;
    padding: 16px !important;
}

/* ── JSON Viewer ── */
.json-viewer {
    background: #0c1222 !important;
    border-radius: 12px !important;
}

/* ── Section Labels ── */
.section-label {
    color: var(--text-secondary) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    margin-bottom: 8px !important;
}

/* ── Panels ── */
.panel {
    background: var(--glass-bg) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: 14px !important;
    padding: 20px !important;
    backdrop-filter: blur(10px) !important;
}

/* ── Metric Number Styling ── */
#metrics-display textarea {
    background: transparent !important;
    border: none !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
}

/* ── Tabs ── */
.tab-nav button {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 600 !important;
    padding: 10px 16px !important;
    transition: all 0.2s ease !important;
}
.tab-nav button.selected {
    color: var(--accent-blue) !important;
    border-bottom-color: var(--accent-blue) !important;
}

/* ── General Improvements ── */
label {
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
}
.block {
    border-radius: 14px !important;
}
"""


# ─── Helper: Build Metrics Display ──────────────────────────────────────────

def _build_stats_markdown() -> str:
    total = len(CONTENT_BANK)
    processed = env_state.step_count
    remaining = len(env_state.content_queue)
    avg_reward = env_state.cumulative_reward / max(processed, 1)
    esc_count = len(escalation_queue)
    
    # Count action distribution
    approves = sum(1 for r in env_state.moderation_log if r.get("action") == "approve")
    removes = sum(1 for r in env_state.moderation_log if r.get("action") == "remove")
    flags = sum(1 for r in env_state.moderation_log if r.get("action") == "flag")
    
    # Count difficulty distribution of processed
    easy_done = sum(1 for r in env_state.moderation_log if r.get("difficulty") == "EASY")
    med_done = sum(1 for r in env_state.moderation_log if r.get("difficulty") == "MEDIUM")
    hard_done = sum(1 for r in env_state.moderation_log if r.get("difficulty") == "HARD")
    
    false_neg = sum(1 for r in reward_history if r.penalty_type == "false_negative")
    false_pos = sum(1 for r in reward_history if r.penalty_type == "false_positive")
    
    emoji_reward = "🟢" if avg_reward >= 0.6 else ("🟡" if avg_reward >= 0.3 else "🔴")
    
    md = f"""
<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:12px; margin-bottom:12px;">
<div style="background:linear-gradient(135deg, rgba(59,130,246,0.15), rgba(59,130,246,0.05)); border:1px solid rgba(59,130,246,0.25); border-radius:12px; padding:16px; text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-weight:600;">Processed</div>
<div style="font-size:1.8rem; font-weight:800; color:#60a5fa; margin:4px 0;">{processed}</div>
<div style="font-size:0.72rem; color:#64748b;">of {total} total</div>
</div>

<div style="background:linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.05)); border:1px solid rgba(16,185,129,0.25); border-radius:12px; padding:16px; text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-weight:600;">Cumulative</div>
<div style="font-size:1.8rem; font-weight:800; color:#34d399; margin:4px 0;">{env_state.cumulative_reward:+.2f}</div>
<div style="font-size:0.72rem; color:#64748b;">avg: {emoji_reward} {avg_reward:+.2f}</div>
</div>

<div style="background:linear-gradient(135deg, rgba(245,158,11,0.15), rgba(245,158,11,0.05)); border:1px solid rgba(245,158,11,0.25); border-radius:12px; padding:16px; text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-weight:600;">Queue</div>
<div style="font-size:1.8rem; font-weight:800; color:#fbbf24; margin:4px 0;">{remaining}</div>
<div style="font-size:0.72rem; color:#64748b;">remaining</div>
</div>

<div style="background:linear-gradient(135deg, rgba(167,139,250,0.15), rgba(167,139,250,0.05)); border:1px solid rgba(167,139,250,0.25); border-radius:12px; padding:16px; text-align:center;">
<div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em; font-weight:600;">Escalations</div>
<div style="font-size:1.8rem; font-weight:800; color:#a78bfa; margin:4px 0;">{esc_count}</div>
<div style="font-size:0.72rem; color:#64748b;">flagged</div>
</div>
</div>

<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px;">
<div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2); border-radius:10px; padding:10px; text-align:center;">
<span style="font-size:0.72rem; color:#94a3b8;">✅ Approve</span><br/>
<span style="font-size:1.2rem; font-weight:700; color:#34d399;">{approves}</span>
</div>
<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.2); border-radius:10px; padding:10px; text-align:center;">
<span style="font-size:0.72rem; color:#94a3b8;">🚫 Remove</span><br/>
<span style="font-size:1.2rem; font-weight:700; color:#f87171;">{removes}</span>
</div>
<div style="background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.2); border-radius:10px; padding:10px; text-align:center;">
<span style="font-size:0.72rem; color:#94a3b8;">🏳️ Flag</span><br/>
<span style="font-size:1.2rem; font-weight:700; color:#60a5fa;">{flags}</span>
</div>
</div>
"""
    return md


def _build_queue_preview() -> str:
    """Builds a visual preview of the upcoming content queue."""
    if not env_state.content_queue:
        return '<div style="text-align:center; padding:24px; color:#64748b;">📭 Queue empty — all content processed.</div>'
    
    items = []
    for i, c in enumerate(env_state.content_queue[:5]):
        diff_colors = {"EASY": "#10b981", "MEDIUM": "#f59e0b", "HARD": "#ef4444"}
        diff_emojis = {"EASY": "🟢", "MEDIUM": "🟡", "HARD": "🔴"}
        color = diff_colors.get(c.difficulty.value, "#94a3b8")
        emoji = diff_emojis.get(c.difficulty.value, "⚪")
        
        border_style = "border-left: 3px solid " + color
        bg = "rgba(30,41,59,0.6)" if i > 0 else "rgba(59,130,246,0.1)"
        
        text_preview = c.text[:65] + ("..." if len(c.text) > 65 else "")
        
        items.append(f"""
<div style="background:{bg}; {border_style}; border-radius:8px; padding:12px 14px; margin-bottom:6px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
<span style="font-size:0.75rem; font-weight:700; color:{color};">{emoji} {c.difficulty.value}</span>
<span style="font-size:0.68rem; color:#64748b; font-family:monospace;">ID: {c.id}</span>
</div>
<div style="font-size:0.82rem; color:#cbd5e1; line-height:1.4;">"{text_preview}"</div>
</div>""")
    
    remaining_extra = len(env_state.content_queue) - 5
    extra = ""
    if remaining_extra > 0:
        extra = f'<div style="text-align:center; font-size:0.72rem; color:#64748b; padding:6px;">+{remaining_extra} more in queue</div>'
    
    return "\n".join(items) + extra


def _build_reward_table() -> str:
    """Builds a formatted reward history table."""
    if not reward_history:
        return '<div style="text-align:center; padding:24px; color:#64748b;">No rewards computed yet.</div>'
    
    rows = ""
    for r in reversed(reward_history):
        total_color = "#34d399" if r.total_score > 0 else "#f87171"
        penalty_cell = f'<span style="color:#f87171;">{r.penalty_applied}</span>' if r.penalty_applied < 0 else f'<span style="color:#64748b;">0.0</span>'
        pen_badge = ""
        if r.penalty_type == "false_negative":
            pen_badge = ' <span style="background:rgba(239,68,68,0.15); color:#f87171; font-size:0.6rem; padding:2px 6px; border-radius:4px;">FN</span>'
        elif r.penalty_type == "false_positive":
            pen_badge = ' <span style="background:rgba(245,158,11,0.15); color:#fbbf24; font-size:0.6rem; padding:2px 6px; border-radius:4px;">FP</span>'
        
        rows += f"""<tr style="border-bottom:1px solid rgba(148,163,184,0.1);">
<td style="padding:8px; font-family:monospace; font-size:0.75rem; color:#94a3b8;">{r.task_id}</td>
<td style="padding:8px; color:#60a5fa; font-weight:600; font-size:0.8rem;">+{r.classification_score}</td>
<td style="padding:8px; color:#a78bfa; font-weight:600; font-size:0.8rem;">+{r.action_score}</td>
<td style="padding:8px; color:#22d3ee; font-weight:600; font-size:0.8rem;">+{r.reasoning_score}</td>
<td style="padding:8px; font-size:0.8rem;">{penalty_cell}{pen_badge}</td>
<td style="padding:8px; color:{total_color}; font-weight:800; font-size:0.85rem;">{r.total_score:+.3f}</td>
</tr>"""
    
    return f"""
<table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
<thead>
<tr style="border-bottom:2px solid rgba(148,163,184,0.2);">
<th style="padding:8px; text-align:left; color:#64748b; font-size:0.7rem; text-transform:uppercase; letter-spacing:0.05em;">Task</th>
<th style="padding:8px; text-align:left; color:#64748b; font-size:0.7rem; text-transform:uppercase;">Classify</th>
<th style="padding:8px; text-align:left; color:#64748b; font-size:0.7rem; text-transform:uppercase;">Action</th>
<th style="padding:8px; text-align:left; color:#64748b; font-size:0.7rem; text-transform:uppercase;">Reason</th>
<th style="padding:8px; text-align:left; color:#64748b; font-size:0.7rem; text-transform:uppercase;">Penalty</th>
<th style="padding:8px; text-align:left; color:#64748b; font-size:0.7rem; text-transform:uppercase;">Total</th>
</tr>
</thead>
<tbody>{rows}</tbody>
</table>"""


def _build_escalation_panel() -> str:
    """Builds escalation queue visualization."""
    if not escalation_queue:
        return '<div style="text-align:center; padding:24px; color:#64748b;">🛡️ No escalations triggered.</div>'
    
    items = []
    for esc in reversed(escalation_queue):
        status_colors = {"Pending": "#f59e0b", "Reviewed": "#3b82f6", "Resolved": "#10b981"}
        s_color = status_colors.get(esc.status.value, "#94a3b8")
        text_preview = esc.content_text[:55] + ("..." if len(esc.content_text) > 55 else "")
        
        items.append(f"""
<div style="background:rgba(167,139,250,0.06); border:1px solid rgba(167,139,250,0.15); border-radius:10px; padding:14px; margin-bottom:8px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<span style="font-size:0.72rem; font-weight:700; color:#a78bfa; font-family:monospace;">{esc.escalation_id}</span>
<span style="background:rgba(255,255,255,0.06); color:{s_color}; font-size:0.65rem; font-weight:600; padding:3px 8px; border-radius:6px; border:1px solid {s_color}33;">{esc.status.value}</span>
</div>
<div style="font-size:0.78rem; color:#cbd5e1; margin-bottom:6px;">"{text_preview}"</div>
<div style="font-size:0.7rem; color:#64748b;">📋 {esc.reason}</div>
<div style="font-size:0.65rem; color:#475569; margin-top:4px;">⏰ {esc.escalated_at}</div>
</div>""")
    
    return "\n".join(items)


# ─── Async Pipeline: Wrapper → Generator → Gradio Stream ────────────────────

async def observability_logger(content: Content):
    """
    Async generator implementing the Wrapper Synchronization Protocol:
    1. Event Emitter — captures backend processing
    2. Async Buffer — decouples from UI thread
    3. Generator Flush — yields [START] → [STEP] → [END] to Gradio
    """
    log = ""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    # ═══ [START] ═══
    diff_emojis = {"EASY": "🟢", "MEDIUM": "🟡", "HARD": "🔴"}
    d_emoji = diff_emojis.get(content.difficulty.value, "⚪")
    
    log += f"{'═'*60}\n"
    log += f"[START] {ts}  Task Initialized\n"
    log += f"{'─'*60}\n"
    log += f"  📌 Content ID   : {content.id}\n"
    log += f"  📊 Difficulty    : {d_emoji} {content.difficulty.value}\n"
    log += f"  📝 Content Text  : \"{content.text}\"\n"
    log += f"  🏷️ Nuance Flag   : {'Yes' if content.has_nuance else 'No'}\n"
    log += f"  💬 Language Type  : {content.language_type}\n"
    log += f"{'─'*60}\n\n"
    
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()
    await asyncio.sleep(0.7)
    
    # ═══ [STEP 1] — Classification Pipeline ═══
    log += f"[STEP 1] Running multi-layer classification pipeline...\n"
    log += f"  ├─ Layer 1: Spam pattern matching (regex heuristics)\n"
    log += f"  ├─ Layer 2: Toxicity baseline scoring (simulated HF model)\n"
    log += f"  ├─ Layer 3: Contextual softener analysis\n"
    log += f"  └─ Layer 4: Difficulty-aware decision routing\n\n"
    
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()
    await asyncio.sleep(0.9)
    
    # Run the actual classification
    label, recommended_action, reasoning, confidence, metrics = classify_content(content)
    
    # Simulate agent decision (in production: LLM agent decides here)
    agent_action = recommended_action
    agent_confidence = confidence
    
    # ═══ [STEP 2] — Classification Results ═══
    action_emojis = {"approve": "✅", "remove": "🚫", "flag": "🏳️"}
    a_emoji = action_emojis.get(agent_action.value, "❓")
    
    log += f"[STEP 2] Classification complete.\n"
    log += f"  ├─ 🏷️  Label           : {label.value}\n"
    log += f"  ├─ 📊 Spam Score       : {metrics['spam_probability']:.1%}\n"
    log += f"  ├─ ☠️  Toxicity Score   : {metrics['toxicity_baseline']:.1%}\n"
    log += f"  ├─ 🛡️ Softener Signals : {metrics['softener_signals']}\n"
    log += f"  ├─ 🎯 Agent Confidence : {agent_confidence:.0%}\n"
    log += f"  └─ {a_emoji} Action Selected  : {agent_action.value.upper()}\n\n"
    
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()
    await asyncio.sleep(1.0)
    
    # ═══ [STEP 3] — Reasoning Chain ═══
    log += f"[STEP 3] Agent Reasoning Chain:\n"
    log += f"  ╔{'═'*56}╗\n"
    # Word-wrap reasoning
    words = reasoning.split()
    line = "  ║ "
    for w in words:
        if len(line) + len(w) + 1 > 57:
            log += line.ljust(58) + "║\n"
            line = "  ║ " + w + " "
        else:
            line += w + " "
    if line.strip() != "║":
        log += line.ljust(58) + "║\n"
    log += f"  ╚{'═'*56}╝\n\n"
    
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()
    await asyncio.sleep(0.8)
    
    # ═══ [STEP 4] — Grading Pipeline ═══
    grading_method = {
        Difficulty.EASY: "Rule-Based Label Matching",
        Difficulty.MEDIUM: "Policy-Matching + Reasoning Assessment",
        Difficulty.HARD: "Embedding Similarity + Full Reasoning Evaluation"
    }
    
    log += f"[STEP 4] Grading Pipeline activated.\n"
    log += f"  ├─ Grading Method  : {grading_method.get(content.difficulty, 'Unknown')}\n"
    log += f"  ├─ Computing classification accuracy...\n"
    log += f"  ├─ Validating action against policy...\n"
    
    if content.difficulty in (Difficulty.MEDIUM, Difficulty.HARD):
        log += f"  ├─ Evaluating reasoning via embedding similarity...\n"
    
    log += f"  └─ Checking penalty conditions...\n\n"
    
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()
    await asyncio.sleep(0.8)
    
    # Compute grades
    reward = grade_action(content, agent_action, reasoning, agent_confidence)
    reward_history.append(reward)
    
    # ═══ [STEP 5] — Reward Matrix Output ═══
    log += f"[STEP 5] Reward Matrix computed.\n"
    log += f"  ┌────────────────────────────────────────────────┐\n"
    log += f"  │  Classification Accuracy  :  +{reward.classification_score:<18}│\n"
    log += f"  │  Action Correctness       :  +{reward.action_score:<18}│\n"
    log += f"  │  Reasoning Quality        :  +{reward.reasoning_score:<18}│\n"
    
    if reward.penalty_applied < 0:
        penalty_label = "FALSE NEGATIVE ⚠️" if reward.penalty_type == "false_negative" else "FALSE POSITIVE ⚠️"
        log += f"  │  ❌ PENALTY ({penalty_label}): {reward.penalty_applied:<8}│\n"
    else:
        log += f"  │  Penalties               :   {reward.penalty_applied:<18}│\n"
    
    log += f"  ├────────────────────────────────────────────────┤\n"
    sign = "+" if reward.total_score >= 0 else ""
    log += f"  │  ★ TOTAL SCORE            :  {sign}{reward.total_score:<18}│\n"
    log += f"  └────────────────────────────────────────────────┘\n\n"
    
    # Handle escalation if flagged
    if agent_action == ActionType.FLAG:
        esc = create_escalation(content, reasoning)
        escalation_queue.append(esc)
        log += f"  🏳️ ESCALATION TRIGGERED → Ticket: {esc.escalation_id}\n"
        log += f"     Reason: {esc.reason}\n\n"
    
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()
    await asyncio.sleep(0.6)
    
    # ═══ [END] ═══
    # Update global observation state
    env_state.moderation_log.append({
        "task_id": content.id,
        "action": agent_action.value,
        "label": label.value,
        "difficulty": content.difficulty.value,
        "confidence": agent_confidence,
        "reward": reward.total_score,
        "reasoning": reasoning[:100],
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    })
    env_state.step_count += 1
    env_state.cumulative_reward = round(env_state.cumulative_reward + reward.total_score, 3)
    
    processed_content_history.append({
        "id": content.id,
        "text": content.text[:50],
        "difficulty": content.difficulty.value,
        "label": label.value,
        "action": agent_action.value,
        "score": reward.total_score,
    })
    
    ts_end = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log += f"{'═'*60}\n"
    log += f"[END] {ts_end}  Step #{env_state.step_count} concluded.\n"
    log += f"  ├─ Action       : {a_emoji} {agent_action.value.upper()}\n"
    log += f"  ├─ Step Reward  : {sign}{reward.total_score}\n"
    log += f"  ├─ Cumulative   : {env_state.cumulative_reward:+.3f}\n"
    log += f"  └─ Queue Left   : {len(env_state.content_queue)}\n"
    log += f"{'═'*60}\n"
    
    if not env_state.content_queue:
        env_state.episode_active = False
        log += f"\n🏁 EPISODE COMPLETE — All {env_state.step_count} tasks processed.\n"
        avg = env_state.cumulative_reward / env_state.step_count
        log += f"   Final Score: {env_state.cumulative_reward:+.3f}  |  Average: {avg:+.3f}\n"
    
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()


async def run_single_step():
    """Wrapper: pops next content from queue and triggers the async generator."""
    if not env_state.content_queue:
        msg = "═══════════════════════════════════════════════════\n"
        msg += "📭 PIPELINE COMPLETE\n"
        msg += f"   All {env_state.step_count} tasks have been processed.\n"
        msg += f"   Cumulative Reward: {env_state.cumulative_reward:+.3f}\n"
        msg += "═══════════════════════════════════════════════════\n"
        yield msg, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()
        return
    
    content = env_state.content_queue.pop(0)
    async for result in observability_logger(content):
        yield result


async def run_all_steps():
    """Runs through ALL remaining content in the queue sequentially."""
    last_result = None
    while env_state.content_queue:
        content = env_state.content_queue.pop(0)
        async for result in observability_logger(content):
            last_result = result
            yield result
        await asyncio.sleep(0.4)
    
    # Final summary
    log = last_result[0] if last_result else ""
    log += "\n\n" + "🏆" * 20 + "\n"
    log += f"  FULL EPISODE COMPLETE — {env_state.step_count} tasks processed.\n"
    avg = env_state.cumulative_reward / max(env_state.step_count, 1)
    log += f"  Final Cumulative: {env_state.cumulative_reward:+.3f}  |  Average: {avg:+.3f}\n"
    log += "🏆" * 20 + "\n"
    yield log, _build_stats_markdown(), _build_queue_preview(), _build_reward_table(), _build_escalation_panel()


def reset_environment():
    """Resets the entire environment to initial state."""
    global escalation_queue, reward_history, processed_content_history
    env_state.content_queue = list(CONTENT_BANK)
    env_state.moderation_log = []
    env_state.step_count = 0
    env_state.cumulative_reward = 0.0
    env_state.episode_active = True
    escalation_queue = []
    reward_history = []
    processed_content_history = []
    
    return (
        "🔄 Environment reset. Ready for new episode.\n",
        _build_stats_markdown(),
        _build_queue_preview(),
        _build_reward_table(),
        _build_escalation_panel()
    )


# ─── Build the Gradio UI ────────────────────────────────────────────────────

with gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Base(), title="TrustOps-Env Dashboard") as demo:
    
    # ── Header ──
    gr.Markdown("""
# 🛡️ TrustOps-Env : Observability Dashboard

Real-time view of AI agent reinforcement learning moderation loops — tracking rewards, penalties, and escalation pipelines.                
    """, elem_id="header-block")
    
    # ── Metrics Row ──
    stats_display = gr.Markdown(value=_build_stats_markdown())
    
    # ── Controls ──
    with gr.Row():
        process_btn = gr.Button("▶️  Process Next", variant="primary", elem_id="process-btn", scale=2)
        auto_btn = gr.Button("⚡ Run All", variant="secondary", elem_id="auto-btn", scale=1)
        reset_btn = gr.Button("🔄 Reset", variant="secondary", elem_id="reset-btn", scale=1)
    
    # ── Main Content Area ──
    with gr.Row():
        # ── Left: Log Stream ──
        with gr.Column(scale=3):
            gr.Markdown('<div class="section-label">AGENT LOG WRAPPER — LIVE STREAM</div>')
            log_output = gr.Textbox(
                label="[START] → [STEP] → [END]",
                lines=28,
                max_lines=50,
                interactive=False,
                elem_id="log-stream"
            )
        
        # ── Right: Panels ──
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.Tab("📋 Queue"):
                    queue_display = gr.Markdown(value=_build_queue_preview())
                
                with gr.Tab("🏆 Rewards"):
                    reward_display = gr.Markdown(value=_build_reward_table())
                
                with gr.Tab("🏳️ Escalations"):
                    escalation_display = gr.Markdown(value=_build_escalation_panel())
    
    # ── Wire Events ──
    outputs = [log_output, stats_display, queue_display, reward_display, escalation_display]
    
    process_btn.click(fn=run_single_step, inputs=[], outputs=outputs)
    auto_btn.click(fn=run_all_steps, inputs=[], outputs=outputs)
    reset_btn.click(fn=reset_environment, inputs=[], outputs=outputs)


# ─── Launch ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo.queue()
    demo.launch(
        server_name=os.getenv("SERVER_HOST", "0.0.0.0"),
        server_port=int(os.getenv("PORT", "7860")),
        show_error=True,
        favicon_path=None
    )
