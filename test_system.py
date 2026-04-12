"""
TrustOps-Env: Comprehensive System Test Suite
=============================================
Tests connections, edge cases, state pipelines, and optimized data paths.
Updated for 3-task architecture with grader/tasks modules.
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
from tasks import list_tasks, get_task, TASK_REGISTRY
from grader import grade_easy_detection, grade_medium_classification, grade_hard_contextual, _clamp

class TestTrustOpsSystem(unittest.TestCase):

    # ─── 1. PIPELINE & STATE TESTS ──────────────────────────────────────────

    def test_pipeline_initialization(self):
        """Tests that the OpenEnv pipeline initializes correctly."""
        env = MyEnv()
        result = env.reset()
        obs = result["observation"]
        self.assertEqual(len(obs["content_queue"]), 12, "Should load 12 bank items.")
        self.assertEqual(obs["step_count"], 0)
        self.assertEqual(obs["cumulative_reward"], 0.0)
        self.assertTrue(obs["episode_active"])

    def test_pipeline_step_logic(self):
        """Tests the direct data path from interaction to environment state."""
        env = MyEnv()
        result = env.reset()
        obs = result["observation"]
        first_content = obs["content_queue"][0]
        first_content_id = first_content["id"] if isinstance(first_content, dict) else first_content.id
        expected_action = first_content["expected_action"] if isinstance(first_content, dict) else first_content.expected_action.value
        
        test_action = Action(
            content_id=first_content_id,
            action_type=ActionType(expected_action),
            reasoning_chain="Test logic execution matches ground truth",
            confidence_score=0.9
        )
        
        step_result = env.step(test_action)
        new_obs = step_result["observation"]
        reward = step_result["reward"]
        done = step_result["done"]
        
        self.assertEqual(new_obs["step_count"], 1)
        self.assertEqual(len(new_obs["content_queue"]), 11)
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
        env._state.content_queue = []  # Manually exhaust
        env._state.episode_active = False
        
        fake_action = Action(content_id="GHOST", action_type=ActionType.FLAG, reasoning_chain="", confidence_score=0.1)
        step_result = env.step(fake_action)
        
        self.assertEqual(step_result["reward"], 0.0)
        self.assertTrue(step_result["done"])

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

    # ─── 4. TASK REGISTRY TESTS ──────────────────────────────────────────────

    def test_task_registry_has_3_tasks(self):
        """Tests that exactly 3 tasks are registered."""
        tasks = list_tasks()
        self.assertEqual(len(tasks), 3, "Must have exactly 3 tasks.")
        self.assertIn("easy_detection", tasks)
        self.assertIn("medium_classification", tasks)
        self.assertIn("hard_contextual", tasks)

    def test_task_datasets_are_nonempty(self):
        """Ensures each task has at least one dataset item."""
        for task_name in list_tasks():
            task = get_task(task_name)
            dataset = task["dataset_loader"]()
            self.assertTrue(len(dataset) > 0, f"Task {task_name} has empty dataset.")

    def test_each_task_has_grader(self):
        """Ensures each task has a callable grader function."""
        for task_name in list_tasks():
            task = get_task(task_name)
            self.assertTrue(callable(task["grader"]), f"Task {task_name} missing grader.")

    # ─── 5. SCORE CLAMPING TESTS ─────────────────────────────────────────────

    def test_score_never_zero_or_one(self):
        """Ensures clamped scores are strictly in (0.01, 0.99)."""
        self.assertEqual(_clamp(0.0), 0.01)
        self.assertEqual(_clamp(1.0), 0.99)
        self.assertEqual(_clamp(-0.5), 0.01)
        self.assertEqual(_clamp(1.5), 0.99)
        self.assertEqual(_clamp(0.5), 0.5)

    def test_grader_scores_in_valid_range(self):
        """Run all graders and ensure scores are in (0.01, 0.99)."""
        from models import CONTENT_BANK
        for content in CONTENT_BANK:
            difficulty = content.difficulty.value
            task_map = {"EASY": "easy_detection", "MEDIUM": "medium_classification", "HARD": "hard_contextual"}
            task_name = task_map[difficulty]
            grader_fn = get_task(task_name)["grader"]
            
            # Test with correct action
            rec = grader_fn(content, content.expected_action, "This is test reasoning with toxic spam context coded leaked", 0.8)
            self.assertGreaterEqual(rec.total_score, 0.01, f"{content.id} score below 0.01")
            self.assertLessEqual(rec.total_score, 0.99, f"{content.id} score above 0.99")
            
            # Test with wrong action  
            wrong_action = ActionType.APPROVE if content.expected_action == ActionType.REMOVE else ActionType.REMOVE
            rec2 = grader_fn(content, wrong_action, "", 0.1)
            self.assertGreaterEqual(rec2.total_score, 0.01, f"{content.id} wrong-action score below 0.01")
            self.assertLessEqual(rec2.total_score, 0.99, f"{content.id} wrong-action score above 0.99")

    # ─── 6. MOCKED CONNECTION TESTING ───────────────────────────────────────

    @patch('inference.OpenAI')
    def test_connection_failure_simulation(self, mock_openai):
        """Tests that the exact inference loop survives an API connection drop."""
        mock_client = mock_openai.return_value
        mock_client.chat.completions.create.side_effect = Exception("Connection Timeout")
        
        from inference import run_inference
        results = run_inference()
        
        # Assert the simulation survived and completed all 3 tasks
        self.assertEqual(len(results["tasks"]), 3, "Should complete all 3 tasks.")
        for task_name, task_result in results["tasks"].items():
            self.assertGreaterEqual(task_result["score"], 0.01, f"{task_name} score too low")
            self.assertLessEqual(task_result["score"], 0.99, f"{task_name} score too high")
        self.assertGreaterEqual(results["overall_score"], 0.01)
        self.assertLessEqual(results["overall_score"], 0.99)

if __name__ == "__main__":
    unittest.main()
