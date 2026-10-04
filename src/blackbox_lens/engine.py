"""Planning, immutable run directories and offline recomputation."""
from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from .adapters import Adapter, ERRORS, Reply
from .suite import (Case, MAX_RAW_CHARS, MAX_REQUESTS, Suite, SuiteError, Variant,
                    canonical_bytes, decode_json, integer, keys, read_json)


@dataclass(frozen=True)
class Trial:
    id: str
    case: Case
    variant: Variant
    repeat: int


def create_plan(suite: Suite, *, repeats: int = 3, seed: int = 42) -> list[Trial]:
    suite = Suite.from_dict(suite.to_dict())  # Validate even manually constructed SDK objects.
    integer(repeats, 1, 100, "repeats")
    integer(seed, 0, 2**32 - 1, "seed")
    count = sum(len(c.variants) for c in suite.cases) * repeats
    if count > MAX_REQUESTS:
        raise SuiteError(f"plan exceeds the hard limit of {MAX_REQUESTS} requests")
    plan = [Trial(f"{c.id}/{v.id}/{r}", c, v, r)
            for c in suite.cases for v in c.variants for r in range(1, repeats + 1)]
    # SHA-256 sorting is a portable seeded permutation, independent of Python's random version.
    plan.sort(key=lambda t: (hashlib.sha256(f"{seed}:{t.id}".encode()).digest(), t.id))
    return plan


def _write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")


def _new_directory(out: str | Path) -> Path:
    path = Path(out)
    try:
        path.mkdir(parents=True, exist_ok=False)
    except OSError:
        raise SuiteError("output must be a new, writable directory; existing paths are never overwritten") from None
    return path


def run_suite(suite: Suite, adapter: Adapter, out: str | Path, *, repeats: int = 3,
              seed: int = 42, max_requests: int = 100) -> dict:
    plan = create_plan(suite, repeats=repeats, seed=seed)
    suite = Suite.from_dict(suite.to_dict())
    integer(max_requests, 1, MAX_REQUESTS, "max_requests")
    if len(plan) > max_requests:
        raise SuiteError("plan exceeds max_requests; inspect plan and explicitly raise the cap")
    try:
        metadata = adapter.metadata
        if not isinstance(metadata, dict) or len(canonical_bytes(metadata)) > 4096:
            raise SuiteError("adapter metadata must be a bounded JSON object")
        # Copy the metadata, so a custom adapter cannot mutate persisted provenance mid-run.
        metadata = decode_json(canonical_bytes(metadata))
    except (ValueError, TypeError, RecursionError):
        raise SuiteError("adapter metadata must be a bounded JSON object") from None
    manifest = {"schema_version": 1, "package_version": "0.1.0", "python_version": platform.python_version(),
                "created_at": datetime.now(timezone.utc).isoformat(), "suite": suite.to_dict(),
                "suite_sha256": suite.sha256, "repeats": repeats, "seed": seed,
                "order": [t.id for t in plan], "adapter": metadata}
    if hasattr(adapter, "contains_secret") and adapter.contains_secret(canonical_bytes(manifest)):
        raise SuiteError("configured credential occurs in suite or metadata; run refused")
    directory = _new_directory(out)
    _write_json(directory / "manifest.json", manifest)
    interrupted = False
    with (directory / "observations.jsonl").open("x", encoding="utf-8", newline="\n") as stream:
        try:
            for trial in plan:
                started = time.perf_counter()
                try:
                    reply = adapter.respond(trial)
                    if not isinstance(reply, Reply):
                        reply = Reply(error="adapter_error")
                    elif reply.error is not None:
                        reply = Reply(error=reply.error if reply.error in ERRORS else "adapter_error")
                    elif not isinstance(reply.raw, str):
                        reply = Reply(error="malformed_response")
                    elif len(reply.raw) > MAX_RAW_CHARS:
                        reply = Reply(error="response_too_large")
                    else:
                        reply.raw.encode("utf-8")
                except Exception:
                    reply = Reply(error="adapter_error")
                observation = {"trial_id": trial.id, "raw": reply.raw, "error": reply.error,
                               "duration_ms": round((time.perf_counter() - started) * 1000, 3)}
                if hasattr(adapter, "contains_secret") and adapter.contains_secret(canonical_bytes(observation)):
                    observation["raw"], observation["error"] = None, "secret_redacted"
                stream.write(canonical_bytes(observation).decode("utf-8") + "\n")
                stream.flush()  # A killed run remains reanalyzable with explicit missing slots.
        except KeyboardInterrupt:
            interrupted = True
    report = analyze_run(directory)
    _save_reports(directory, report)
    if interrupted:
        raise KeyboardInterrupt
    return report


