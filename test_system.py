"""
TrustOps-Env: Comprehensive System Test Suite
=============================================
Tests connections, edge cases, state pipelines, and optimized data paths.
"""

import unittest
from unittest.mock import patch
import json
import time

from engine import (
    MyEnv, classify_content, grade_action, 
    _compute_spam_score, _compute_toxicity_score, _compute_embedding_similarity
)
from models import Content, Difficulty, ContentLabel, ActionType, Action
from inference import parse_agent_response

class TestTrustOpsSystem(unittest.TestCase):

    # ─── 1. PIPELINE & STATE TESTS ──────────────────────────────────────────

    def test_pipeline_initialization(self):
        """Tests that the OpenEnv pipeline initializes correctly."""
        env = MyEnv()
        state = env.reset()
        self.assertEqual(len(state.content_queue), 12, "Should load 12 bank items.")
        self.assertEqual(state.step_count, 0)
        self.assertEqual(state.cumulative_reward, 0.0)
        self.assertTrue(state.episode_active)

    def test_pipeline_step_logic(self):
        """Tests the direct data path from interaction to environment state."""
        env = MyEnv()
        state = env.reset()
        first_content_id = state.content_queue[0].id
        
        test_action = Action(
            content_id=first_content_id,
            action_type=state.content_queue[0].expected_action,
            reasoning_chain="Test logic execution matches ground truth",
            confidence_score=1.0
        )
        
        new_state, reward, done, _ = env.step(test_action)
        
        self.assertEqual(new_state.step_count, 1)
        self.assertEqual(len(new_state.content_queue), 11)
        self.assertFalse(done)
        self.assertTrue(reward > 0.0, "Should generate a valid float reward.")

    # ─── 2. EDGE CASES & RESILIENCY ─────────────────────────────────────────

    def test_edge_case_invalid_json_fallback(self):
        """Tests inference robustness to corrupted LLM output."""
        bad_llm_output = "I think we should probably remove this but I'm not sure {"
        parsed = parse_agent_response(bad_llm_output)
        
        self.assertEqual(parsed["action_type"], "flag", "Should safely fallback to flag.")
        self.assertEqual(parsed["confidence_score"], 0.1, "Confidence should drop on failure.")
        self.assertIn("Failed to parse", parsed["reasoning_chain"])

    def test_edge_case_unexpected_action_type(self):
        """Tests how the engine handles hallucinated action enums."""
        fake_action = "shadowban"
        try:
            action_type = ActionType(fake_action)
        except ValueError:
            action_type = ActionType.FLAG
        self.assertEqual(action_type, ActionType.FLAG, "Should sanitize impossible actions.")

    def test_edge_case_empty_queue_step(self):
        """Tests stepping an exhausted environment."""
        env = MyEnv()
        env._state.content_queue = [] # Manually exhaust
        env._state.episode_active = False
        
        # Try to step
        fake_action = Action(content_id="GHOST", action_type=ActionType.FLAG, reasoning_chain="", confidence_score=0.1)
        obs, reward, done, _ = env.step(fake_action)
        
        self.assertEqual(reward, 0.0)
        self.assertTrue(done)

    # ─── 3. OPTIMIZED DATA PATH (HEURISTICS/GRADING) ────────────────────────

    def test_optimized_spam_calculation(self):
        """Tests the text pattern matching engine directly."""
        spam_text = "WIN FREE MONEY NOW!!! click this link http://scam.com !!"
        score = _compute_spam_score(spam_text)
        self.assertTrue(score > 0.5, f"Spam score {score} too low for clear spam.")

    def test_optimized_toxicity_softeners(self):
        """Tests edge cases where threats are softened by context."""
        hard_threat = "I will destroy you."
        soft_threat = "In the game, my character will destroy you lol."
        
        hard_score = _compute_toxicity_score(hard_threat)
        soft_score = _compute_toxicity_score(soft_threat)
        
        self.assertTrue(hard_score > soft_score, "Context softeners failed to discount toxicity.")

    def test_optimized_embedding_proxy(self):
        """Tests the simulated cosine similarity grading path."""
        expert_match = "Due to the violation of our policy regarding hateful terminology and veiled threats this requires escalation."
        poor_match = "It seems bad."
        
        best = _compute_embedding_similarity(expert_match, ContentLabel.ABUSIVE.value)
        worst = _compute_embedding_similarity(poor_match, ContentLabel.ABUSIVE.value)
        
        self.assertTrue(best > worst, "Similarity proxy failed to reward expert reasoning.")

    # ─── 4. MOCKED CONNECTION TESTING ───────────────────────────────────────

    @patch('inference.OpenAI')
    def test_connection_failure_simulation(self, mock_openai):
        """Tests that the exact inference loop survives an API connection drop."""
        # Setup mock to immediately throw connection error on chat creation
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("Connection Timeout")
        
        from inference import run_inference
        # Run inference (will use fallback logic)
        results = run_inference()
        
        # Assert the simulation survived and completed all tasks
        self.assertEqual(results["steps"], 12)
        self.assertTrue(results["total_reward"] > 0)
        self.assertTrue(results["avg_reward"] < 0.5, "Averaged reward should be low due to zero-confidence fallbacks.")

if __name__ == "__main__":
    unittest.main()
