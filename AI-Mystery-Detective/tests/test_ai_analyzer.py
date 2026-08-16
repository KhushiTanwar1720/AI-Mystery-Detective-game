"""
Unit tests for the AIAnalyzer class (game/ai_analyzer.py).

Run with:
    python -m unittest tests.test_ai_analyzer
"""

import os
import sys
import unittest
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.ai_analyzer import (
    AIAnalyzer,
    AIProvider,
    AnalysisResult,
    RuleBasedAIProvider,
)
from game.case import Case
from game.clue import Clue
from game.evidence import Evidence
from game.suspect import Suspect


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def make_case(**overrides) -> Case:
    defaults = dict(
        case_id="case_test",
        title="The Test Case",
        description="A case used for testing.",
        location="Test Location",
        crime_type="theft",
        difficulty="easy",
        correct_suspect="Suspect A",
        suspects=["suspect_a", "suspect_b"],
        evidence=["ev1", "ev2"],
        clues=["cl1"],
    )
    defaults.update(overrides)
    return Case(**defaults)


def make_suspect(**overrides) -> Suspect:
    defaults = dict(
        suspect_id="suspect_a",
        name="Suspect A",
        age=40,
        occupation="Gardener",
        description="A gardener.",
        relationship_to_victim="Employee",
        alibi="Unknown",
        behavior=[],
        statements=[],
        suspicion_level=0,
    )
    defaults.update(overrides)
    return Suspect(**defaults)


def make_evidence(**overrides) -> Evidence:
    defaults = dict(
        evidence_id="ev1",
        name="Muddy Boots",
        description="Boots with fresh mud, matching the garden bed.",
        evidence_type="physical",
        location_found="Garden",
        importance="high",
        discovered=False,
        related_suspects=["suspect_a"],
    )
    defaults.update(overrides)
    return Evidence(**defaults)


def make_clue(**overrides) -> Clue:
    defaults = dict(
        clue_id="cl1",
        description="A torn note mentioning the garden.",
        source="crime scene inspection",
        location="Study",
        importance="medium",
        discovered=False,
        related_evidence=["ev1"],
        related_suspects=["suspect_a"],
    )
    defaults.update(overrides)
    return Clue(**defaults)


class FakeAIProvider(AIProvider):
    """A mocked/fake AI provider used to verify AIAnalyzer's provider hook."""

    def __init__(self, fixed_text: Optional[str] = None, raise_error: bool = False):
        self.fixed_text = fixed_text
        self.raise_error = raise_error
        self.calls: List[Dict[str, Any]] = []

    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        self.calls.append({"prompt": prompt, "context": context})
        if self.raise_error:
            raise RuntimeError("simulated provider failure")
        return self.fixed_text if self.fixed_text is not None else f"[fake] {prompt}"


def _contains_value(data: Any, needle: str) -> bool:
    """Recursively search a nested structure for an exact string value."""
    if isinstance(data, str):
        return data == needle
    if isinstance(data, dict):
        return any(_contains_value(k, needle) or _contains_value(v, needle) for k, v in data.items())
    if isinstance(data, (list, tuple, set)):
        return any(_contains_value(item, needle) for item in data)
    return False


# ---------------------------------------------------------------------------
# Construction / graceful handling of missing data
# ---------------------------------------------------------------------------


class TestAIAnalyzerConstruction(unittest.TestCase):
    def test_construct_with_no_data(self):
        analyzer = AIAnalyzer()
        self.assertEqual(analyzer.suspects, [])
        self.assertEqual(analyzer.evidence, [])
        self.assertEqual(analyzer.clues, [])
        self.assertIsInstance(analyzer.ai_provider, RuleBasedAIProvider)

    def test_case_info_accepts_case_object_via_get_info(self):
        case = make_case()
        analyzer = AIAnalyzer(case_info=case)
        self.assertEqual(analyzer.case_info["case_id"], "case_test")

    def test_case_info_never_retains_correct_suspect(self):
        case = make_case()
        # Even if a caller mistakenly hands over to_dict() output
        # (which includes the solution), AIAnalyzer must drop it.
        analyzer = AIAnalyzer(case_info=case.to_dict())
        self.assertNotIn("correct_suspect", analyzer.case_info)

    def test_update_data_replaces_only_given_fields(self):
        analyzer = AIAnalyzer(suspects=[make_suspect()])
        analyzer.update_data(evidence=[make_evidence()])
        self.assertEqual(len(analyzer.suspects), 1)
        self.assertEqual(len(analyzer.evidence), 1)