def _load_manifest(directory: Path) -> tuple[dict, Suite, list[Trial]]:
    manifest = read_json(directory / "manifest.json", 4_194_304)
    keys(manifest, {"schema_version", "package_version", "python_version", "created_at", "suite",
                    "suite_sha256", "repeats", "seed", "order", "adapter"}, "manifest")
    integer(manifest["schema_version"], 1, 1, "artifact schema_version")
    for field in ("package_version", "python_version", "created_at"):
        if not isinstance(manifest[field], str) or not 1 <= len(manifest[field]) <= 100:
            raise SuiteError("invalid manifest metadata")
    if not isinstance(manifest["adapter"], dict) or len(canonical_bytes(manifest["adapter"])) > 4096:
        raise SuiteError("invalid adapter metadata")
    suite = Suite.from_dict(manifest["suite"])
    if manifest["suite_sha256"] != suite.sha256:
        raise SuiteError("suite digest mismatch")
    plan = create_plan(suite, repeats=manifest["repeats"], seed=manifest["seed"])
    if manifest["order"] != [t.id for t in plan]:
        raise SuiteError("manifest trial order/count does not match the exact planned trials")
    return manifest, suite, plan


def _load_observations(directory: Path, planned: set[str]) -> dict[str, dict]:
    observations = {}
    total = 0
    try:
        with (directory / "observations.jsonl").open("rb") as stream:
            while True:
                line = stream.readline(32769)
                if not line:
                    break
                total += len(line)
                if len(line) > 32768 or total > 33_554_432:
                    raise SuiteError("observations exceed size limit")
                value = decode_json(line)
                keys(value, {"trial_id", "raw", "error", "duration_ms"}, "observation")
                tid = value["trial_id"]
                if not isinstance(tid, str) or tid not in planned or tid in observations:
                    raise SuiteError("duplicate or unplanned observation trial id")
                raw, error, duration = value["raw"], value["error"], value["duration_ms"]
                if error is not None:
                    if not isinstance(error, str) or error not in ERRORS or raw is not None:
                        raise SuiteError("invalid observation error")
                elif not isinstance(raw, str) or len(raw) > MAX_RAW_CHARS:
                    raise SuiteError("invalid raw response")
                if isinstance(raw, str):
                    try:
                        raw.encode("utf-8")
                    except UnicodeError:
                        raise SuiteError("invalid raw response Unicode") from None
                if type(duration) not in {int, float} or not math.isfinite(duration) or duration < 0:
                    raise SuiteError("invalid observation duration")
                observations[tid] = value
    except OSError:
        raise SuiteError("cannot read observations") from None
    return observations


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _counts(rows: list[dict]) -> dict:
    counts = Counter(r["status"] for r in rows)
    correct = sum(r["correct"] is True for r in rows)
    return {"planned": len(rows), "observed": len(rows) - counts["missing"], "valid": counts["valid"],
            "invalid": counts["invalid"], "errors": counts["error"], "missing": counts["missing"],
            "correct": correct, "strict_accuracy": _rate(correct, len(rows)),
            "valid_accuracy": _rate(correct, counts["valid"])}


PAIR_COUNT_FIELDS = ("planned_pairs", "observed_pairs", "valid_pairs", "same", "flips",
                     "correct_to_incorrect", "incorrect_to_correct", "both_correct", "both_incorrect")


def _pair_counts() -> dict:
    return dict.fromkeys(PAIR_COUNT_FIELDS, 0)


def _pair_rates(pair: dict) -> None:
    pair["excluded_pairs"] = pair["planned_pairs"] - pair["valid_pairs"]
    pair["coverage"] = _rate(pair["valid_pairs"], pair["planned_pairs"])
    pair["invariance"] = _rate(pair["same"], pair["valid_pairs"])
    pair["flip_rate"] = _rate(pair["flips"], pair["valid_pairs"])


