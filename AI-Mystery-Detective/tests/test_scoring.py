"""
Unit and integration tests for ScoreManager and ScoringConfig.

Tests cover:
- add_points() & deduct_points()
- calculate_score() & component breakdown
- calculate_accuracy() bounding [0, 100]
- get_rank() threshold progression
- get_score_summary() & reset_score()
- correct / incorrect suspect handling
- evidence & clue importance scoring
- unnecessary actions & hint penalties
- time bonus decay
- difficulty multipliers
- invalid & negative value validation
- end-to-end GameController integration flow
"""

import unittest
from game.scoring import ScoreManager, ScoringConfig
from game.game_controller import GameController


class TestScoreManagerBasicOps(unittest.TestCase):
    def setUp(self):
        self.manager = ScoreManager()

    def test_initial_state(self):
        self.assertEqual(self.manager.current_score, 0)
        self.assertEqual(self.manager.current_accuracy, 0.0)
        self.assertEqual(self.manager.get_rank(), "Detective Rookie")

    def test_add_points_valid(self):
        new_score = self.manager.add_points(150)
        self.assertEqual(new_score, 150)
        self.assertEqual(self.manager.current_score, 150)

    def test_add_points_zero(self):
        new_score = self.manager.add_points(0)
        self.assertEqual(new_score, 0)

    def test_add_points_invalid_types(self):
        with self.assertRaises(ValueError):
            self.manager.add_points("100")
        with self.assertRaises(ValueError):
            self.manager.add_points(15.5)
        with self.assertRaises(ValueError):
            self.manager.add_points(True)

    def test_add_points_negative(self):
        with self.assertRaises(ValueError):
            self.manager.add_points(-50)

    def test_deduct_points_valid(self):
        self.manager.add_points(200)
        score = self.manager.deduct_points(50)
        self.assertEqual(score, 150)

    def test_deduct_points_floored_at_zero(self):
        self.manager.add_points(50)
        score = self.manager.deduct_points(100)
        self.assertEqual(score, 0)
        self.assertEqual(self.manager.current_score, 0)

    def test_deduct_points_invalid_types(self):
        with self.assertRaises(ValueError):
            self.manager.deduct_points("20")
        with self.assertRaises(ValueError):
            self.manager.deduct_points(False)

    def test_deduct_points_negative(self):
        with self.assertRaises(ValueError):
            self.manager.deduct_points(-10)

    def test_reset_score(self):
        self.manager.add_points(300)
        self.manager.reset_score()
        self.assertEqual(self.manager.current_score, 0)
        self.assertEqual(self.manager.current_accuracy, 0.0)
        summary = self.manager.get_score_summary()
        self.assertEqual(summary["score"], 0)
        self.assertEqual(summary["breakdown"], {})


class TestScoreCalculation(unittest.TestCase):
    def setUp(self):
        self.manager = ScoreManager()

    def test_calculate_score_correct_suspect(self):
        score = self.manager.calculate_score(solved=True, difficulty="easy")
        # 500 suspect + 100 time bonus = 600
        self.assertEqual(score, 600)
        self.assertEqual(self.manager.current_score, 600)

    def test_calculate_score_wrong_suspect(self):
        score = self.manager.calculate_score(solved=False, difficulty="easy")
        # -200 suspect + 100 time bonus = -100, floored at 0
        self.assertEqual(score, 0)

    def test_evidence_scoring_with_importance(self):
        evidence = [
            {"evidence_id": "e1", "importance": "low"},      # 50 * 1 = 50
            {"evidence_id": "e2", "importance": "medium"},   # 50 * 2 = 100
            {"evidence_id": "e3", "importance": "high"},     # 50 * 3 = 150
            {"evidence_id": "e4", "importance": "critical"}, # 50 * 5 = 250
        ]
        score = self.manager.calculate_score(
            solved=True,
            evidence_list=evidence,
            difficulty="easy",
            action_count=20  # full time bonus 100
        )
        # 500 + 550 (evidence) + 100 = 1150
        self.assertEqual(score, 1150)

    def test_clue_scoring_with_importance(self):
        clues = [
            {"clue_id": "c1", "importance": "low"},      # 30 * 1 = 30
            {"clue_id": "c2", "importance": "critical"}, # 30 * 5 = 150
        ]
        score = self.manager.calculate_score(
            solved=True,
            clues_list=clues,
            difficulty="easy",
            action_count=20
        )
        # 500 + 180 + 100 = 780
        self.assertEqual(score, 780)

    def test_contradiction_scoring(self):
        score = self.manager.calculate_score(
            solved=True,
            contradictions_found=2,
            difficulty="easy",
            action_count=20
        )
        # 500 + (2 * 75) + 100 = 750
        self.assertEqual(score, 750)

    def test_unnecessary_actions_penalty(self):
        score = self.manager.calculate_score(
            solved=True,
            unnecessary_actions=3,
            difficulty="easy",
            action_count=20
        )
        # 500 + 100 - (3 * 10) = 570
        self.assertEqual(score, 570)

    def test_hints_used_penalty(self):
        score = self.manager.calculate_score(
            solved=True,
            hints_used=2,
            difficulty="easy",
            action_count=20
        )
        # 500 + 100 - (2 * 25) = 550
        self.assertEqual(score, 550)

    def test_time_bonus_decay(self):
        score_fast = self.manager.calculate_score(solved=True, action_count=10)
        score_mid = self.manager.calculate_score(solved=True, action_count=40)
        score_slow = self.manager.calculate_score(solved=True, action_count=70)

        self.assertEqual(score_fast, 600)  # max bonus 100
        self.assertGreater(score_fast, score_mid)
        self.assertEqual(score_slow, 500)  # 0 time bonus

    def test_case_difficulty_multipliers(self):
        easy_score = self.manager.calculate_score(solved=True, difficulty="easy", action_count=20)
        med_score = self.manager.calculate_score(solved=True, difficulty="medium", action_count=20)
        hard_score = self.manager.calculate_score(solved=True, difficulty="hard", action_count=20)

        self.assertEqual(easy_score, 600)          # 600 * 1.0 = 600
        self.assertEqual(med_score, 750)           # 600 * 1.25 = 750
        self.assertEqual(hard_score, 900)          # 600 * 1.5 = 900