# ---------------------------------------------------------------------------
# analyze_evidence / analyze_clues
# ---------------------------------------------------------------------------


class TestAnalyzeEvidence(unittest.TestCase):
    def test_no_evidence_returns_warning(self):
        analyzer = AIAnalyzer()
        result = analyzer.analyze_evidence()
        self.assertIsInstance(result, AnalysisResult)
        self.assertEqual(result.data["total_evidence"], 0)
        self.assertTrue(result.warnings)

    def test_undiscovered_evidence_not_detailed(self):
        evidence = make_evidence(discovered=False)
        analyzer = AIAnalyzer(evidence=[evidence])
        result = analyzer.analyze_evidence()
        self.assertEqual(result.data["discovered_count"], 0)
        self.assertEqual(result.data["undiscovered_count"], 1)
        # Location is safe to surface even before discovery.
        self.assertIn("Garden", result.data["undiscovered_locations"])
        # But nothing links it to a suspect yet.
        self.assertEqual(result.data["evidence_per_suspect"], {})

    def test_discovered_evidence_is_tallied(self):
        evidence = make_evidence(discovered=True, importance="critical")
        analyzer = AIAnalyzer(evidence=[evidence])
        result = analyzer.analyze_evidence()
        self.assertEqual(result.data["discovered_count"], 1)
        self.assertEqual(result.data["by_importance"]["critical"], 1)
        self.assertEqual(result.data["evidence_per_suspect"]["suspect_a"], 1)


class TestAnalyzeClues(unittest.TestCase):
    def test_no_clues_returns_warning(self):
        analyzer = AIAnalyzer()
        result = analyzer.analyze_clues()
        self.assertEqual(result.data["total_clues"], 0)
        self.assertTrue(result.warnings)

    def test_discovered_clue_links(self):
        clue = make_clue(discovered=True)
        analyzer = AIAnalyzer(clues=[clue])
        result = analyzer.analyze_clues()
        self.assertEqual(result.data["discovered_count"], 1)
        self.assertEqual(result.data["clues_per_suspect"]["suspect_a"], 1)
        self.assertEqual(result.data["clues_per_evidence"]["ev1"], 1)


# ---------------------------------------------------------------------------
# compare_suspects
# ---------------------------------------------------------------------------


class TestCompareSuspects(unittest.TestCase):
    def test_no_suspects(self):
        analyzer = AIAnalyzer()
        result = analyzer.compare_suspects()
        self.assertEqual(result.data["profiles"], [])
        self.assertTrue(result.warnings)

    def test_profiles_and_no_alibi_flagging(self):
        a = make_suspect(suspect_id="suspect_a", name="A", alibi="Unknown")
        b = make_suspect(suspect_id="suspect_b", name="B", alibi="Was at the market.")
        analyzer = AIAnalyzer(suspects=[a, b])
        result = analyzer.compare_suspects()
        self.assertEqual(len(result.data["profiles"]), 2)
        self.assertIn("suspect_a", result.data["no_alibi"])
        self.assertNotIn("suspect_b", result.data["no_alibi"])

    def test_shared_alibi_detected(self):
        a = make_suspect(suspect_id="suspect_a", name="A", alibi="Was in the kitchen.")
        b = make_suspect(suspect_id="suspect_b", name="B", alibi="Was in the kitchen.")
        analyzer = AIAnalyzer(suspects=[a, b])
        result = analyzer.compare_suspects()
        self.assertEqual(len(result.data["shared_alibis"]), 1)
        self.assertCountEqual(
            result.data["shared_alibis"][0]["suspects"], ["suspect_a", "suspect_b"]
        )


# ---------------------------------------------------------------------------
# detect_inconsistencies
# ---------------------------------------------------------------------------


