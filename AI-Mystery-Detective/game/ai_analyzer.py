"""
AI analysis module for AI Mystery Detective.

Defines the `AIAnalyzer` class, which reads investigation data
(case info, suspects, evidence, clues, statements, and investigation
history) and produces structured analysis: evidence/clue breakdowns,
suspect comparisons, inconsistency detection, suspicion scoring, and
hints. It is the "AI logic" layer of the project.

Design notes
------------
- **Separation of concerns**: this module never mutates game state
  (`game.case`, `game.suspect`, `game.evidence`, `game.clue`,
  `game.investigation`) and never renders anything. It only reads the
  data it is handed and returns structured, JSON-friendly results.
  Wiring analysis results into gameplay or a UI is left to callers.

- **No spoilers**: `AIAnalyzer` is never given, and never reads,
  `Case.correct_suspect`. Callers should pass case information as the
  dictionary returned by `Case.get_info()` (or an equivalent plain
  dict), not `Case.to_dict()`. Evidence and clues are only inspected
  through their own discovery-gated `get_info()`, so undiscovered
  details never leak into an analysis result. Suspicion scores and
  suspect comparisons rank suspects relative to one another -- they
  never assert who is guilty.

- **Replaceable AI layer**: the actual number-crunching (evidence
  tallies, suspicion scoring, inconsistency detection) is plain,
  deterministic Python and doesn't depend on any external service.
  Natural-language phrasing (hints, the investigation summary
  narrative) is delegated to an `AIProvider`. The default
  `RuleBasedAIProvider` is a local, template-based implementation
  that requires no API key and no network access. Swapping in a
  different model or provider (e.g. an LLM-backed one) only requires
  implementing the small `AIProvider` interface and passing it to
  `AIAnalyzer(ai_provider=...)`; no other code in this module needs
  to change. Provider implementations are responsible for sourcing
  any credentials they need (e.g. from environment variables) --
  this module never accepts or stores API keys/secrets.

- **Graceful degradation**: every analysis method accepts missing or
  empty input without raising. When there isn't enough data for a
  meaningful analysis, the returned `AnalysisResult` still has a
  well-formed `data` payload (zeros/empty collections) plus a
  `warnings` list explaining what was missing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from game.clue import Clue
from game.evidence import Evidence
from game.suspect import Suspect

# Mirrors game.evidence.VALID_IMPORTANCE_LEVELS / game.clue.VALID_IMPORTANCE_LEVELS.
# Used to turn importance labels into a numeric weight for scoring.
IMPORTANCE_WEIGHTS: Dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 5,
}

# Loose, non-exhaustive set of keywords that, when found in a
# suspect's recorded behavior notes, nudge their suspicion score up.
# Kept as plain substring matches (case-insensitive) rather than NLP
# so the scoring stays deterministic and dependency-free.
SUSPICIOUS_BEHAVIOR_KEYWORDS: Sequence[str] = (
    "nervous",
    "lied",
    "lying",
    "evasive",
    "fled",
    "threatened",
    "aggressive",
    "avoided eye contact",
    "sweating",
    "stammered",
    "suspicious",
    "hesitated",
)

# Suspicion-score weighting for each contributing signal. Exposed as a
# module-level constant (rather than buried inside a method) so a
# caller can inspect or, if they build their own AIAnalyzer subclass,
# override the balance between signals without touching the scoring
# logic itself.
SUSPICION_SIGNAL_WEIGHTS: Dict[str, float] = {
    "base_suspicion": 0.35,
    "evidence": 0.25,
    "clues": 0.15,
    "inconsistencies": 0.15,
    "behavior": 0.07,
    "no_alibi": 0.03,
}

# A single statement/answer record, normalized from whatever shape the
# caller supplies (see AIAnalyzer._normalize_statements).
StatementRecord = Dict[str, Optional[str]]

# Case info is expected to be a plain dict (typically Case.get_info())
# or any object exposing get_info() -> Dict[str, Any]. Never
# Case.to_dict(), which includes the solution.
CaseInfoLike = Union[Dict[str, Any], Any]


# ---------------------------------------------------------------------------
# Replaceable AI provider interface
# ---------------------------------------------------------------------------


class AIProvider(ABC):
    """Interface for pluggable natural-language generation backends.

    `AIAnalyzer` uses an `AIProvider` only for phrasing -- turning
    already-computed, structured facts into readable hint/summary
    text. All actual reasoning (what counts as suspicious, which
    statements contradict each other, etc.) happens in `AIAnalyzer`
    itself and does not depend on the provider, so swapping providers
    never changes *what* is discovered, only how it reads.

    To integrate a different AI provider or model (e.g. a hosted
    LLM), subclass `AIProvider`, implement `generate_text`, and pass
    an instance to `AIAnalyzer(ai_provider=...)`. Implementations are
    responsible for their own configuration (endpoints, credentials,
    timeouts, etc.) -- none of that belongs in this module.
    """

    @abstractmethod
    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a short piece of natural-language text.

        Args:
            prompt: Instruction describing what to write (e.g. "write
                a one-sentence investigative hint about ...").
            context: Optional structured facts the implementation may
                use to ground its output.

        Returns:
            Generated text. Implementations should raise on failure
            rather than returning an empty string, so callers in this
            module can fall back to a template deterministically.
        """
        raise NotImplementedError


