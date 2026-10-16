"""The judgement seat — a two-phase protocol that makes the OFFICER the judge, with zero extra inference.

WHY NOT A BACKEND MODEL PUMP. The reference desk runs a separate judge service that calls a model per
candidate. On Forge that would be both (a) a Token Plan terms violation — "custom application backends /
non-interactive batch calls" are explicitly prohibited, and risking the key risks the whole firm — and
(b) wasteful, since an officer's interactive Qwen call is already happening and already paid for.

THE PROTOCOL (pure deterministic code on both ends; the only model work is inside the officer's own run):
    1. officer calls  forge_judge_ask(question_set, state)
         -> tool returns {schema, pruned_state, questions_in_plain_english, worth_gate}
         The state is pruned to exactly the fields the questions declared they read. A fat state costs
         accuracy and tokens; pruning is enforced from the question declarations, not left to discipline.
    2. officer reasons over it IN ITS EXISTING CALL and produces typed answers
    3. officer calls  forge_judge_commit(question_set, answers)
         -> tool validates (never invents a number; malformed is dropped and reported), calibrates every
            noul through the existing CalibrationEngine on realized outcomes, applies the absolute gate,
            records the judgement for compounding calibration, and returns a verdict the funnel can act on.

WHAT MAKES THIS BEAT THE REFERENCE DESK: they rent calibration from a vendor; we manufacture it. Every
committed judgement is scored when its outcome settles, so the same question gets more honest over time.
A judgement on n=3 is marked provisional and cuts ticket size; it is never sized like one on n=4,000.
"""
from __future__ import annotations

import time
from typing import Any

from forge.judge import primitives as P
from forge.judge.calibrator import JudgeCalibrator, question_class
from forge.judge.questions import resolve
from forge.judge.thresholds import JUDGE