class TestDetectInconsistencies(unittest.TestCase):
    def test_no_statements_no_inconsistencies(self):
        suspect = make_suspect()
        analyzer = AIAnalyzer(suspects=[suspect])
        result = analyzer.detect_inconsistencies()
        self.assertEqual(result.data["inconsistencies"], [])

    def test_self_contradiction_detected(self):
        suspect = make_suspect()
        statements = {
            "suspect_a": [
                {"question": "Where were you?", "answer": "In the garden."},
                {"question": "Where were you?", "answer": "In the kitchen."},
            ]
        }
        analyzer = AIAnalyzer(suspects=[suspect], statements=statements)
        result = analyzer.detect_inconsistencies()
        types = [item["type"] for item in result.data["inconsistencies"]]
        self.assertIn("self_contradiction", types)

    def test_consistent_repeated_answer_not_flagged(self):
        suspect = make_suspect()
        statements = {
            "suspect_a": [
                {"question": "Where were you?", "answer": "In the garden."},
                {"question": "Where were you?", "answer": "in the garden."},
            ]
        }
        analyzer = AIAnalyzer(suspects=[suspect], statements=statements)
        result = analyzer.detect_inconsistencies()
        self.assertEqual(result.data["inconsistencies"], [])

    def test_alibi_conflict_heuristic(self):
        suspect = make_suspect(alibi="I was in the garden all evening.")
        statements = {"suspect_a": ["I was not in the garden at all."]}
        analyzer = AIAnalyzer(suspects=[suspect], statements=statements)
        result = analyzer.detect_inconsistencies()
        types = [item["type"] for item in result.data["inconsistencies"]]
        self.assertIn("alibi_conflict", types)


# ---------------------------------------------------------------------------
# calculate_suspicion
# ---------------------------------------------------------------------------


class TestCalculateSuspicion(unittest.TestCase):
    def test_no_suspects(self):
        analyzer = AIAnalyzer()
        result = analyzer.calculate_suspicion()
        self.assertEqual(result.data["scores"], [])

    def test_more_evidence_yields_higher_score(self):
        a = make_suspect(suspect_id="suspect_a", name="A")
        b = make_suspect(suspect_id="suspect_b", name="B")
        linked_evidence = make_evidence(
            evidence_id="ev1", discovered=True, importance="critical",
            related_suspects=["suspect_a"],
        )
        unlinked_evidence = make_evidence(
            evidence_id="ev2", discovered=True, importance="low",
            related_suspects=[],
        )
        analyzer = AIAnalyzer(
            suspects=[a, b], evidence=[linked_evidence, unlinked_evidence]
        )
        result = analyzer.calculate_suspicion()
        scores = {item["suspect_id"]: item["score"] for item in result.data["scores"]}
        self.assertGreater(scores["suspect_a"], scores["suspect_b"])

    def test_scores_are_ranked(self):
        a = make_suspect(suspect_id="suspect_a", name="A", suspicion_level=80)
        b = make_suspect(suspect_id="suspect_b", name="B", suspicion_level=10)
        analyzer = AIAnalyzer(suspects=[a, b])
        result = analyzer.calculate_suspicion()
        ranks = {item["suspect_id"]: item["rank"] for item in result.data["scores"]}
        self.assertEqual(ranks["suspect_a"], 1)
        self.assertEqual(ranks["suspect_b"], 2)

    def test_never_references_correct_suspect(self):
        case = make_case(correct_suspect="Suspect A")
        a = make_suspect(suspect_id="suspect_a", name="Suspect A")
        b = make_suspect(suspect_id="suspect_b", name="Suspect B")
        analyzer = AIAnalyzer(case_info=case.get_info(), suspects=[a, b])
        result = analyzer.calculate_suspicion()
        # The solution string should never leak into analysis output
        # via any special "this one is guilty" marker/field.
        self.assertNotIn("is_guilty", str(result.data))
        self.assertNotIn("correct_suspect", result.to_dict())


# ---------------------------------------------------------------------------
# generate_hints (uses mocked/fake AI provider)
# ---------------------------------------------------------------------------


