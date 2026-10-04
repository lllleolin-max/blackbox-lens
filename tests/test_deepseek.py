from __future__ import annotations

import importlib.util
import copy
import hashlib
import io
import os
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from blackbox_lens import OpenAICompatible, Suite, SuiteError, analyze_run, create_plan, run_suite
from blackbox_lens.suite import canonical_bytes
from test_core import small_suite
from test_http import KEY, server

spec = importlib.util.spec_from_file_location("deepseek_batch", Path(__file__).parents[1] / "tools" / "deepseek_batch.py")
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


def provider_body(content="A", reasoning="Provided reasoning", finish="stop", **extra):
    return json.dumps({"id": "chat-example", "model": "returned-model", "choices": [{"finish_reason": finish,
        "message": {"content": content, "reasoning_content": reasoning}}], "usage": {
        "prompt_tokens": 20, "completion_tokens": 31, "total_tokens": 51,
        "prompt_cache_hit_tokens": 12, "prompt_cache_miss_tokens": 8,
        "prompt_tokens_details": {"cached_tokens": 12}, "completion_tokens_details": {"reasoning_tokens": 30}},
        **extra}).encode()


class DeepSeekTests(unittest.TestCase):
    def test_explicit_thinking_and_temperature_payloads(self):
        for mode in ("disabled", "enabled"):
            with self.subTest(mode=mode), server(provider_body()) as (url, requests):
                adapter = OpenAICompatible(url, "requested-model", api_key=KEY, thinking=mode,
                    reasoning_effort="high" if mode == "enabled" else None)
                reply = adapter.respond(create_plan(small_suite())[0])
                payload = requests[0][2]
                self.assertEqual(payload["thinking"], {"type": mode})
                self.assertEqual(payload["max_tokens"], 4096 if mode == "enabled" else 32)
                if mode == "enabled":
                    self.assertNotIn("temperature", payload)
                    self.assertEqual(payload["reasoning_effort"], "high")
                    self.assertIsNone(adapter.metadata["temperature"])
                else:
                    self.assertEqual(payload["temperature"], 0)
                    self.assertNotIn("reasoning_effort", payload)
                evidence = reply.evidence
                self.assertEqual(evidence["request"]["payload"], payload)
                metadata = evidence["response"]["metadata"]
                self.assertEqual((metadata["id"], metadata["model"], metadata["finish_reason"]),
                                 ("chat-example", "returned-model", "stop"))
                self.assertEqual(metadata["usage"]["completion_tokens_details"]["reasoning_tokens"], 30)
                self.assertEqual(metadata["usage"]["prompt_cache_hit_tokens"], 12)
                self.assertIn("not guaranteed", evidence["reasoning_content_meaning"])

    def test_failed_and_long_reasoning_retained_and_redacted(self):
        cases = [(provider_body(content="", reasoning="x" * 80000, finish="length"), "incomplete_response"),
                 (provider_body(extra={"nested": [KEY]}), "secret_redacted"),
                 (provider_body(reasoning=KEY), "secret_redacted"),
                 (provider_body(content="x" * 5000), "response_too_large")]
        for body, error in cases:
            with self.subTest(error=error), server(body) as (url, _):
                reply = OpenAICompatible(url, "m", api_key=KEY, thinking="enabled").respond(create_plan(small_suite())[0])
                self.assertEqual(reply.error, error)
                self.assertIsNone(reply.raw)
                self.assertIn("provider_response", reply.evidence["response"])
                self.assertNotIn(KEY, canonical_bytes(reply.evidence).decode())
                if error == "incomplete_response":
                    self.assertEqual(len(reply.evidence["response"]["metadata"]["reasoning_content"]), 80000)

    def test_http_bad_json_and_byte_cap_evidence(self):
        from blackbox_lens.adapters import MAX_RESPONSE_BYTES
        cases = [(b'{"error": "' + json.dumps(KEY)[1:-1].encode() + b'"}', 429, "http_error"),
                 (b'bad body ' + KEY.encode(), 200, "malformed_response"),
                 (b'x' * (MAX_RESPONSE_BYTES + 20), 200, "response_too_large")]
        for body, status, error in cases:
            with self.subTest(error=error), server(body, status=status) as (url, _):
                reply = OpenAICompatible(url, "m", api_key=KEY).respond(create_plan(small_suite())[0])
                response = reply.evidence["response"]
                self.assertEqual(reply.error, error)
                self.assertEqual(response["http_status"], status)
                self.assertIsNone(response["metadata"]["usage"])
                self.assertNotIn(KEY, json.dumps(reply.evidence))
                if error == "response_too_large":
                    self.assertTrue(response["body_truncated"])
                    self.assertEqual(response["retained_body_bytes"], MAX_RESPONSE_BYTES)

    def test_declared_body_length_short_read_retains_response_as_error(self):
        body = provider_body()
        with server(body, declared_extra=37) as (url, requests):
            reply = OpenAICompatible(url, "m", api_key=KEY).respond(create_plan(small_suite())[0])
            self.assertEqual(reply.error, "incomplete_response")
            self.assertIsNone(reply.raw)
            response = reply.evidence["response"]
            self.assertTrue(response["body_truncated"])
            self.assertEqual(response["declared_content_length"], len(body) + 37)
            self.assertEqual(response["body_bytes_received"], len(body))
            self.assertEqual(response["provider_response"]["choices"][0]["message"]["content"], "A")
            self.assertEqual(len(requests), 1)

    def test_provider_request_response_and_timestamps_must_be_consistent(self):
        with tempfile.TemporaryDirectory() as tmp, server(provider_body()) as (url, _):
            directory = Path(tmp) / "run"
            run_suite(small_suite(), OpenAICompatible(url, "m", api_key=KEY), directory, repeats=1)
            observation_path = directory / "observations.jsonl"
            original_observations = [json.loads(line) for line in observation_path.read_text().splitlines()]
            call_path = directory / original_observations[0]["call_record"]["path"]
            original_call = json.loads(call_path.read_text())
            def change_both_content(call):
                response = call["provider"]["response"]
                response["provider_response"]["choices"][0]["message"]["content"] = "B"
                response["metadata"]["content"] = "B"
            changes = [change_both_content,
                lambda call: call["provider"]["response"]["metadata"].update(usage={"total_tokens": 99}),
                lambda call: call["provider"]["request"]["payload"]["messages"][1].update(content="different prompt"),
                lambda call: call["provider"]["request"]["payload"].update(model="different model"),
                lambda call: call.update(completed_at="2000-01-01T00:00:00+00:00"),
                lambda call: call["provider"].update(completed_at="2000-01-01T00:00:00+00:00"),
                lambda call: call["provider"]["response"].update(body_truncated=True),
                lambda call: call["provider"]["response"].update(declared_content_length=999999)]
            for index, mutation in enumerate(changes):
                with self.subTest(index=index):
                    call = copy.deepcopy(original_call)
                    observations = copy.deepcopy(original_observations)
                    mutation(call)
                    encoded = canonical_bytes(call)
                    call_path.write_bytes(encoded)
                    observations[0]["call_record"]["sha256"] = hashlib.sha256(encoded).hexdigest()
                    observation_path.write_bytes(b"\n".join(canonical_bytes(x) for x in observations) + b"\n")
                    with self.assertRaises(SuiteError):
                        analyze_run(directory)

    def test_v2_digest_validation_and_v1_reanalysis(self):
        with tempfile.TemporaryDirectory() as tmp, server(provider_body()) as (url, _):
            directory = Path(tmp) / "run"
            report = run_suite(small_suite(), OpenAICompatible(url, "m", api_key=KEY), directory, repeats=1)
            self.assertEqual(report["manifest"]["schema_version"], 2)
            observations = [json.loads(line) for line in (directory / "observations.jsonl").read_text().splitlines()]
            first = observations[0]
            path = directory / first["call_record"]["path"]
            record = json.loads(path.read_text())
            self.assertEqual(record["observation"]["raw"], "A")
            self.assertTrue(record["started_at"].endswith("+00:00"))
            self.assertEqual(report, analyze_run(directory))
            path.write_text("{}")
            with self.assertRaises(SuiteError):
                analyze_run(directory)
            manifest = json.loads((directory / "manifest.json").read_text())
            manifest["schema_version"] = 1
            (directory / "manifest.json").write_text(json.dumps(manifest))
            for observation in observations:
                observation.pop("call_record")
            (directory / "observations.jsonl").write_text("\n".join(json.dumps(x) for x in observations) + "\n")
            self.assertEqual(analyze_run(directory)["counts"], report["counts"])

    def test_batch_schedule_and_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp, server(provider_body()) as (url, requests):
            adapters = {mode: OpenAICompatible(url, "m", api_key=KEY, thinking=mode, max_tokens=4096)
                        for mode in ("disabled", "enabled")}
            directory = Path(tmp) / "batch"
            summary = batch.run_batch(small_suite(), adapters, directory, repeats=2, seed=20261005, workers=2)
            self.assertEqual(len(requests), 8)
            manifest = json.loads((directory / "batch-manifest.json").read_text())
            schedule = manifest["schedule"]
            self.assertEqual([slot["sequence"] for slot in schedule], list(range(1, 9)))
            self.assertEqual([schedule[i]["mode"] for i in range(0, 8, 2)], ["disabled", "enabled"] * 2)
            self.assertEqual(summary["stop_reason"], None)
            self.assertTrue(all(x["complete"] for x in summary["modes"].values()))
            self.assertEqual(manifest["retries"], 0)
            self.assertFalse(manifest["resume_supported"])
            for mode in adapters:
                self.assertEqual(len(list((directory / mode / "calls").glob("*.json"))), 4)
                self.assertEqual(analyze_run(directory / mode)["counts"], summary["modes"][mode]["counts"])

    def test_batch_stops_after_truncation_and_auth_error(self):
        for body, status, reason in ((provider_body(finish="length"), 200, "finish_length"),
                                    (b'{"error":"unauthorized"}', 401, "http_401")):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp, server(body, status=status) as (url, requests):
                adapters = {mode: OpenAICompatible(url, "m", api_key=KEY, thinking=mode)
                            for mode in ("disabled", "enabled")}
                summary = batch.run_batch(small_suite(), adapters, Path(tmp) / "batch", repeats=3, workers=1)
                self.assertEqual(len(requests), 1)
                self.assertEqual(summary["stop_reason"], reason)
                self.assertEqual(sum(x["counts"]["missing"] for x in summary["modes"].values()), 11)

    def test_plan_only_cli_and_matching_plan_bind_actual_schedule_without_http_planning(self):
        with tempfile.TemporaryDirectory() as tmp, server(provider_body()) as (url, requests):
            root = Path(tmp)
            suite = small_suite()
            suite_path = root / "suite.json"
            suite_path.write_bytes(canonical_bytes(suite.to_dict()))
            source = {"head": "test-clean-commit", "dirty": False,
                      "runner_sha256": "a" * 64, "package_sha256": "b" * 64}
            options = {"repeats": 1, "seed": 20261005, "workers": 1, "max_requests": 4}
            with patch.object(batch, "_source_provenance", return_value=source), patch.dict(os.environ, {"MOCK_KEY": KEY}):
                with redirect_stdout(io.StringIO()):
                    code = batch.main([str(suite_path), "--out", str(root / "plan"), "--base-url", url,
                        "--model", "m", "--key-env", "MOCK_KEY", "--timeout", "1", "--max-tokens", "4096",
                        "--repeats", "1", "--seed", "20261005", "--workers", "1", "--max-requests", "4", "--plan-only"])
                self.assertEqual(code, 0)
                self.assertEqual(requests, [])
                plan_path = root / "plan" / "batch-plan.json"
                frozen = json.loads(plan_path.read_text())
                self.assertNotIn(KEY, plan_path.read_text())
                adapters = {mode: OpenAICompatible(url, "m", api_key=KEY, thinking=mode, timeout=1,
                    max_tokens=4096, reasoning_effort="high" if mode == "enabled" else None)
                    for mode in ("disabled", "enabled")}
                summary = batch.run_batch(suite, adapters, root / "actual", expected_plan=plan_path, **options)
                self.assertIsNone(summary["stop_reason"])
                self.assertEqual(len(requests), 4)
                manifest = json.loads((root / "actual" / "batch-manifest.json").read_text())
                self.assertEqual(manifest["plan_sha256"], frozen["plan_sha256"])
                self.assertEqual(manifest["expected_plan_sha256"], frozen["plan_sha256"])
                events = [json.loads(line) for line in (root / "actual" / "events.jsonl").read_text().splitlines()]
                admissions = [{k: event[k] for k in ("sequence", "mode", "trial_id")}
                              for event in events if event["kind"] == "submitted"]
                self.assertEqual(admissions, frozen["plan"]["schedule"])

    def test_expected_plan_mismatches_are_refused_before_network_and_output_creation(self):
        with tempfile.TemporaryDirectory() as tmp, server(provider_body()) as (url, requests):
            root, suite = Path(tmp), small_suite()
            source = {"head": "clean-commit", "dirty": False, "runner_sha256": "a" * 64, "package_sha256": "b" * 64}
            adapters = {mode: OpenAICompatible(url, "m", api_key=KEY, thinking=mode)
                        for mode in ("disabled", "enabled")}
            options = {"repeats": 1, "seed": 42, "workers": 1, "max_requests": 4}
            with patch.object(batch, "_source_provenance", return_value=source):
                batch.plan_batch(suite, adapters, root / "plan", **options)
                plan_path = root / "plan" / "batch-plan.json"
                with self.assertRaises(SuiteError):
                    batch.plan_batch(suite, adapters, root / "plan", **options)
                changed = suite.to_dict()
                changed["cases"][0]["variants"][0]["prompt"] += " Changed text."
                for index, (candidate, changes) in enumerate(((suite, {"workers": 2}),
                        (suite, {"seed": 43}), (suite, {"max_requests": 5}), (Suite.from_dict(changed), {}))):
                    out = root / f"mismatch-{index}"
                    with self.assertRaises(SuiteError):
                        batch.run_batch(candidate, adapters, out, expected_plan=plan_path, **{**options, **changes})
                    self.assertFalse(out.exists())
                for index, field in enumerate(("head", "runner_sha256", "package_sha256", "dirty")):
                    changed_source = {**source, field: True if field == "dirty" else "changed"}
                    with patch.object(batch, "_source_provenance", return_value=changed_source), self.assertRaises(SuiteError):
                        batch.run_batch(suite, adapters, root / f"source-{index}", expected_plan=plan_path, **options)
                frozen = json.loads(plan_path.read_text())
                frozen["plan"]["schedule"][0]["trial_id"] = "unplanned"
                plan_path.write_bytes(canonical_bytes(frozen))
                with self.assertRaises(SuiteError):
                    batch.run_batch(suite, adapters, root / "tampered", expected_plan=plan_path, **options)
                self.assertEqual(requests, [])

    def test_mode_validation(self):
        for config in ({"thinking": "yes"}, {"thinking": "disabled", "reasoning_effort": "high"},
                       {"reasoning_effort": "high"}, {"thinking": "enabled", "reasoning_effort": "none"},
                       {"thinking": []}, {"thinking": {}}, {"reasoning_effort": {}}, {"token_parameter": []},
                       {"max_tokens": True}, {"max_tokens": 393217}):
            with self.subTest(config=config), self.assertRaises(SuiteError):
                OpenAICompatible("http://localhost", "m", api_key=None, **config)


if __name__ == "__main__":
    unittest.main()
