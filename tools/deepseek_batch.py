"""Two-mode experiment runner. Standard library only; no retries or overwrite/resume."""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess

import blackbox_lens
from blackbox_lens import __version__, OpenAICompatible, SuiteError, analyze_run, load_suite
from blackbox_lens.engine import _make_manifest, _new_directory, _record_trial, _write_json
from blackbox_lens.suite import MAX_REQUESTS, canonical_bytes, integer, keys, read_json


def _source_provenance():
    package_root = Path(blackbox_lens.__file__).resolve().parent
    package_files = sorted([*package_root.glob("*.py"), *package_root.glob("data/*.json")])
    fingerprints = [{"path": path.relative_to(package_root).as_posix(),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in package_files]
    source = {"head": None, "dirty": None,
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "package_sha256": hashlib.sha256(canonical_bytes(fingerprints)).hexdigest()}
    try:
        repo = Path(__file__).resolve().parents[1]
        source["head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                                        text=True, check=True).stdout.strip()
        source["dirty"] = bool(subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                                               capture_output=True, text=True, check=True).stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return source


def _build_batch_plan(suite, adapters, *, repeats, seed, workers, max_requests):
    integer(workers, 1, 4, "workers")
    integer(max_requests, 1, 2 * MAX_REQUESTS, "max_requests")
    if set(adapters) != {"disabled", "enabled"}:
        raise SuiteError("batch requires exactly disabled and enabled adapters")
    manifests, plans = {}, {}
    for mode, adapter in adapters.items():
        manifests[mode], plans[mode] = _make_manifest(suite, adapter, repeats=repeats, seed=seed,
                                                    max_requests=MAX_REQUESTS)
        if manifests[mode]["adapter"].get("thinking") != mode:
            raise SuiteError("adapter thinking mode does not match batch mode")
    if sum(map(len, plans.values())) > max_requests:
        raise SuiteError("batch exceeds max_requests")
    # Each same-trial mode pair is adjacent; alternate which mode is admitted first.
    schedule = []
    for index, trial in enumerate(plans["disabled"]):
        modes = ["disabled", "enabled"]
        if index % 2:
            modes.reverse()
        base = len(schedule)
        schedule.extend({"sequence": base + offset + 1, "mode": mode, "trial_id": trial.id}
                        for offset, mode in enumerate(modes))
    plan = {"schema_version": 1, "package_version": __version__, "python_version": platform.python_version(),
                "source": _source_provenance(),
                "suite_sha256": suite.sha256, "repeats": repeats, "seed": seed, "workers": workers,
                "max_requests": max_requests, "planned_calls": len(schedule), "retries": 0, "resume_supported": False,
                "stop_rules": {"http_status": [401, 402, 403], "finish_reason": ["length"],
                               "response_too_large": True, "consecutive_errors": 3, "cumulative_errors": 10,
                               "ordering": "completed events in events.jsonl; invalid labels reset consecutive errors",
                               "in_flight": "Already submitted calls finish and are retained; no further admission."},
                "schedule_semantics": "Deterministic admission order; concurrent start/completion times may differ.",
                "modes": {mode: value["adapter"] for mode, value in manifests.items()}, "schedule": schedule}
    for adapter in adapters.values():
        if hasattr(adapter, "contains_secret") and adapter.contains_secret(canonical_bytes(plan)):
            raise SuiteError("configured credential occurs in batch metadata; run refused")
    return plan, manifests, plans


def plan_batch(suite, adapters, out, *, repeats=3, seed=42, workers=2, max_requests=1000):
    """Create one immutable plan artifact; adapter.respond is never called."""
    plan, _, _ = _build_batch_plan(suite, adapters, repeats=repeats, seed=seed, workers=workers,
                                  max_requests=max_requests)
    digest = hashlib.sha256(canonical_bytes(plan)).hexdigest()
    envelope = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "plan_sha256": digest, "plan": plan}
    directory = _new_directory(out)
    _write_json(directory / "batch-plan.json", envelope)
    return {"network_invoked": False, "planned_calls": plan["planned_calls"], "plan_sha256": digest,
            "plan_path": str((directory / "batch-plan.json").resolve())}


def run_batch(suite, adapters, out, *, repeats=3, seed=42, workers=2, max_requests=1000, expected_plan=None):
    plan, manifests, plans = _build_batch_plan(suite, adapters, repeats=repeats, seed=seed, workers=workers,
                                            max_requests=max_requests)
    digest = hashlib.sha256(canonical_bytes(plan)).hexdigest()
    if expected_plan is not None:
        frozen = read_json(expected_plan, 4_194_304)
        keys(frozen, {"schema_version", "created_at", "plan_sha256", "plan"}, "batch plan artifact")
        integer(frozen["schema_version"], 1, 1, "batch plan schema_version")
        if hashlib.sha256(canonical_bytes(frozen["plan"])).hexdigest() != frozen["plan_sha256"]:
            raise SuiteError("expected batch plan digest mismatch")
        if plan["source"]["head"] is None or plan["source"]["dirty"] is not False:
            raise SuiteError("expected-plan binding requires an available, clean Git checkout")
        if frozen["plan"] != plan:
            raise SuiteError("current configuration, suite, source or schedule differs from expected plan")
    manifest = {**plan, "created_at": datetime.now(timezone.utc).isoformat(), "plan_sha256": digest,
                "expected_plan_sha256": digest if expected_plan is not None else None}
    schedule = plan["schedule"]
    directory = _new_directory(out)
    _write_json(directory / "batch-manifest.json", manifest)
    lookup = {mode: {trial.id: trial for trial in plan} for mode, plan in plans.items()}
    streams = {}
    for mode, mode_manifest in manifests.items():
        child = directory / mode
        child.mkdir()
        (child / "calls").mkdir()
        _write_json(child / "manifest.json", mode_manifest)
        streams[mode] = (child / "observations.jsonl").open("x", encoding="utf-8", newline="\n")
    interrupted = False
    stop_reason = None
    consecutive_errors = cumulative_errors = 0
    events = (directory / "events.jsonl").open("x", encoding="utf-8", newline="\n")
    pending = {}
    pool = ThreadPoolExecutor(max_workers=workers)
    iterator = iter(schedule)
    def event(kind, slot, **extra):
        events.write(canonical_bytes({"at": datetime.now(timezone.utc).isoformat(), "kind": kind,
                                      **slot, **extra}).decode() + "\n")
        events.flush()
    def collect(future):
        nonlocal stop_reason, consecutive_errors, cumulative_errors
        slot = pending.pop(future)
        observation = future.result()
        stream = streams[slot["mode"]]
        stream.write(canonical_bytes(observation).decode() + "\n")
        stream.flush()
        event("completed", slot, error=observation["error"])
        if observation["error"] is not None:
            cumulative_errors += 1
            consecutive_errors += 1
        else:
            consecutive_errors = 0
        call = read_json(directory / slot["mode"] / observation["call_record"]["path"], 4_194_304)
        provider = call["provider"] or {}
        response = provider.get("response", {})
        status = response.get("http_status")
        finish = response.get("metadata", {}).get("finish_reason")
        reason = (f"http_{status}" if status in {401, 402, 403} else
                  "finish_length" if finish == "length" else
                  "response_too_large" if observation["error"] == "response_too_large" else
                  "three_consecutive_errors" if consecutive_errors >= 3 else
                  "ten_cumulative_errors" if cumulative_errors >= 10 else None)
        if stop_reason is None and reason:
            stop_reason = reason
            event("stopped", slot, reason=reason)
    try:
        exhausted = False
        while pending or not exhausted:
            if stop_reason:
                exhausted = True
            while len(pending) < workers and not exhausted:
                slot = next(iterator, None)
                if slot is None:
                    exhausted = True
                    break
                event("submitted", slot)
                mode = slot["mode"]
                future = pool.submit(_record_trial, lookup[mode][slot["trial_id"]], adapters[mode],
                                     directory / mode, suite.sha256)
                pending[future] = slot
            if pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    collect(future)
    except KeyboardInterrupt:
        interrupted = True
        event("interrupted", {"sequence": None, "mode": None, "trial_id": None})
        # Stop admissions, retain already submitted paid calls when their bounded requests finish.
        for future in list(pending):
            collect(future)
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        for stream in streams.values():
            stream.close()
        events.close()
    reports = {mode: analyze_run(directory / mode, directory / f"analysis-{mode}") for mode in adapters}
    summary = {"schema_version": 1, "completed_at": datetime.now(timezone.utc).isoformat(),
               "interrupted": interrupted, "modes": {mode: {"complete": report["complete"],
               "counts": report["counts"]} for mode, report in reports.items()}, "stop_reason": stop_reason,
               "cumulative_errors": cumulative_errors}
    _write_json(directory / "batch-summary.json", summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--reasoning-effort", choices=["low", "high", "max"], default="high")
    parser.add_argument("--max-requests", type=int, default=1000)
    parser.add_argument("--plan-only", action="store_true", help="save a new immutable plan; invoke no model requests")
    parser.add_argument("--expected-plan", type=Path, help="require this batch-plan.json to match before any request")
    args = parser.parse_args(argv)
    try:
        if args.plan_only and args.expected_plan is not None:
            raise SuiteError("--plan-only and --expected-plan cannot be combined")
        key = os.environ.get(args.key_env)
        if not key:
            raise SuiteError("API key environment variable is absent or empty")
        adapters = {mode: OpenAICompatible(args.base_url, args.model, api_key=key, timeout=args.timeout,
                    max_tokens=args.max_tokens, thinking=mode,
                    reasoning_effort=args.reasoning_effort if mode == "enabled" else None)
                    for mode in ("disabled", "enabled")}
        options = {"repeats": args.repeats, "seed": args.seed, "workers": args.workers,
                   "max_requests": args.max_requests}
        if args.plan_only:
            summary = plan_batch(load_suite(args.suite), adapters, args.out, **options)
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        summary = run_batch(load_suite(args.suite), adapters, args.out, expected_plan=args.expected_plan, **options)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if summary["interrupted"]:
            return 130
        return 0 if all(value["complete"] and not value["counts"]["errors"]
                        for value in summary["modes"].values()) else 1
    except SuiteError as exc:
        parser.exit(2, f"Error: {exc}\n")
    except OSError:
        parser.exit(2, "Error: filesystem operation failed; existing evidence is preserved.\n")
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