class TestGenerateHints(unittest.TestCase):
    def test_invalid_max_hints_raises(self):
        analyzer = AIAnalyzer()
        with self.assertRaises(ValueError):
            analyzer.generate_hints(max_hints=0)
        with self.assertRaises(ValueError):
            analyzer.generate_hints(max_hints=-1)

    def test_no_data_returns_fallback_hint(self):
        analyzer = AIAnalyzer()
        result = analyzer.generate_hints()
        self.assertEqual(len(result.data["hints"]), 1)

    def test_undiscovered_evidence_produces_hint_with_default_provider(self):
        evidence = make_evidence(discovered=False, location_found="Garden")
        analyzer = AIAnalyzer(evidence=[evidence])
        result = analyzer.generate_hints(max_hints=3)
        self.assertTrue(any("Garden" in hint for hint in result.data["hints"]))

    def test_uses_supplied_ai_provider(self):
        fake_provider = FakeAIProvider(fixed_text="A custom hint from the fake model.")
        evidence = make_evidence(discovered=False, location_found="Garden")
        analyzer = AIAnalyzer(evidence=[evidence], ai_provider=fake_provider)
        result = analyzer.generate_hints(max_hints=1)
        self.assertEqual(result.data["hints"], ["A custom hint from the fake model."])
        self.assertEqual(len(fake_provider.calls), 1)

    def test_provider_failure_falls_back_to_template(self):
        failing_provider = FakeAIProvider(raise_error=True)
        evidence = make_evidence(discovered=False, location_found="Garden")
        analyzer = AIAnalyzer(evidence=[evidence], ai_provider=failing_provider)
        result = analyzer.generate_hints(max_hints=1)
        # Should not raise, and should still produce a usable hint.
        self.assertTrue(result.data["hints"])
        self.assertIn("Garden", result.data["hints"][0])

    def test_max_hints_respected(self):
        evidences = [
            make_evidence(
                evidence_id=f"ev{i}", discovered=False, location_found=f"Room {i}"
            )
            for i in range(5)
        ]
        analyzer = AIAnalyzer(evidence=evidences)
        result = analyzer.generate_hints(max_hints=2)
        self.assertLessEqual(len(result.data["hints"]), 2)


# ---------------------------------------------------------------------------
# generate_investigation_summary
# ---------------------------------------------------------------------------


class TestGenerateInvestigationSummary(unittest.TestCase):
    def test_summary_structure(self):
        case = make_case()
        suspects = [make_suspect(suspect_id="suspect_a", name="Suspect A")]
        evidence = [make_evidence(discovered=True)]
        clues = [make_clue(discovered=True)]
        analyzer = AIAnalyzer(
            case_info=case.get_info(),
            suspects=suspects,
            evidence=evidence,
            clues=clues,
        )
        result = analyzer.generate_investigation_summary()
        for key in (
            "case",
            "progress",
            "evidence_analysis",
            "clue_analysis",
            "suspect_comparison",
            "inconsistencies",
            "suspicion_scores",
            "hints",
            "narrative",
        ):
            self.assertIn(key, result.data)

        self.assertEqual(result.data["progress"]["evidence_discovered"], 1)
        self.assertEqual(result.data["progress"]["clues_discovered"], 1)

    def test_summary_never_leaks_correct_suspect(self):
        case = make_case(correct_suspect="Suspect A")
        suspects = [
            make_suspect(suspect_id="suspect_a", name="Suspect A"),
            make_suspect(suspect_id="suspect_b", name="Suspect B"),
        ]
        analyzer = AIAnalyzer(case_info=case.get_info(), suspects=suspects)
        result = analyzer.generate_investigation_summary()
        self.assertFalse(_contains_value(result.data, "Suspect A is guilty"))
        self.assertNotIn("correct_suspect", result.data["case"])

    def test_hints_can_be_excluded(self):
        analyzer = AIAnalyzer(suspects=[make_suspect()])
        result = analyzer.generate_investigation_summary(include_hints=False)
        self.assertNotIn("hints", result.data)

    def test_uses_supplied_provider_for_narrative(self):
        fake_provider = FakeAIProvider(fixed_text="Custom narrative text.")
        analyzer = AIAnalyzer(suspects=[make_suspect()], ai_provider=fake_provider)
        result = analyzer.generate_investigation_summary()
        self.assertEqual(result.data["narrative"], "Custom narrative text.")


# ---------------------------------------------------------------------------
# AnalysisResult / RuleBasedAIProvider
# ---------------------------------------------------------------------------


class TestAnalysisResultAndProvider(unittest.TestCase):
    def test_analysis_result_to_dict(self):
        result = AnalysisResult(success=True, summary="ok", data={"a": 1})
        as_dict = result.to_dict()
        self.assertEqual(as_dict["success"], True)
        self.assertEqual(as_dict["data"], {"a": 1})
        self.assertIn("generated_at", as_dict)

    def test_rule_based_provider_formats_template(self):
        provider = RuleBasedAIProvider()
        text = provider.generate_text(
            prompt="fallback",
            context={"template": "Hello {name}!", "name": "Detective"},
        )
        self.assertEqual(text, "Hello Detective!")

    def test_rule_based_provider_falls_back_on_bad_template(self):
        provider = RuleBasedAIProvider()
        text = provider.generate_text(
            prompt="fallback text",
            context={"template": "Hello {missing_key}!"},
        )
        self.assertEqual(text, "fallback text")


if __name__ == "__main__":
    unittest.main()
