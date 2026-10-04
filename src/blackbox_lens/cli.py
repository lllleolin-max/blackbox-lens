"""Explicit offline commands, with live calls confined to `run`."""
from __future__ import annotations

import argparse
import json
import os
import sys
from importlib.resources import files
from pathlib import Path

from . import __version__
from .adapters import OpenAICompatible, SyntheticAdapter
from .engine import analyze_run, create_plan, run_suite
from .suite import MAX_REQUESTS, Suite, SuiteError, decode_json, load_suite


def demo_suite() -> Suite:
    return Suite.from_dict(decode_json(files("blackbox_lens").joinpath("data/demo.json").read_bytes()))


def _planning(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repeats", type=int, default=3, help="separate observations per condition (1–100)")
    parser.add_argument("--seed", type=int, default=42, help="presentation-order seed only (0–4294967295)")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Blackbox Lens: bounded behavioral comparisons; no hidden reasoning recovery.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="offline synthetic planted-bias fixture; never calls a model")
    demo.add_argument("--out", type=Path, required=True, help="new output directory")
    _planning(demo)
    plan = commands.add_parser("plan", help="validate suite and count requests, without network")
    plan.add_argument("suite", type=Path)
    _planning(plan)
    run = commands.add_parser("run", help="explicitly invoke a live OpenAI-compatible chat endpoint")
    run.add_argument("suite", type=Path)
    run.add_argument("--out", type=Path, required=True, help="new output directory")
    _planning(run)
    run.add_argument("--base-url", required=True, help="e.g. https://host/v1 or http://localhost:11434/v1")
    run.add_argument("--model", required=True)
    auth = run.add_mutually_exclusive_group()
    auth.add_argument("--key-env", default="OPENAI_API_KEY", help="environment variable name; never pass a key on command line")
    auth.add_argument("--no-auth", action="store_true", help="local host only")
    run.add_argument("--timeout", type=float, default=30, help="request time budget, in seconds (0 < timeout ≤ 600)")
    run.add_argument("--max-tokens", type=int, default=None, help="output budget; default 4096 with enabled thinking, otherwise 32")
    run.add_argument("--token-parameter", choices=["max_tokens", "max_completion_tokens"], default="max_tokens")
    run.add_argument("--thinking", choices=["enabled", "disabled"], help="explicit provider thinking extension; omit for other providers")
    run.add_argument("--reasoning-effort", choices=["low", "high", "max"], help="requires --thinking enabled")
    run.add_argument("--max-requests", type=int, default=100, help=f"explicit cost cap; hard maximum {MAX_REQUESTS}, no retries")
    analyze = commands.add_parser("analyze", help="offline recomputation; ignores cached report metrics")
    analyze.add_argument("run_dir", type=Path)
    analyze.add_argument("--out", type=Path, required=True, help="new directory for recomputed JSON and HTML")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Redirected Windows consoles on older Python may use a non-Unicode locale.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            suite = load_suite(args.suite)
            plan = create_plan(suite, repeats=args.repeats, seed=args.seed)
            print(json.dumps({"suite_sha256": suite.sha256, "cases": len(suite.cases),
                              "conditions": sum(len(c.variants) for c in suite.cases),
                              "repeats": args.repeats, "seed": args.seed, "requests": len(plan),
                              "retries": 0, "network_invoked": False}, indent=2))
            return 0
        if args.command == "demo":
            report = run_suite(demo_suite(), SyntheticAdapter(), args.out,
                               repeats=args.repeats, seed=args.seed, max_requests=MAX_REQUESTS)
        elif args.command == "analyze":
            report = analyze_run(args.run_dir, args.out)
        else:
            suite = load_suite(args.suite)
            key = None if args.no_auth else os.environ.get(args.key_env)
            if not args.no_auth and not key:
                raise SuiteError("API key environment variable is absent or empty; local servers may use --no-auth")
            adapter = OpenAICompatible(args.base_url, args.model, api_key=key, timeout=args.timeout,
                                       max_tokens=args.max_tokens, token_parameter=args.token_parameter,
                                       thinking=args.thinking, reasoning_effort=args.reasoning_effort)
            report = run_suite(suite, adapter, args.out, repeats=args.repeats, seed=args.seed,
                               max_requests=args.max_requests)
        c = report["counts"]
        print(f"{'Complete' if report['complete'] else 'INCOMPLETE'}: {c['observed']}/{c['planned']} observed; "
              f"{c['correct']}/{c['planned']} correct; {c['invalid']} invalid; {c['errors']} errors; {c['missing']} missing.")
        print(f"Reports: {args.out / 'report.json'} and {args.out / 'report.html'}")
        return 0 if report["complete"] and c["errors"] == 0 else 1
    except SuiteError as exc:
        parser.exit(2, f"Error: {exc}\n")
    except OSError:
        parser.exit(2, "Error: filesystem operation failed; no existing output is overwritten.\n")
    except KeyboardInterrupt:
        print("Interrupted: completed observations were retained; use analyze to inspect missing slots.")
        return 130
    return 2
