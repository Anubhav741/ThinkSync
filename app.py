"""
🛡️ TrustOps-Env: The Original Premium Dashboard
==============================================
Restoring the 'First-Version' aesthetic with advanced glassmorphism,
neon accents, and high-density moderation metrics.
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="gradio")
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except ImportError:
    pass

import gradio as gr
import asyncio
import os
import random
from datetime import datetime
from typing import AsyncGenerator, Tuple

try:
    from models import (
        Content, Action, RewardRecord, EscalationTicket,
        ActionType
    )
    from engine import MyEnv, classify_content, grade_action, create_escalation

    # ─── Global State ──────────────────────────────────────────────────────────
    _env_instance = MyEnv()
    _env_instance.reset()

    reward_history: list[RewardRecord] = []
    escalation_history: list[EscalationTicket] = []

    # ─── Humanized Amber Hearth Design ─────────────────────────────────────────
    CUSTOM_CSS = """
    :root {
        --bg-cream: #fbf9f5;
        --card-bg: #ffffff;
        --txt-dark: #31332f;
        --txt-muted: #5e605b;
        --acc-orange: #e67e22;
        --acc-soft-orange: #f68a2f;
        --acc-green: #10b981;
        --acc-red: #f43f5e;
        --border-light: #efeee9;
    }
    .gradio-container {
        background-color: var(--bg-cream) !important;
        background-image: radial-gradient(at 100% 0%, rgba(246, 138, 47, 0.08) 0, transparent 40%),
                          radial-gradient(at 0% 100%, rgba(230, 126, 34, 0.05) 0, transparent 40%) !important;
        color: var(--txt-dark) !important;
        font-family: 'Inter', system-ui, sans-serif !important;
    }
    .glass-panel {
        background: var(--card-bg) !important;
        border: 1px solid var(--border-light) !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03) !important;
    }
    .stat-card {
        background: #ffffff;
        border: 1px solid var(--border-light);
        border-radius: 16px;
        padding: 24px;
        text-align: left;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
    }
    #log-output textarea {
        background: #efeee9 !important;
        color: var(--txt-dark) !important;
        font-family: 'Inter', monospace !important;
        border: none !important;
        border-radius: 12px !important;
    }
    """

    # ─── HTML Component Builders ────────────────────────────────────────────────

    def _get_stats_html():
        try:
            s = _env_instance.state()
            avg = s.cumulative_reward / max(s.step_count, 1)
            
            return f"""
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 24px;">
                <div class="stat-card">
                    <div style="color: var(--txt-muted); font-size: 0.8rem; font-weight: 500;">Tasks Processed Today</div>
                    <div style="color: var(--txt-dark); font-size: 2rem; font-weight: 800;">{s.step_count}</div>
                </div>
                <div class="stat-card">
                    <div style="color: var(--txt-muted); font-size: 0.8rem; font-weight: 500;">Success Rate</div>
                    <div style="color: var(--acc-green); font-size: 2rem; font-weight: 800;">{avg:+.3f}</div>
                </div>
                <div class="stat-card">
                    <div style="color: var(--txt-muted); font-size: 0.8rem; font-weight: 500;">Total Reward</div>
                    <div style="color: var(--acc-orange); font-size: 2rem; font-weight: 800;">{s.cumulative_reward:+.3f}</div>
                </div>
                <div class="stat-card">
                    <div style="color: var(--txt-muted); font-size: 0.8rem; font-weight: 500;">Pending Review</div>
                    <div style="color: var(--acc-red); font-size: 2rem; font-weight: 800;">{len(escalation_history)}</div>
                </div>
            </div>
            """
        except Exception as e:
            return f"<div>Error stats html: {str(e)}</div>"

    def _get_queue_html():
        try:
            s = _env_instance.state()
            if not s.content_queue: return "<div style='color:var(--txt-muted); padding:20px;'>Hooray! The queue is empty.</div>"
            
            html = "<div style='display: flex; flex-direction: column; gap: 12px;'>"
            for c in s.content_queue[:5]:
                color = "var(--acc-green)" if "EASY" in c.difficulty.value else "var(--acc-orange)" if "MEDIUM" in c.difficulty.value else "var(--acc-red)"
                html += f"""
                <div style="background: var(--card-bg); border: 1px solid var(--border-light); padding: 16px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px; align-items:center;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div style="width:32px; height:32px; border-radius:50%; background:var(--border-light); display:flex; align-items:center; justify-content:center; font-size:14px;">👤</div>
                            <span style="font-weight:600; color:var(--txt-dark); font-size:0.9rem;">User • {c.id}</span>
                        </div>
                        <span style="color:{color}; font-size:0.75rem; font-weight:700; background:rgba(0,0,0,0.04); padding:4px 8px; border-radius:8px;">{c.difficulty.value}</span>
                    </div>
                    <div style="font-size:0.9rem; color:var(--txt-muted); line-height:1.5;">"{c.text[:120]}..."</div>
                </div>
                """
            return html + "</div>"
        except Exception as e:
            return f"<div>Error queue html: {str(e)}</div>"

    def _get_reward_history_html():
        try:
            if not reward_history: return "<div style='color:var(--txt-muted); padding:20px;'>No history.</div>"
            rows = []
            for r in reversed(reward_history[-10:]):
                score_color = "var(--acc-green)" if r.total_score > 0.5 else "var(--acc-red)" if r.total_score < 0 else "var(--txt-dark)"
                rows.append(f"""
                <tr style="border-bottom: 1px solid var(--border-light);">
                    <td style="padding:12px; color:var(--txt-muted); font-size:0.85rem;">{r.task_id}</td>
                    <td style="padding:12px; font-weight:700; color:{score_color};">{r.total_score:+.2f}</td>
                    <td style="padding:12px; color:var(--txt-muted); font-size:0.75rem;">{r.penalty_type if r.penalty_applied else 'Okay'}</td>
                </tr>
                """)
            return f"""
            <table style="width:100%; text-align:left; border-collapse:collapse;">
                <thead style="color:var(--txt-muted); font-size:0.75rem;"><tr><th>Item</th><th>Score</th><th>Status</th></tr></thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
            """
        except Exception as e:
            return f"<div>Error reward html: {str(e)}</div>"

    def _get_escalation_html():
        try:
            if not escalation_history: return "<div style='color:var(--txt-muted); padding:20px;'>Inbox zero for threats.</div>"
            html = ""
            for e in reversed(escalation_history[-4:]):
                html += f"""
                <div style="background: rgba(244,63,94,0.04); border-left: 4px solid var(--acc-red); padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="color:var(--acc-red); font-weight:700; font-size:0.85rem; margin-bottom:4px;">Action Required: {e.escalation_id}</div>
                    <div style="color:var(--txt-muted); font-size:0.8rem;">{e.reason}</div>
                </div>
                """
            return html
        except Exception as e:
            return f"<div>Error escalation html: {str(e)}</div>"

    # ─── Async Logic ────────────────────────────────────────────────────────────

    async def run_step(content: Content) -> AsyncGenerator[Tuple, None]:
        log = ""
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            log += f"[{ts}] INITIALIZING MODERATION PIPELINE FOR {content.id}...\n"
            yield log, _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()
            await asyncio.sleep(0.4)

            label, action, reason, conf, _ = classify_content(content)
            log += f"[{ts}] AGENT OUTPUT: Action={action.value.upper()} | Conf={conf:.1%}\n"
            log += f"[{ts}] REASONING: {reason[:150]}...\n"
            yield log, _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()
            await asyncio.sleep(0.4)

            action_obj = Action(content_id=content.id, action_type=action, reasoning_chain=reason, confidence_score=conf)
            step_result = _env_instance.step(action_obj)
            reward_val = step_result["reward"]
            
            # Track local
            rec = grade_action(content, action, reason, conf)
            reward_history.append(rec)
            if action == ActionType.FLAG:
                escalation_history.append(create_escalation(content, reason))

            log += f"[{ts}] ENVIRONMENT SYNC: Reward awarded {reward_val:+.3f}. State advanced.\n"
            yield log, _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()
            
        except Exception as e:
            log += f"[ERROR in run_step] {str(e)}\n"
            yield log, _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()

    async def manual_step():
        try:
            s = _env_instance.state()
            if not s.content_queue:
                yield "STREAMS EXHAUSTED", _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()
                return
            async for update in run_step(s.content_queue[0]):
                yield update
        except Exception as e:
            yield f"[ERROR in manual_step] {str(e)}", _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()

    async def batch_all():
        try:
            while _env_instance.state().content_queue:
                async for update in manual_step(): 
                    yield update
                await asyncio.sleep(0.5)
        except Exception as e:
            yield f"[ERROR in batch_all] {str(e)}", _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()

    def reset_all():
        try:
            global reward_history, escalation_history
            _env_instance.reset()
            reward_history, escalation_history = [], []
            return "ENGINE RESET", _get_stats_html(), _get_queue_html(), _get_reward_history_html(), _get_escalation_html()
        except Exception as e:
            return f"[ERROR in reset_all] {str(e)}", "Error", "Error", "Error", "Error"

    # ─── UI Layout ─────────────────────────────────────────────────────────────

    demo = gr.Blocks(css=CUSTOM_CSS, theme=gr.themes.Default())
    with demo:
        gr.HTML(f'''
        <div style="text-align: left; padding: 40px 20px 20px 20px; max-width: 1200px; margin: 0 auto;">
            <h1 style="color: var(--txt-dark); font-weight: 800; letter-spacing: -1px; margin: 0; font-size: 2.5rem;">TrustOps <span style="color: var(--acc-orange);">Workspace</span></h1>
            <p style="color: var(--txt-muted); font-weight: 500; font-size: 1.1rem; margin-top: 8px;">An OpenEnv-based AI moderation evaluation system.</p>
        </div>
        ''')
        
        with gr.Row():
            stats_ui = gr.HTML(_get_stats_html())
        
        with gr.Row():
            with gr.Column(scale=3):
                with gr.Group(elem_classes="glass-panel"):
                    terminal = gr.Textbox(label="Agent Reasoning Stream", lines=20, interactive=False, elem_id="log-output")
                with gr.Row():
                    btn_s = gr.Button("Evaluate Next Item", variant="primary")
                    btn_b = gr.Button("Review Batch", variant="secondary")
                    btn_r = gr.Button("Reset Session")
            
            with gr.Column(scale=2):
                with gr.Group(elem_classes="glass-panel"):
                    with gr.Tab("Inbox Queue"):
                        queue_ui = gr.HTML(_get_queue_html())
                    with gr.Tab("Recent Activity"):
                        rewards_ui = gr.HTML(_get_reward_history_html())
                    with gr.Tab("Escalations"):
                        escalations_ui = gr.HTML(_get_escalation_html())

        outputs = [terminal, stats_ui, queue_ui, rewards_ui, escalations_ui]
        btn_s.click(manual_step, outputs=outputs)
        btn_b.click(batch_all, outputs=outputs)
        btn_r.click(reset_all, outputs=outputs)

except Exception as e:
    def health_check():
        return f"UI Loaded Successfully, but application failed to initialize.\\n[ERROR]: {str(e)}"
    
    demo = gr.Interface(fn=health_check, inputs=[], outputs="text")

try:
    import fastapi, uvicorn
    print("App started successfully")
    api = fastapi.FastAPI()

    @api.post("/reset")
    async def openenv_reset():
        return _env_instance.reset()

    @api.post("/step")
    async def openenv_step(req: fastapi.Request):
        data = await req.json()
        result = _env_instance.step(data)
        if isinstance(result, dict) and "reward" in result:
            result["reward"] = max(0.01, min(float(result["reward"]), 0.99))
        return result

    api = gr.mount_gradio_app(api, demo, path="/")
    uvicorn.run(api, host=os.getenv("SERVER_HOST", "0.0.0.0"), port=int(os.getenv("PORT", "7860")))
except Exception as e:
    print(f"API Init Error: {e}")
    demo.queue().launch(server_name=os.getenv("SERVER_HOST", "0.0.0.0"), server_port=int(os.getenv("PORT", "7860")))
