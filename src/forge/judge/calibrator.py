"""Question-level calibration for typed judgements — built ON the engine Forge already has.

Forge already fits honest probabilities in forge.research.calibration.CalibrationEngine:
PAV isotonic regression, source-weighted (live 3.0 / paper 2.0 / shadow 1.5 / counterfactual 1.0),
with a skeptical prior and a "no evidence => halve the claimed edge" fallback, over 4,072 realized
points. We do NOT rebuild that. We route every judge `noul` through it under a per-question class
key so each question type accumulates its own realized calibration.

WHY THIS MATTERS (measured tonight): a raw LLM probability is not a probability. Qwen returned
noul=0.0062 / confidence=0.00027 for a plainly risky token — plausible-looking noise. Jev is
purpose-trained (RLCD) to be calibrated; a general model is not. So we never trust `raw`: we fit
`calibrated` from OUR OWN realized outcomes and act on that. This is the single biggest way Forge
can beat the reference desk — they rent calibration from a vendor forever; we manufacture it and
it compounds with every settled judgement.
"""
from __future__ import annotations

from typing import Any

from forge.research.calibration import CalibrationEngine

# Class-key namespace so judge questions never collide with strategy families in calibration_points.
_PREFIX = "judge:"


def question_class(question_set: str, question_name: str) -> str:
    """Stable calibration class for one question in one set, e.g. judge:event.gap_is_tradeable."""
    return f"{_PREFIX}{question_set}.{question_name}"


class JudgeCalibrator:
    """Thin, honest wrapper: record a judgement's outcome, and calibrate a raw noul on demand."""

    def __init__(self, engine: CalibrationEngine | None = None, db: Any = None) -> None:
        if engine is None and db is None:
            raise ValueError("JudgeCalibrator needs either an engine or a db")
        self.engine = engine or CalibrationEngine(db)

    # ---- write path: score a judgement when its outcome becomes known ----
    def record(self, question_set: str, question_name: str, predicted: float, outcome: bool,
               *, source: str = "paper", ref_id: str | None = None, regime: str | None = None) -> None:
        """Record one realized outcome for a noul. `source` weights it (live>paper>shadow>counterfactual)."""
        cls = question_class(question_set, question_name)
        # CalibrationEngine.record signature: (cls, predicted, outcome, source, strategy_id, regime)
        self.engine.record(cls, float(predicted), bool(outcome), source, ref_id, regime)

    # ---- read path: turn a raw model claim into an honest probability ----
    def calibrate(self, question_set: str, question_name: str, raw: float) -> dict[str, Any]:
        """Return {p, n, provisional, source}. p is the value thresholds must act on.

        With no realized evidence the engine already halves the claimed edge toward 0.5 (its
        skeptical prior); we surface n so callers can additionally cut ticket size on thin evidence
        rather than sizing a provisional judgement like a proven one.
        """
        cls = question_class(question_set, question_name)
        p, n = self.engine.calibrate(cls, float(raw))
        return {
            "p": float(p),
            "n": int(n),
            "provisional": int(n) < 30,
            "source": "fitted" if int(n) >= 30 else ("thin" if int(n) > 0 else "skeptical_prior"),
            "raw": float(raw),
        }

    # ---- introspection for Luca / Mira / the morning report ----
    def report(self, question_set: str | None = None) -> list[dict[str, Any]]:
        """Per-question calibration health, using the engine's own reliability() (Brier + bin table).

        Honest by construction: raw Brier is the model's claim scored against reality; the fitted map
        is what we act on. `improvement` is the value calibration adds — if it is not positive with
        enough n, the question is not worth asking and Mira should retire it.
        """
        db = self.engine.db
        like = f"{_PREFIX}{question_set}.%" if question_set else f"{_PREFIX}%"
        rows = db.query(
            "SELECT family, COUNT(*) n, AVG(CAST(predicted AS REAL)) avg_raw, "
            "AVG(CAST(outcome AS REAL)) base_rate FROM calibration_points "
            "WHERE family LIKE ? GROUP BY family ORDER BY n DESC LIMIT 60", (like,)) or []
        out = []
        for r in rows:
            fam = str(r["family"])
            rel = self.engine.reliability(fam)
            n = int(rel.get("n") or r["n"] or 0)
            brier_raw = float(rel.get("brier") or 0.0)
            # calibrated Brier: score every realized point through the fitted map (honest, not a proxy)
            pts = db.query("SELECT predicted, outcome FROM calibration_points WHERE family=?", (fam,)) or []
            if pts:
                import numpy as _np
                cal = _np.array([self.engine.calibrate(fam, float(x["predicted"]))[0] for x in pts])
                obs = _np.array([float(x["outcome"]) for x in pts])
                brier_cal = float(_np.mean((cal - obs) ** 2))
            else:
                brier_cal = brier_raw
            out.append({
                "question": fam.replace(_PREFIX, "", 1), "n": n,
                "base_rate": round(float(r["base_rate"] or 0.0), 4),
                "avg_raw": round(float(r["avg_raw"] or 0.0), 4),
                "brier_raw": round(brier_raw, 5), "brier_calibrated": round(brier_cal, 5),
                "improvement": round(brier_raw - brier_cal, 5),
                "provisional": n < 30, "hit_rate": rel.get("hit_rate"),
            })
        return out
