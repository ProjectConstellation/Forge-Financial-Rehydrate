"""Typed judgement primitives — the three seats every Forge judgement sits in.

Design lineage (improved, not copied): a trading desk's judgements should be typed numbers a
threshold can act on, not prose a parser has to interpret. Three primitives cover every decision:

    Noul   "is this true"            -> calibrated probability 0..1        (an `if`)
    Choice "which one of these"      -> label + probabilities + confidence (a `switch`)
    Score  "rate on my rubric"       -> ordinal level + legend + confidence (a `sort`)

FORGE-SPECIFIC IMPROVEMENTS over the reference desk:
  * **Calibration we own.** A raw LLM probability is not a probability — measured tonight, Qwen
    returned noul=0.0062 and confidence=0.00027 for a plainly risky token, i.e. plausible-looking
    noise. Every `noul` therefore carries BOTH the model's raw claim and a `calibrated` value
    fitted by forge.research.calibration.CalibrationEngine on realized outcomes (PAV isotonic,
    source-weighted, skeptical prior). Thresholds act on `calibrated`; `raw` is kept for audit and
    for measuring how far the model drifts.
  * **Evidence count is returned, not hidden.** A judgement on n=3 is not a judgement on n=4,000.
    Every answer reports `n` and `provisional` so callers can refuse to size on thin evidence.
  * **Null discipline is enforced by the schema, not by hope.** `reads` declares exactly which
    state fields a question may see, so the state sent to the model is pruned (a fat state costs
    accuracy) and a field the question did not declare cannot silently influence it. Missing data
    is a first-class answer: `unknown` is always available and must carry its own consequence
    downstream (cut the ticket — never treat null as fine, never invent a number).
  * **Absolute vs relative kept distinct.** A Choice settles *which*; it cannot say whether today
    is a day at all. Any pick-style set must ship a `worth_*` Noul beside it, and `absolute_gate`
    marks which question that is, so the funnel can refuse to act on a relative winner alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# A judgement with fewer than this many realized outcomes behind its calibration is provisional.
PROVISIONAL_BELOW_N = 30


@dataclass(frozen=True)
class Noul:
    """Is this true? Returns a probability in 0..1."""

    instructions: str
    reads: tuple[str, ...] = ()                 # state fields this question may see
    criteria: dict[str, str] = field(default_factory=dict)   # optional {"true": ..., "false": ...}
    unknown_ok: bool = True                     # allow an explicit "insufficient data" answer

    kind = "noul"

    def schema(self) -> dict[str, Any]:
        props: dict[str, Any] = {"raw": {"type": "number", "minimum": 0, "maximum": 1}}
        if self.unknown_ok:
            props["insufficient_data"] = {"type": "boolean"}
        return {"type": "object", "additionalProperties": False,
                "properties": props, "required": ["raw"]}


@dataclass(frozen=True)
class Choice:
    """Which one? Returns a label plus the probability of every option."""

    instructions: str
    criteria: dict[str, str] = field(default_factory=dict)
    reads: tuple[str, ...] = ()
    max_options: int = 255                      # hard ceiling on a single choice question

    kind = "choice"

    def schema(self) -> dict[str, Any]:
        return {"type": "object", "additionalProperties": False,
                "properties": {"choice": {"type": "string"},
                               "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
                "required": ["choice", "confidence"]}

    def resolve_options(self, state: dict[str, Any]) -> dict[str, str]:
        """Options may be static (criteria) or built from state at call time (a pick over candidates)."""
        if self.criteria:
            return dict(self.criteria)
        cands = state.get("candidates") or []
        out: dict[str, str] = {}
        for c in cands[: self.max_options]:
            key = str(c.get("key") or c.get("ticker") or c.get("id") or "")
            if key:
                out[key] = str(c.get("summary") or "")[:400]
        return out


@dataclass(frozen=True)
class Score:
    """Rate on my rubric. Returns an ordinal level and the legend it landed on."""

    instructions: str
    levels: tuple[str, ...] = ()
    reads: tuple[str, ...] = ()

    kind = "score"

    def schema(self) -> dict[str, Any]:
        return {"type": "object", "additionalProperties": False,
                "properties": {"score": {"type": "number", "minimum": 0,
                                         "maximum": max(0, len(self.levels) - 1)},
                               "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
                "required": ["score", "confidence"]}

    @property
    def max_level(self) -> int:
        return max(0, len(self.levels) - 1)


Question = Noul | Choice | Score
QuestionSet = dict[str, Question]


def reads_of(qs: QuestionSet) -> set[str]:
    """Every state field this set actually reads. Used to prune state before the call."""
    out: set[str] = set()
    for q in qs.values():
        out |= set(q.reads)
        if isinstance(q, Choice) and not q.criteria:
            out.add("candidates")        # pick-style sets read the candidate list
    return out


def prune_state(state: dict[str, Any], qs: QuestionSet) -> dict[str, Any]:
    """Send only what the questions read. A fat state costs accuracy and costs tokens."""
    need = reads_of(qs)
    if not need:
        return dict(state)
    return {k: v for k, v in state.items() if k in need}


def json_schema_for(qs: QuestionSet, resolved_choices: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    """Build one strict object schema covering the whole set, so ONE call answers every question.

    Splitting a set into one call per question re-charges the identical state each time and
    multiplies the bill for identical answers. This is why sets exist.
    """
    props: dict[str, Any] = {}
    for name, q in qs.items():
        sch = q.schema()
        if isinstance(q, Choice):
            opts = (resolved_choices or {}).get(name) or q.criteria
            if opts:
                sch["properties"]["choice"] = {"type": "string", "enum": sorted(opts.keys())}
                # Probabilities over every option, so a near-tie is visible instead of hidden.
                sch["properties"]["probabilities"] = {
                    "type": "object", "additionalProperties": False,
                    "properties": {k: {"type": "number", "minimum": 0, "maximum": 1} for k in sorted(opts)},
                    "required": sorted(opts),
                }
                sch["required"] = ["choice", "confidence", "probabilities"]
        if isinstance(q, Score) and q.levels:
            sch["properties"]["legend"] = {"type": "string", "enum": list(q.levels)}
            sch["required"] = ["score", "confidence", "legend"]
        props[name] = sch
    return {"type": "object", "additionalProperties": False, "properties": props,
            "required": sorted(props.keys())}


def absolute_gate(qs: QuestionSet) -> str | None:
    """The Noul that decides whether to act at all, when the set is a pick over options.

    A choice is relative: it settles *which* of these, and always returns a winner even when every
    option is bad. The absolute gate is what says "none of them, stand down today". A pick set
    without one is a set that can never say no.
    """
    has_choice = any(isinstance(q, Choice) for q in qs.values())
    if not has_choice:
        return None
    for name, q in qs.items():
        if isinstance(q, Noul) and (name.startswith("worth_") or name.startswith("act_")
                                    or name.startswith("any_")):
            return name
    return None


def validate(qs: QuestionSet, answers: dict[str, Any],
             resolved_choices: dict[str, dict[str, str]] | None = None) -> tuple[dict[str, Any], list[str]]:
    """Validate and normalise a raw model reply. Returns (clean_answers, problems).

    Never invents a value. Anything malformed is dropped and reported, so a null stays a null and
    the caller sees exactly which question failed rather than acting on a fabricated number.
    """
    clean: dict[str, Any] = {}
    problems: list[str] = []
    for name, q in qs.items():
        a = (answers or {}).get(name)
        if a is None:
            problems.append(f"{name}: absent")
            continue
        if not isinstance(a, dict):
            problems.append(f"{name}: not an object")
            continue
        try:
            if q.kind == "noul":
                raw = a.get("raw", a.get("noul"))
                if raw is None:
                    problems.append(f"{name}: no probability")
                    continue
                v = float(raw)
                if not 0.0 <= v <= 1.0:
                    problems.append(f"{name}: probability {v} out of range")
                    continue
                clean[name] = {"kind": "noul", "raw": v,
                               "insufficient_data": bool(a.get("insufficient_data", False))}
            elif q.kind == "choice":
                lab = a.get("choice")
                opts = (resolved_choices or {}).get(name) or q.criteria
                if lab is None:
                    problems.append(f"{name}: no choice")
                    continue
                if opts and lab not in opts:
                    problems.append(f"{name}: choice {lab!r} not among declared options")
                    continue
                probs = a.get("probabilities") or {}
                bad = [k for k, pv in probs.items() if not isinstance(pv, (int, float))]
                if bad:
                    problems.append(f"{name}: non-numeric probabilities {bad[:3]}")
                clean[name] = {"kind": "choice", "choice": str(lab),
                               "confidence": float(a.get("confidence", 0.0)),
                               "probabilities": {k: float(v) for k, v in probs.items()
                                                 if isinstance(v, (int, float))}}
            elif q.kind == "score":
                sc = a.get("score")
                if sc is None:
                    problems.append(f"{name}: no score")
                    continue
                sc = float(sc)
                if not 0 <= sc <= q.max_level:
                    problems.append(f"{name}: score {sc} outside 0..{q.max_level}")
                    continue
                legend = a.get("legend")
                if q.levels:
                    if legend not in q.levels:
                        legend = q.levels[int(round(sc))] if 0 <= round(sc) <= q.max_level else None
                clean[name] = {"kind": "score", "score": sc, "legend": legend,
                               "confidence": float(a.get("confidence", 0.0)),
                               "normalized": (sc / q.max_level) if q.max_level else None}
        except (TypeError, ValueError) as e:
            problems.append(f"{name}: malformed ({e})")
    return clean, problems


def annotate_calibration(clean: dict[str, Any], calibrated: dict[str, dict[str, Any]]) -> None:
    """Attach calibrated probability + evidence count to every noul, in place.

    Thresholds must act on `calibrated`, never on `raw`. `provisional` marks an answer whose
    calibration rests on too little realized evidence to be trusted for sizing.
    """
    for name, a in clean.items():
        if a.get("kind") != "noul":
            continue
        c = calibrated.get(name) or {}
        a["calibrated"] = float(c.get("p", a["raw"]))
        a["n_evidence"] = int(c.get("n", 0))
        a["provisional"] = int(c.get("n", 0)) < PROVISIONAL_BELOW_N
        a["calibration_source"] = c.get("source", "skeptical_prior")