class Judge:
    """Stateless-ish judgement seat. Holds a calibrator; makes NO model call of its own."""

    def __init__(self, db: Any, calibrator: JudgeCalibrator | None = None) -> None:
        self.db = db
        self.cal = calibrator or JudgeCalibrator(db=db)

    # ------------------------------------------------------------------ phase 1: ask
    def ask(self, question_set: str, state: dict[str, Any]) -> dict[str, Any]:
        qs = resolve(question_set, state)
        resolved_choices: dict[str, dict[str, str]] = {}
        for name, q in qs.items():
            if isinstance(q, P.Choice):
                resolved_choices[name] = q.resolve_options(state)
        pruned = P.prune_state(state, qs)
        schema = P.json_schema_for(qs, resolved_choices)
        worth = P.absolute_gate(qs)
        return {
            "question_set": question_set,
            "schema": schema,
            "state": pruned,                      # only the declared fields — never the fat object
            "worth_gate": worth,                  # the absolute "act at all" question, if any
            "explain": {name: _plain(q) for name, q in qs.items()},
            "rules": [
                "Answer with typed values only; do not narrate.",
                "Never invent a number. If a field is missing, use insufficient_data / the 'dark' or "
                "'unknown' option — missing is an answer with its own consequence, never a pass.",
                "A Choice settles WHICH; it always returns a winner. The worth-gate Noul is what says "
                "'none of these today'. Answer both.",
                "Your probabilities are raw claims; the desk calibrates them against realized outcomes. "
                "Answer honestly, not confidently.",
            ],
            "n_questions": len(qs),
        }

    # ------------------------------------------------------------------ phase 2: commit
    def commit(self, question_set: str, answers: dict[str, Any], *, state: dict[str, Any] | None = None,
               role: str = "", candidate_id: str = "", source: str = "paper",
               regime: str | None = None) -> dict[str, Any]:
        state = state or {}
        qs = resolve(question_set, state)
        resolved_choices = {n: q.resolve_options(state) for n, q in qs.items() if isinstance(q, P.Choice)}
        clean, problems = P.validate(qs, answers, resolved_choices)

        # Calibrate every noul against realized outcomes; thresholds act on `calibrated`, never `raw`.
        cal_map: dict[str, dict[str, Any]] = {}
        for name, a in clean.items():
            if a.get("kind") == "noul":
                cal_map[name] = self.cal.calibrate(question_set, name, a["raw"])
        P.annotate_calibration(clean, cal_map)

        verdict = self._decide(qs, clean)
        rec = {
            "ts": time.time(), "question_set": question_set, "role": role, "candidate_id": candidate_id,
            "source": source, "regime": regime, "verdict": verdict["action"],
            "worth_gate": verdict.get("worth_gate"), "size_factor": verdict["size_factor"],
            "problems": problems, "answers": clean,
        }
        self._record(rec)
        return {**verdict, "answers": clean, "problems": problems, "recorded": True}

    # ------------------------------------------------------------------ decision policy
    def _decide(self, qs: dict[str, P.Question], clean: dict[str, Any]) -> dict[str, Any]:
        """Turn validated+calibrated answers into an action and a SIZE factor. Never re-ranks a Choice
        winner — if you disagree with the pick you disagree with a threshold, and thresholds live in
        thresholds.py. Standing down is a first-class result."""
        size = 1.0

        # Absolute gate first: is today a day at all?
        worth = P.absolute_gate(qs)
        if worth and worth in clean:
            cw = clean[worth]
            p = cw.get("calibrated", cw.get("raw", 0.0))
            if cw.get("insufficient_data") or cw.get("provisional"):
                # Not a hard no — but thin/absent evidence must not be sized like proof.
                size *= JUDGE["insufficient_data_size_factor"]
            if p < JUDGE["pick_min_worth"]:
                return {"action": "STAND_DOWN", "reason": f"{worth} calibrated {p:.3f} < "
                        f"{JUDGE['pick_min_worth']} (nothing worth doing today)",
                        "worth_gate": {"name": worth, "p": round(p, 4)}, "size_factor": 0.0}

        # A Choice's confidence must clear the floor, else no favourite.
        for name, a in clean.items():
            if a.get("kind") == "choice" and a.get("confidence", 0) < JUDGE["choice_min_confidence"]:
                # Only the pick's `best` gates the action; descriptive choices (shape, coverage) size.
                if name in ("best",):
                    return {"action": "STAND_DOWN",
                            "reason": f"pick confidence {a['confidence']:.3f} < {JUDGE['choice_min_confidence']} "
                                      f"(flat over options = no favourite)",
                            "worth_gate": None, "size_factor": 0.0}

        # Any hard-risk Noul that fires true => reject (these are the "is this a trap" questions).
        for name, a in clean.items():
            if a.get("kind") != "noul":
                continue
            p = a.get("calibrated", a.get("raw", 0.0))
            if name in ("leg_failure_risk", "concentration_is_exit_risk", "momentum_already_spent") and p > 0.55:
                return {"action": "REJECT", "reason": f"{name} calibrated {p:.3f} > 0.55",
                        "worth_gate": None, "size_factor": 0.0}
            # Positive-edge gates must clear a floor or there is no trade.
            if name in ("gap_exceeds_all_costs", "edge_survives_costs", "gap_is_real_after_costs",
                        "is_structural_identity", "same_question_both_venues", "model_beats_market",
                        "information_not_already_priced", "settlement_basis_matches") and p < 0.60:
                return {"action": "REJECT", "reason": f"{name} calibrated {p:.3f} < 0.60",
                        "worth_gate": None, "size_factor": 0.0}

        # Data coverage sizes the ticket; it never skips. dark => cut hard, partial => cut gently.
        for name, a in clean.items():
            if a.get("kind") == "choice" and name == "data_coverage":
                ch = a.get("choice")
                if ch == "dark":
                    size *= JUDGE["insufficient_data_size_factor"]
                elif ch == "partial":
                    size *= JUDGE["no_social_size_factor"]

        # Provisional calibration on any load-bearing noul => cut the ticket.
        if any(a.get("kind") == "noul" and a.get("provisional") for a in clean.values()):
            size *= JUDGE["noul_provisional_size_factor"]

        chosen = None
        for name, a in clean.items():
            if a.get("kind") == "choice" and name == "best":
                chosen = a.get("choice")
        return {"action": "ACT" if size > 0 else "STAND_DOWN", "reason": "all gates cleared",
                "worth_gate": None, "size_factor": round(size, 3), "chosen": chosen}

    # ------------------------------------------------------------------ persistence
    def _record(self, rec: dict[str, Any]) -> None:
        import json as _json
        try:
            self.db.insert("judge_verdicts", {
                "ts": rec["ts"], "question_set": rec["question_set"], "role": rec["role"],
                "candidate_id": rec["candidate_id"], "source": rec["source"], "regime": rec["regime"],
                "verdict": rec["verdict"], "size_factor": rec["size_factor"],
                "answers": _json.dumps(rec["answers"], default=str)[:8000],
                "problems": _json.dumps(rec["problems"], default=str)[:1000],
            })
        except Exception:
            pass
        # Seed calibration for every noul so outcomes can later score it. Outcome starts unknown;
        # score_verdict() fills it when reality resolves.
        for name, a in (rec["answers"] or {}).items():
            if a.get("kind") == "noul":
                try:
                    self.db.insert("judge_noul_pending", {
                        "ts": rec["ts"], "question_set": rec["question_set"], "question": name,
                        "candidate_id": rec["candidate_id"], "role": rec["role"], "source": rec["source"],
                        "raw": a.get("raw"), "calibrated": a.get("calibrated"), "outcome": None,
                    })
                except Exception:
                    pass

    def score_verdict(self, question_set: str, question: str, candidate_id: str, outcome: bool,
                      *, source: str = "paper", regime: str | None = None) -> bool:
        """When reality resolves a pending noul, score it so the calibrator learns. Idempotent."""
        try:
            row = self.db.query_one(
                "SELECT raw, calibrated FROM judge_noul_pending WHERE question_set=? AND question=? "
                "AND candidate_id=? AND outcome IS NULL ORDER BY id DESC LIMIT 1",
                (question_set, question, candidate_id))
            if not row:
                return False
            predicted = float(row.get("calibrated") or row.get("raw") or 0.5)
            self.cal.record(question_set, question, predicted, bool(outcome), source=source,
                            ref_id=candidate_id, regime=regime)
            self.db.execute("UPDATE judge_noul_pending SET outcome=? WHERE question_set=? AND question=? "
                            "AND candidate_id=? AND outcome IS NULL",
                            (int(bool(outcome)), question_set, question, candidate_id))
            return True
        except Exception:
            return False


def _plain(q: P.Question) -> str:
    """One plain-English line per question, so the officer (and Luca, reading a report) sees intent."""
    head = q.instructions.strip().split(".")[0]
    if isinstance(q, P.Choice):
        return f"[which] {head}. options: {', '.join(sorted((q.criteria or {}).keys())) or 'from state.candidates'}"
    if isinstance(q, P.Score):
        return f"[rate 0..{q.max_level}] {head}"
    return f"[true/false 0..1] {head}"