def analyze_run(run_dir: str | Path, out: str | Path | None = None) -> dict:
    """Recompute from raw observations; cached reports are ignored. Missing slots remain missing."""
    directory = Path(run_dir)
    manifest, suite, plan = _load_manifest(directory)
    observations = _load_observations(directory, {t.id for t in plan})
    rows = []
    lookup = {}
    for order, trial in enumerate(plan, start=1):
        observation = observations.get(trial.id)
        raw = observation["raw"] if observation else None
        semantic = trial.variant.answer_map.get(raw.strip()) if raw is not None else None
        status = ("missing" if observation is None else "error" if observation["error"] is not None
                  else "valid" if semantic is not None else "invalid")
        row = {"trial_id": trial.id, "order": order, "case_id": trial.case.id,
               "variant_id": trial.variant.id, "kind": trial.variant.kind, "repeat": trial.repeat,
               "status": status, "raw": raw, "error": observation["error"] if observation else None,
               "duration_ms": observation["duration_ms"] if observation else None,
               "semantic_answer": semantic, "expected": trial.case.expected,
               "correct": semantic == trial.case.expected if status == "valid" else False}
        rows.append(row)
        lookup[(trial.case.id, trial.variant.id, trial.repeat)] = row
    counts = _counts(rows)
    by_kind = {kind: _counts([r for r in rows if r["kind"] == kind]) for kind in sorted({r["kind"] for r in rows})}
    comparisons: dict[str, dict] = {}
    case_contrasts: list[dict] = []
    repeated: dict[str, dict] = {}
    for case in suite.cases:
        for variant in case.variants:
            condition_rows = [lookup[(case.id, variant.id, r)] for r in range(1, manifest["repeats"] + 1)]
            repeat_summary = repeated.setdefault(variant.kind, {"conditions": 0, "eligible_conditions": 0,
                "conditions_with_disagreement": 0, "planned_repeat_pairs": 0, "valid_repeat_pairs": 0,
                "disagreeing_repeat_pairs": 0})
            repeat_summary["conditions"] += 1
            valid = [r for r in condition_rows if r["status"] == "valid"]
            repeat_summary["eligible_conditions"] += len(valid) >= 2
            repeat_summary["conditions_with_disagreement"] += len({r["semantic_answer"] for r in valid}) > 1
            repeat_summary["planned_repeat_pairs"] += len(condition_rows) * (len(condition_rows) - 1) // 2
            for left, right in combinations(valid, 2):
                repeat_summary["valid_repeat_pairs"] += 1
                repeat_summary["disagreeing_repeat_pairs"] += left["semantic_answer"] != right["semantic_answer"]
            if variant.kind == "baseline":
                continue
            pair = {"case_id": case.id, "variant_id": variant.id, "baseline_variant_id": case.baseline.id,
                    "kind": variant.kind, **_pair_counts()}
            for row in condition_rows:
                baseline = lookup[(case.id, case.baseline.id, row["repeat"])]
                pair["planned_pairs"] += 1
                pair["observed_pairs"] += row["status"] != "missing" and baseline["status"] != "missing"
                if row["status"] != "valid" or baseline["status"] != "valid":
                    continue
                pair["valid_pairs"] += 1
                pair["same"] += row["semantic_answer"] == baseline["semantic_answer"]
                pair["flips"] += row["semantic_answer"] != baseline["semantic_answer"]
                if baseline["correct"] and not row["correct"]:
                    pair["correct_to_incorrect"] += 1
                elif not baseline["correct"] and row["correct"]:
                    pair["incorrect_to_correct"] += 1
                elif baseline["correct"]:
                    pair["both_correct"] += 1
                else:
                    pair["both_incorrect"] += 1
            _pair_rates(pair)
            case_contrasts.append(pair)
            pooled = comparisons.setdefault(variant.kind, _pair_counts())
            for field in PAIR_COUNT_FIELDS:
                pooled[field] += pair[field]
    for pair in comparisons.values():
        _pair_rates(pair)
    for repeated_summary in repeated.values():
        repeated_summary["disagreement_rate"] = _rate(repeated_summary["disagreeing_repeat_pairs"],
                                                    repeated_summary["valid_repeat_pairs"])
    report = {"schema_version": 1, "complete": counts["missing"] == 0, "manifest": manifest,
              "counts": counts, "by_kind": by_kind, "comparisons": comparisons,
              "case_contrasts": case_contrasts, "repeat_consistency": repeated, "trials": rows}
    if out is not None:
        _save_reports(_new_directory(out), report)
    return report


def _save_reports(directory: Path, report: dict) -> None:
    from .report import render_html
    _write_json(directory / "report.json", report)
    with (directory / "report.html").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(render_html(report))