class TestAccuracyCalculation(unittest.TestCase):
    def setUp(self):
        self.manager = ScoreManager()

    def test_perfect_accuracy(self):
        acc = self.manager.calculate_accuracy(
            solved=True,
            discovered_evidence_count=5,
            total_evidence_count=5,
            discovered_clues_count=3,
            total_clues_count=3,
            unnecessary_actions=0,
            hints_used=0
        )
        self.assertEqual(acc, 100.0)

    def test_failed_accusation_accuracy(self):
        acc = self.manager.calculate_accuracy(
            solved=False,
            discovered_evidence_count=5,
            total_evidence_count=5,
            discovered_clues_count=3,
            total_clues_count=3,
            unnecessary_actions=0,
            hints_used=0
        )
        self.assertEqual(acc, 50.0)

    def test_accuracy_bounded_min_zero(self):
        acc = self.manager.calculate_accuracy(
            solved=False,
            discovered_evidence_count=0,
            total_evidence_count=10,
            unnecessary_actions=50,
            hints_used=20
        )
        self.assertEqual(acc, 0.0)

    def test_accuracy_handles_none_and_invalid_safely(self):
        acc = self.manager.calculate_accuracy(
            solved=True,
            discovered_evidence_count=None,
            total_evidence_count=None,
            unnecessary_actions=-5,
            hints_used=-10
        )
        self.assertGreaterEqual(acc, 0.0)
        self.assertLessEqual(acc, 100.0)


class TestRanksAndConfig(unittest.TestCase):
    def setUp(self):
        self.manager = ScoreManager()

    def test_rank_progression(self):
        self.assertEqual(self.manager.get_rank(0), "Detective Rookie")
        self.assertEqual(self.manager.get_rank(299), "Detective Rookie")
        self.assertEqual(self.manager.get_rank(300), "Investigator")
        self.assertEqual(self.manager.get_rank(599), "Investigator")
        self.assertEqual(self.manager.get_rank(600), "Senior Detective")
        self.assertEqual(self.manager.get_rank(899), "Senior Detective")
        self.assertEqual(self.manager.get_rank(900), "Master Detective")
        self.assertEqual(self.manager.get_rank(1500), "Master Detective")

    def test_custom_config_validation(self):
        invalid_config = ScoringConfig(correct_suspect_points=-100)
        with self.assertRaises(ValueError):
            ScoreManager(config=invalid_config)


class TestGameControllerIntegration(unittest.TestCase):
    def setUp(self):
        self.controller = GameController(player_id="p1", player_name="Test Detective")

    def test_end_to_end_flow_integration(self):
        self.controller.load_case("case_001")
        self.controller.start_investigation()

        locations = self.controller.get_case_locations()
        for loc in locations:
            info = self.controller.explore_location(loc)
            for item in info["evidence_here"]:
                if not item["discovered"]:
                    self.controller.discover_evidence(item["evidence_id"])
            for item in info["clues_here"]:
                if not item["discovered"]:
                    self.controller.discover_clue(item["clue_id"])

        suspects = self.controller.get_case_suspects()
        if suspects:
            target = suspects[0]
            self.controller.start_interrogation(target.suspect_id)
            q = self.controller.ask_question("Where were you?", category="alibi")
            self.controller.record_answer(q.question_id, target.alibi)
            self.controller.end_interrogation()

        self.controller.run_ai_analysis()

        outcome = self.controller.conclude_case("Butler James")
        self.assertIn("score_info", outcome)
        score_info = outcome["score_info"]

        self.assertIn("score", score_info)
        self.assertIn("accuracy", score_info)
        self.assertIn("rank", score_info)
        self.assertIn("breakdown", score_info)

        self.assertGreater(score_info["score"], 0)
        self.assertGreaterEqual(score_info["accuracy"], 0.0)
        self.assertLessEqual(score_info["accuracy"], 100.0)
        self.assertIn(score_info["rank"], ["Detective Rookie", "Investigator", "Senior Detective", "Master Detective"])
        self.assertEqual(self.controller.player.investigation_score, score_info["score"])


if __name__ == "__main__":
    unittest.main()