class RuleBasedAIProvider(AIProvider):
    """Default, local, dependency-free `AIProvider`.

    Produces serviceable phrasing by lightly templating the supplied
    `context`, without any external API calls or model weights. This
    is what `AIAnalyzer` uses when no provider is supplied, so the
    module works fully offline and never requires an API key.
    """

    def generate_text(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        context = context or {}
        template = context.get("template")
        if isinstance(template, str) and template.strip():
            try:
                return template.format(**context)
            except (KeyError, IndexError):
                # Fall through to returning the raw prompt if the
                # template references a key that wasn't supplied.
                pass
        return prompt


# ---------------------------------------------------------------------------
# Structured result wrapper
# ---------------------------------------------------------------------------


@dataclass
class AnalysisResult:
    """Structured, JSON-friendly result returned by every analysis method.

    Attributes:
        success: True if the analysis ran and produced meaningful
            output. False only for cases where the request itself was
            invalid (currently unused by `AIAnalyzer`'s own methods,
            which prefer `warnings` over failing outright).
        summary: A short, human-readable one-line description of the
            result, safe to display directly.
        data: The full structured payload. Shape depends on which
            method produced it (documented on each method).
        warnings: Human-readable notes about missing/incomplete input
            that affected this result. Empty when nothing was
            missing.
        generated_at: UTC ISO-8601 timestamp of when this result was
            produced.
    """

    success: bool
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Return this result as a plain, JSON-serializable dictionary."""
        return {
            "success": self.success,
            "summary": self.summary,
            "data": self.data,
            "warnings": list(self.warnings),
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# AIAnalyzer
# ---------------------------------------------------------------------------


class AIAnalyzer:
    """Analyzes investigation data and returns structured findings.

    `AIAnalyzer` is a read-only observer over the data it is given at
    construction time (or refreshed via `update_data`). It never
    mutates `Suspect`/`Evidence`/`Clue`/`Case` objects and never
    decides -- let alone reveals -- who the guilty suspect is; the
    `Case.correct_suspect` field is intentionally never accepted or
    consulted anywhere in this class.

    Typical usage::

        analyzer = AIAnalyzer(
            case_info=case.get_info(),
            suspects=suspect_manager.get_suspects_for_case(case),
            evidence=[evidence_manager.get_evidence(eid) for eid in case.evidence],
            clues=[clue_manager.get_clue(cid) for cid in case.clues],
        )
        result = analyzer.calculate_suspicion()
    """

    def __init__(
        self,
        case_info: Optional[CaseInfoLike] = None,
        suspects: Optional[List[Suspect]] = None,
        evidence: Optional[List[Evidence]] = None,
        clues: Optional[List[Clue]] = None,
        statements: Optional[Dict[str, List[Union[str, Dict[str, str]]]]] = None,
        investigation_history: Optional[List[Dict[str, Any]]] = None,
        ai_provider: Optional[AIProvider] = None,
    ) -> None:
        """Create a new analyzer over a snapshot of investigation data.

        All data arguments are optional so the analyzer can be built
        incrementally or reused across a growing investigation (see
        `update_data`). Every analysis method is written to tolerate
        missing/empty data rather than raising.

        Args:
            case_info: Case metadata as a dict (e.g. `Case.get_info()`)
                or any object exposing a `get_info()` method. Must NOT
                be `Case.to_dict()` output or otherwise include
                `correct_suspect` -- if it does, that field is
                dropped and never stored.
            suspects: `Suspect` objects involved in the case.
            evidence: `Evidence` objects belonging to the case. Only
                each item's own discovery-gated `get_info()` is ever
                read, so undiscovered evidence details are never
                inspected.
            clues: `Clue` objects belonging to the case. Same
                discovery-gating as `evidence`.
            statements: Optional mapping of suspect id/name to a list
                of statements. Each statement may be a plain string,
                or a dict with `"question"` and `"answer"` keys (as
                produced by pairing `game.interrogation.Question` and
                `Statement`). If omitted, statements are derived from
                each `Suspect.get_statements()` instead (as
                unstructured strings).
            investigation_history: Optional action log, typically
                `Investigation.get_history()` output -- a list of
                `{"action": ..., "timestamp": ..., "details": ...}`
                entries.
            ai_provider: Optional pluggable text-generation backend
                (see `AIProvider`). Defaults to `RuleBasedAIProvider`,
                which is local and requires no credentials.
        """
        self.case_info: Dict[str, Any] = self._normalize_case_info(case_info)
        self.suspects: List[Suspect] = list(suspects) if suspects else []
        self.evidence: List[Evidence] = list(evidence) if evidence else []
        self.clues: List[Clue] = list(clues) if clues else []
        self.statements: Dict[str, List[StatementRecord]] = self._normalize_statements(
            statements
        )
        self.investigation_history: List[Dict[str, Any]] = (
            [dict(entry) for entry in investigation_history]
            if investigation_history
            else []
        )
        self.ai_provider: AIProvider = ai_provider or RuleBasedAIProvider()

    # -- Setup / data refresh ------------------------------------------------

    @staticmethod
    def _normalize_case_info(case_info: Optional[CaseInfoLike]) -> Dict[str, Any]:
        """Coerce `case_info` into a plain dict, dropping any solution field."""
        if case_info is None:
            data: Dict[str, Any] = {}
        elif isinstance(case_info, dict):
            data = dict(case_info)
        elif hasattr(case_info, "get_info") and callable(case_info.get_info):
            data = dict(case_info.get_info())
        else:
            data = {}
        # Defense in depth: even if a caller mistakenly passes
        # to_dict()-shaped data, never retain the solution.
        data.pop("correct_suspect", None)
        return data

    @staticmethod
    def _normalize_statements(
        statements: Optional[Dict[str, List[Union[str, Dict[str, str]]]]]
    ) -> Dict[str, List[StatementRecord]]:
        """Normalize caller-supplied statements into a consistent shape.

        Each entry becomes `{"question": Optional[str], "answer": str}`.
        Plain strings become `{"question": None, "answer": <text>}`.
        """
        normalized: Dict[str, List[StatementRecord]] = {}
        if not statements:
            return normalized

        for suspect_key, entries in statements.items():
            if not entries:
                continue
            records: List[StatementRecord] = []
            for entry in entries:
                if isinstance(entry, str):
                    if entry.strip():
                        records.append({"question": None, "answer": entry})
                elif isinstance(entry, dict):
                    answer = entry.get("answer")
                    if isinstance(answer, str) and answer.strip():
                        records.append(
                            {
                                "question": entry.get("question")
                                or entry.get("question_text"),
                                "answer": answer,
                            }
                        )
            if records:
                normalized[suspect_key] = records
        return normalized

    def update_data(
        self,
        case_info: Optional[CaseInfoLike] = None,
        suspects: Optional[List[Suspect]] = None,
        evidence: Optional[List[Evidence]] = None,
        clues: Optional[List[Clue]] = None,
        statements: Optional[Dict[str, List[Union[str, Dict[str, str]]]]] = None,
        investigation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Refresh some or all of the analyzer's data snapshot.

        Only arguments that are not `None` are replaced; omitted
        arguments keep their current value. Useful for re-running
        analysis as an investigation progresses without rebuilding a
        new `AIAnalyzer`.
        """
        if case_info is not None:
            self.case_info = self._normalize_case_info(case_info)
        if suspects is not None:
            self.suspects = list(suspects)
        if evidence is not None:
            self.evidence = list(evidence)
        if clues is not None:
            self.clues = list(clues)
        if statements is not None:
            self.statements = self._normalize_statements(statements)
        if investigation_history is not None:
            self.investigation_history = [dict(e) for e in investigation_history]

    # -- Internal helpers ------------------------------------------------

    def _suspect_label(self, suspect: Suspect) -> str:
        """Return the id used to key this suspect across statements/links."""
        return suspect.suspect_id

    def _discovered_evidence_info(self) -> List[Dict[str, Any]]:
        return [e.get_info() for e in self.evidence if e.is_discovered()]

    def _discovered_clue_info(self) -> List[Dict[str, Any]]:
        return [c.get_info() for c in self.clues if c.is_discovered()]

    def _statements_for(self, suspect: Suspect) -> List[StatementRecord]:
        """Return normalized statement records for a suspect.

        Prefers explicitly supplied `self.statements` (keyed by
        `suspect_id` or `name`); falls back to the suspect's own
        `get_statements()` (plain strings, no question association).
        """
        for key in (suspect.suspect_id, suspect.name):
            if key in self.statements:
                return self.statements[key]
        return [
            {"question": None, "answer": text} for text in suspect.get_statements()
        ]

    @staticmethod
    def _importance_weight(importance: Optional[str]) -> int:
        return IMPORTANCE_WEIGHTS.get(importance or "", 0)

    # -- analyze_evidence -----------------------------------------------------

    def analyze_evidence(self) -> AnalysisResult:
        """Summarize the case's evidence: discovery, type, and importance.

        Only discovered evidence is inspected in detail (via
        `Evidence.get_info()`); undiscovered items are counted but
        not otherwise described.

        Returns:
            `AnalysisResult` with `data` containing:
                - `total_evidence`, `discovered_count`,
                  `undiscovered_count`
                - `by_importance`: counts of discovered evidence per
                  importance level
                - `by_type`: counts of discovered evidence per
                  `evidence_type`
                - `evidence_per_suspect`: counts of discovered
                  evidence linked to each suspect id
                - `undiscovered_locations`: locations where
                  undiscovered evidence is known to be (safe to
                  surface -- `location_found` is not discovery-gated)
        """
        warnings: List[str] = []
        if not self.evidence:
            warnings.append("No evidence data was provided for this case.")

        discovered = self._discovered_evidence_info()
        undiscovered = [e for e in self.evidence if not e.is_discovered()]

        if self.evidence and not discovered:
            warnings.append("No evidence has been discovered yet.")

        by_importance = Counter(item.get("importance", "unknown") for item in discovered)
        by_type = Counter(item.get("evidence_type", "unknown") for item in discovered)

        evidence_per_suspect: Counter = Counter()
        for item in discovered:
            for suspect_ref in item.get("related_suspects", []):
                evidence_per_suspect[suspect_ref] += 1

        undiscovered_locations = sorted({e.location_found for e in undiscovered})

        data = {
            "total_evidence": len(self.evidence),
            "discovered_count": len(discovered),
            "undiscovered_count": len(undiscovered),
            "by_importance": dict(by_importance),
            "by_type": dict(by_type),
            "evidence_per_suspect": dict(evidence_per_suspect),
            "undiscovered_locations": undiscovered_locations,
        }

        summary = (
            f"{len(discovered)} of {len(self.evidence)} evidence item(s) discovered."
            if self.evidence
            else "No evidence available to analyze."
        )
        return AnalysisResult(success=True, summary=summary, data=data, warnings=warnings)

    # -- analyze_clues --------------------------------------------------------

    def analyze_clues(self) -> AnalysisResult:
        """Summarize the case's clues: discovery, source, and connections.

        Mirrors `analyze_evidence`, but for clues, and also reports
        how clues connect to evidence items.

        Returns:
            `AnalysisResult` with `data` containing:
                - `total_clues`, `discovered_count`,
                  `undiscovered_count`
                - `by_importance`: counts of discovered clues per
                  importance level
                - `by_source`: counts of discovered clues per
                  `source`
                - `clues_per_suspect`: counts of discovered clues
                  linked to each suspect id
                - `clues_per_evidence`: counts of discovered clues
                  linked to each evidence id
                - `undiscovered_locations`: locations where
                  undiscovered clues are known to be
        """
        warnings: List[str] = []
        if not self.clues:
            warnings.append("No clue data was provided for this case.")

        discovered = self._discovered_clue_info()
        undiscovered = [c for c in self.clues if not c.is_discovered()]

        if self.clues and not discovered:
            warnings.append("No clues have been discovered yet.")

        by_importance = Counter(item.get("importance", "unknown") for item in discovered)
        by_source = Counter(item.get("source", "unknown") for item in discovered)

        clues_per_suspect: Counter = Counter()
        clues_per_evidence: Counter = Counter()
        for item in discovered:
            for suspect_ref in item.get("related_suspects", []):
                clues_per_suspect[suspect_ref] += 1
            for evidence_ref in item.get("related_evidence", []):
                clues_per_evidence[evidence_ref] += 1

        undiscovered_locations = sorted({c.location for c in undiscovered})

        data = {
            "total_clues": len(self.clues),
            "discovered_count": len(discovered),
            "undiscovered_count": len(undiscovered),
            "by_importance": dict(by_importance),
            "by_source": dict(by_source),
            "clues_per_suspect": dict(clues_per_suspect),
            "clues_per_evidence": dict(clues_per_evidence),
            "undiscovered_locations": undiscovered_locations,
        }

        summary = (
            f"{len(discovered)} of {len(self.clues)} clue(s) discovered."
            if self.clues
            else "No clues available to analyze."
        )
        return AnalysisResult(success=True, summary=summary, data=data, warnings=warnings)

    # -- compare_suspects -------------------------------------------------

    def compare_suspects(self) -> AnalysisResult:
        """Build a side-by-side comparison of all suspects.

        This method reports *differences and similarities* between
        suspects on observable attributes -- it does not compute or
        expose any notion of guilt (see `calculate_suspicion` for
        relative suspicion scoring).

        Returns:
            `AnalysisResult` with `data` containing:
                - `profiles`: one entry per suspect with
                  `suspect_id`, `name`, `has_alibi`,
                  `statement_count`, `behavior_count`,
                  `suspicion_level`, `occupation`,
                  `relationship_to_victim`
                - `shared_alibis`: groups of suspects who gave the
                  exact same alibi text (worth double-checking)
                - `shared_occupations`: groups of suspects sharing an
                  occupation
                - `no_alibi`: suspect ids whose alibi is still
                  "Unknown"
        """
        warnings: List[str] = []
        if not self.suspects:
            warnings.append("No suspect data was provided for this case.")
            return AnalysisResult(
                success=True,
                summary="No suspects available to compare.",
                data={
                    "profiles": [],
                    "shared_alibis": [],
                    "shared_occupations": [],
                    "no_alibi": [],
                },
                warnings=warnings,
            )

        profiles: List[Dict[str, Any]] = []
        alibi_groups: Dict[str, List[str]] = {}
        occupation_groups: Dict[str, List[str]] = {}
        no_alibi: List[str] = []

        for suspect in self.suspects:
            has_alibi = suspect.alibi.strip().lower() != "unknown"
            profiles.append(
                {
                    "suspect_id": suspect.suspect_id,
                    "name": suspect.name,
                    "occupation": suspect.occupation,
                    "relationship_to_victim": suspect.relationship_to_victim,
                    "has_alibi": has_alibi,
                    "statement_count": len(self._statements_for(suspect)),
                    "behavior_count": len(suspect.behavior),
                    "suspicion_level": suspect.suspicion_level,
                }
            )

            if not has_alibi:
                no_alibi.append(suspect.suspect_id)

            alibi_key = suspect.alibi.strip().lower()
            alibi_groups.setdefault(alibi_key, []).append(suspect.suspect_id)

            occupation_key = suspect.occupation.strip().lower()
            occupation_groups.setdefault(occupation_key, []).append(suspect.suspect_id)

        shared_alibis = [
            {"alibi": key, "suspects": ids}
            for key, ids in alibi_groups.items()
            if len(ids) > 1
        ]
        shared_occupations = [
            {"occupation": key, "suspects": ids}
            for key, ids in occupation_groups.items()
            if len(ids) > 1
        ]

        data = {
            "profiles": profiles,
            "shared_alibis": shared_alibis,
            "shared_occupations": shared_occupations,
            "no_alibi": no_alibi,
        }
        summary = f"Compared {len(profiles)} suspect(s)."
        return AnalysisResult(success=True, summary=summary, data=data, warnings=warnings)

    # -- detect_inconsistencies ------------------------------------------

    def detect_inconsistencies(self) -> AnalysisResult:
        """Flag possible contradictions in suspects' statements/alibis.

        Two checks are performed, both purely rule-based:

        1. **Self-contradiction**: among a suspect's statement
           records that share the same (normalized) question text,
           are there two or more distinct answers?
        2. **Alibi/statement conflict**: does any of a suspect's
           statements contain an explicit negation ("not", "n't",
           "never") of a distinctive word from their own stated
           alibi? This is a coarse heuristic, not a semantic
           analysis, and is meant to surface things worth the
           player's attention rather than to be authoritative.

        Returns:
            `AnalysisResult` with `data["inconsistencies"]`: a list of
            `{"suspect_id", "type", "detail"}` records. Empty if none
            were found (or if there wasn't enough data to check).
        """
        warnings: List[str] = []
        if not self.suspects:
            warnings.append("No suspect data was provided for this case.")

        inconsistencies: List[Dict[str, Any]] = []

        for suspect in self.suspects:
            records = self._statements_for(suspect)
            if not records:
                continue

            # -- Self-contradiction across repeated questions --------
            by_question: Dict[str, List[str]] = {}
            for record in records:
                question = record.get("question")
                if not question:
                    continue
                key = question.strip().lower()
                by_question.setdefault(key, []).append(record["answer"])

            for question_key, answers in by_question.items():
                distinct = {a.strip().lower() for a in answers}
                if len(distinct) > 1:
                    inconsistencies.append(
                        {
                            "suspect_id": suspect.suspect_id,
                            "type": "self_contradiction",
                            "detail": (
                                f"Gave differing answers to the same question "
                                f"({len(distinct)} distinct answers recorded)."
                            ),
                            "question": records[0].get("question") or question_key,
                            "answers": answers,
                        }
                    )

            # -- Alibi vs. statement negation heuristic ---------------
            alibi = suspect.alibi.strip()
            if alibi and alibi.lower() != "unknown":
                alibi_words = {
                    w.strip(".,!?").lower()
                    for w in alibi.split()
                    if len(w.strip(".,!?")) > 3
                }
                for record in records:
                    answer_lower = record["answer"].lower()
                    if "not" not in answer_lower and "n't" not in answer_lower and "never" not in answer_lower:
                        continue
                    if any(word in answer_lower for word in alibi_words):
                        inconsistencies.append(
                            {
                                "suspect_id": suspect.suspect_id,
                                "type": "alibi_conflict",
                                "detail": (
                                    "A statement appears to negate part of "
                                    "this suspect's own stated alibi."
                                ),
                                "alibi": suspect.alibi,
                                "statement": record["answer"],
                            }
                        )

        data = {"inconsistencies": inconsistencies}
        summary = (
            f"Found {len(inconsistencies)} potential inconsistency(ies)."
            if inconsistencies
            else "No inconsistencies detected in the available statements."
        )
        return AnalysisResult(success=True, summary=summary, data=data, warnings=warnings)

    # -- calculate_suspicion -----------------------------------------------

    def calculate_suspicion(self) -> AnalysisResult:
        """Compute a relative suspicion score for each suspect.

        The score blends several observable signals -- it is an
        investigative aid for the player, not a verdict, and it is
        computed without ever consulting `Case.correct_suspect`
        (which this class never even receives). Signals combined:

        - the suspect's own recorded `suspicion_level` (set via
          gameplay, e.g. `Suspect.update_suspicion_level`)
        - discovered evidence linked to the suspect (weighted by
          importance)
        - discovered clues linked to the suspect (weighted by
          importance)
        - inconsistencies attributed to the suspect (from
          `detect_inconsistencies`)
        - suspicious-sounding recorded behavior (keyword heuristic)
        - having no stated alibi

        Returns:
            `AnalysisResult` with `data["scores"]`: a list of
            `{"suspect_id", "name", "score", "breakdown", "rank"}`
            records sorted by score descending (ties broken by
            `suspect_id` for stable, deterministic output). `score`
            is on a roughly 0-100 scale but is not clamped, since a
            suspect with many strong signals can legitimately exceed
            other suspects by a wide margin.
        """
        warnings: List[str] = []
        if not self.suspects:
            warnings.append("No suspect data was provided for this case.")
            return AnalysisResult(
                success=True,
                summary="No suspects available to score.",
                data={"scores": []},
                warnings=warnings,
            )

        evidence_by_suspect = self.analyze_evidence().data.get("evidence_per_suspect", {})
        clues_by_suspect = self.analyze_clues().data.get("clues_per_suspect", {})
        inconsistencies_by_suspect: Counter = Counter()
        for item in self.detect_inconsistencies().data.get("inconsistencies", []):
            inconsistencies_by_suspect[item["suspect_id"]] += 1

        scored: List[Dict[str, Any]] = []
        for suspect in self.suspects:
            sid = suspect.suspect_id

            base = suspect.suspicion_level * SUSPICION_SIGNAL_WEIGHTS["base_suspicion"]

            evidence_hits = evidence_by_suspect.get(sid, 0) or evidence_by_suspect.get(
                suspect.name, 0
            )
            evidence_component = min(evidence_hits, 10) * 10 * SUSPICION_SIGNAL_WEIGHTS["evidence"]

            clue_hits = clues_by_suspect.get(sid, 0) or clues_by_suspect.get(suspect.name, 0)
            clue_component = min(clue_hits, 10) * 10 * SUSPICION_SIGNAL_WEIGHTS["clues"]

            inconsistency_hits = inconsistencies_by_suspect.get(sid, 0)
            inconsistency_component = (
                min(inconsistency_hits, 5) * 20 * SUSPICION_SIGNAL_WEIGHTS["inconsistencies"]
            )

            behavior_hits = sum(
                1
                for note in suspect.behavior
                if any(keyword in note.lower() for keyword in SUSPICIOUS_BEHAVIOR_KEYWORDS)
            )
            behavior_component = min(behavior_hits, 5) * 20 * SUSPICION_SIGNAL_WEIGHTS["behavior"]

            no_alibi_component = (
                100 * SUSPICION_SIGNAL_WEIGHTS["no_alibi"]
                if suspect.alibi.strip().lower() == "unknown"
                else 0.0
            )

            total = (
                base
                + evidence_component
                + clue_component
                + inconsistency_component
                + behavior_component
                + no_alibi_component
            )

            scored.append(
                {
                    "suspect_id": sid,
                    "name": suspect.name,
                    "score": round(total, 2),
                    "breakdown": {
                        "base_suspicion": round(base, 2),
                        "evidence": round(evidence_component, 2),
                        "clues": round(clue_component, 2),
                        "inconsistencies": round(inconsistency_component, 2),
                        "behavior": round(behavior_component, 2),
                        "no_alibi": round(no_alibi_component, 2),
                    },
                }
            )

        scored.sort(key=lambda item: (-item["score"], item["suspect_id"]))
        for rank, item in enumerate(scored, start=1):
            item["rank"] = rank

        summary = f"Scored {len(scored)} suspect(s) based on available evidence."
        return AnalysisResult(
            success=True, summary=summary, data={"scores": scored}, warnings=warnings
        )

    # -- generate_hints -----------------------------------------------------

    def generate_hints(self, max_hints: int = 3) -> AnalysisResult:
        """Generate a small number of investigative hints.

        Hints point toward under-explored parts of the case (an
        undiscovered evidence/clue location, a suspect with few
        recorded statements, or a detected inconsistency) without
        stating or implying who is guilty. Phrasing is produced via
        `self.ai_provider`; if the provider raises or is unavailable,
        a deterministic template is used instead so this method never
        fails outright because of the provider.

        Args:
            max_hints: Maximum number of hints to return. Must be a
                positive integer.

        Returns:
            `AnalysisResult` with `data["hints"]`: a list of hint
            strings (possibly empty if nothing stands out to hint
            about).

        Raises:
            ValueError: If `max_hints` is not a positive integer.
        """
        if not isinstance(max_hints, int) or isinstance(max_hints, bool) or max_hints <= 0:
            raise ValueError("max_hints must be a positive integer")

        warnings: List[str] = []
        candidates: List[Dict[str, Any]] = []

        evidence_analysis = self.analyze_evidence().data
        for location in evidence_analysis.get("undiscovered_locations", []):
            candidates.append(
                {
                    "template": "There may be more to find at {location}.",
                    "location": location,
                }
            )

        clue_analysis = self.analyze_clues().data
        for location in clue_analysis.get("undiscovered_locations", []):
            candidates.append(
                {
                    "template": "It might be worth looking closer around {location}.",
                    "location": location,
                }
            )

        inconsistencies = self.detect_inconsistencies().data.get("inconsistencies", [])
        if inconsistencies:
            candidates.append(
                {
                    "template": (
                        "Something one of the suspects said doesn't quite "
                        "line up -- it may be worth reviewing their "
                        "statements again."
                    ),
                }
            )

        for suspect in self.suspects:
            if len(self._statements_for(suspect)) == 0:
                candidates.append(
                    {
                        "template": "You haven't questioned {name} yet.",
                        "name": suspect.name,
                    }
                )

        if not self.evidence and not self.clues and not self.suspects:
            warnings.append("No investigation data was provided; hints are limited.")

        hints: List[str] = []
        for candidate in candidates[:max_hints]:
            template = candidate["template"]
            try:
                text = self.ai_provider.generate_text(
                    prompt=template.format(**{k: v for k, v in candidate.items() if k != "template"}),
                    context=candidate,
                )
            except Exception:  # pragma: no cover - defensive fallback
                text = template.format(**{k: v for k, v in candidate.items() if k != "template"})
            hints.append(text)

        if not hints:
            hints.append(
                "Nothing new stands out right now -- review what the "
                "suspects have told you so far."
            )

        summary = f"Generated {len(hints)} hint(s)."
        return AnalysisResult(
            success=True, summary=summary, data={"hints": hints}, warnings=warnings
        )

    # -- generate_investigation_summary -------------------------------------

    def generate_investigation_summary(
        self, include_hints: bool = True, max_hints: int = 3
    ) -> AnalysisResult:
        """Produce a consolidated overview of the investigation so far.

        Combines `analyze_evidence`, `analyze_clues`,
        `compare_suspects`, `detect_inconsistencies`,
        `calculate_suspicion`, and (optionally) `generate_hints` into
        a single structured payload, plus a short narrative paragraph
        produced via `self.ai_provider`.

        Args:
            include_hints: Whether to include a `hints` section.
            max_hints: Passed through to `generate_hints` when
                `include_hints` is True.

        Returns:
            `AnalysisResult` with `data` containing:
                - `case`: the case info this analyzer was given
                  (never includes `correct_suspect`)
                - `progress`: counts of discovered evidence/clues and
                  how many suspects have recorded statements
                - `evidence_analysis`, `clue_analysis`,
                  `suspect_comparison`, `inconsistencies`,
                  `suspicion_scores`: the full sub-results, as dicts
                - `hints`: present only if `include_hints` is True
                - `narrative`: a short prose overview
        """
        warnings: List[str] = []

        evidence_result = self.analyze_evidence()
        clue_result = self.analyze_clues()
        comparison_result = self.compare_suspects()
        inconsistency_result = self.detect_inconsistencies()
        suspicion_result = self.calculate_suspicion()

        for sub_result in (
            evidence_result,
            clue_result,
            comparison_result,
            inconsistency_result,
            suspicion_result,
        ):
            warnings.extend(sub_result.warnings)

        examined_actions = [
            entry
            for entry in self.investigation_history
            if entry.get("action") == "examine_suspect"
        ]
        suspects_with_statements = sum(
            1 for s in self.suspects if len(self._statements_for(s)) > 0
        )

        progress = {
            "evidence_discovered": evidence_result.data.get("discovered_count", 0),
            "evidence_total": evidence_result.data.get("total_evidence", 0),
            "clues_discovered": clue_result.data.get("discovered_count", 0),
            "clues_total": clue_result.data.get("total_clues", 0),
            "suspects_total": len(self.suspects),
            "suspects_examined": len(examined_actions),
            "suspects_with_statements": suspects_with_statements,
            "actions_logged": len(self.investigation_history),
        }

        data: Dict[str, Any] = {
            "case": dict(self.case_info),
            "progress": progress,
            "evidence_analysis": evidence_result.to_dict(),
            "clue_analysis": clue_result.to_dict(),
            "suspect_comparison": comparison_result.to_dict(),
            "inconsistencies": inconsistency_result.to_dict(),
            "suspicion_scores": suspicion_result.to_dict(),
        }

        if include_hints:
            hints_result = self.generate_hints(max_hints=max_hints)
            warnings.extend(hints_result.warnings)
            data["hints"] = hints_result.data.get("hints", [])

        narrative_context = {
            "template": (
                "So far {evidence_discovered}/{evidence_total} evidence "
                "item(s) and {clues_discovered}/{clues_total} clue(s) have "
                "been discovered, across {suspects_total} suspect(s)."
            ),
            **progress,
        }
        try:
            narrative = self.ai_provider.generate_text(
                prompt=narrative_context["template"].format(**progress),
                context=narrative_context,
            )
        except Exception:  # pragma: no cover - defensive fallback
            narrative = narrative_context["template"].format(**progress)
        data["narrative"] = narrative

        title = self.case_info.get("title") or self.case_info.get("case_id") or "the case"
        summary = f"Investigation summary generated for {title}."
        return AnalysisResult(success=True, summary=summary, data=data, warnings=warnings)

    def __repr__(self) -> str:
        return (
            f"AIAnalyzer(suspects={len(self.suspects)}, "
            f"evidence={len(self.evidence)}, clues={len(self.clues)})"
        )
