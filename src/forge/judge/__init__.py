"""forge.judge — Forge-Jev: typed judgements, a cost-ordered funnel, calibration we own, and an
inference economy where every seat must recoup its salary.

Public surface:
    Candidate, Funnel, FunnelResult          the cost-ordered ladder (free arithmetic -> judgement)
    Noul, Choice, Score                      the three typed seats
    Judge                                    the two-phase ask/commit protocol (zero extra inference)
    JudgeCalibrator                          honest noul calibration built on CalibrationEngine
    SETS, resolve                            every question the desk can ask, in one file
    InferenceEconomy                         "inference is a salary; recoup it or lose the wake budget"
    ensure_schema                            idempotent DDL for the judge tables
"""
from forge.judge.primitives import (Noul, Choice, Score, Question, QuestionSet, prune_state,
                                    reads_of, json_schema_for, absolute_gate, validate,
                                    annotate_calibration, PROVISIONAL_BELOW_N)
from forge.judge.questions import SETS, resolve
from forge.judge.calibrator import JudgeCalibrator, question_class
from forge.judge.funnel import Candidate, Funnel, FunnelResult
from forge.judge.checks import default_funnel, R0, R1, R2
from forge.judge.judge import Judge
from forge.judge.salary import InferenceEconomy
from forge.judge.doctrine import doctrine, DOCTRINE, PREAMBLE
from forge.judge.event_verdict import verdict as event_verdict, event_rail_tradeable
from forge.judge.schema import ensure_schema

__all__ = [
    "Noul", "Choice", "Score", "Question", "QuestionSet", "prune_state", "reads_of",
    "json_schema_for", "absolute_gate", "validate", "annotate_calibration", "PROVISIONAL_BELOW_N",
    "SETS", "resolve", "JudgeCalibrator", "question_class",
    "Candidate", "Funnel", "FunnelResult", "default_funnel", "R0", "R1", "R2",
    "Judge", "InferenceEconomy", "ensure_schema",
    "doctrine", "DOCTRINE", "PREAMBLE", "event_verdict", "event_rail_tradeable",
]
