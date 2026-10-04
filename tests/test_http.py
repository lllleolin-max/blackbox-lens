from __future__ import annotations

import json
import socketserver
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from blackbox_lens import OpenAICompatible, Suite, SuiteError, create_plan, run_suite
from blackbox_lens.adapters import MAX_RESPONSE_BYTES
from test_core import small_suite

KEY = 'dummy-key-quote"back\\slash'


@contextmanager
def server(body, status=200, delay=0):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.path, dict(self.headers), json.loads(payload)))
            time.sleep(delay)
            try:
                self.send_response(status)
                if status == 302:
                    self.send_header("Location", "http://127.0.0.1:1/credential-trap")
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                pass
        def log_message(self, *args):
            pass
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/v1", requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join()


def answer(raw="A", finish="stop"):
    return json.dumps({"choices": [{"message": {"content": raw}, "finish_reason": finish}]}).encode()


class HTTPTests(unittest.TestCase):
    def test_request_shape_and_raw_mapping(self):
        with server(answer("B")) as (url, requests):
            adapter = OpenAICompatible(url + "/", "test-model", api_key=KEY, timeout=1)
            trial = next(t for t in create_plan(small_suite(), repeats=1) if t.variant.kind == "option-order")
            self.assertEqual(adapter.respond(trial).raw, "B")
            path, headers, payload = requests[0]
            self.assertEqual(path, "/v1/chat/completions")
            self.assertEqual(headers["Authorization"], "Bearer " + KEY)
            self.assertEqual(payload["messages"][1]["content"], trial.variant.prompt)
            self.assertEqual(payload["messages"][0]["content"], "Return exactly one of these labels, with no explanation: A, B")
            self.assertEqual((payload["temperature"], payload["stream"], payload["max_tokens"]), (0, False, 32))
            self.assertEqual(len(requests), 1)

    def test_local_no_auth_and_parameter_choice(self):
        with server(answer()) as (url, requests):
            adapter = OpenAICompatible(url, "model", api_key=None, token_parameter="max_completion_tokens")
            self.assertIsNone(adapter.respond(create_plan(small_suite())[0]).error)
            self.assertNotIn("Authorization", requests[0][1])
            self.assertIn("max_completion_tokens", requests[0][2])

    def test_response_error_shapes(self):
        cases = [(b"not json", "malformed_response"), (b'{}', "malformed_response"),
                 (b'{"choices":[]}', "malformed_response"),
                 (b'{"choices":[{},{}]}', "malformed_response"),
                 (answer(None), "malformed_response"),
                 (answer("A", "length"), "incomplete_response"),
                 (answer(KEY), "secret_redacted"),
                 (answer("A" * 4097), "response_too_large"),
                 (b" " * (MAX_RESPONSE_BYTES + 1), "response_too_large")]
        for body, expected in cases:
            with self.subTest(expected=expected, size=len(body)), server(body) as (url, requests):
                reply = OpenAICompatible(url, "m", api_key=KEY).respond(create_plan(small_suite())[0])
                self.assertEqual(reply.error, expected)
                self.assertIsNone(reply.raw)
                self.assertEqual(len(requests), 1)

    def test_http_error_redirect_and_timeout_are_single_attempt(self):
        for status, delay, expected in ((401, 0, "http_error"), (429, 0, "http_error"),
                                        (302, 0, "http_error"), (200, 0.2, "timeout")):
            with self.subTest(status=status), server(answer(KEY), status, delay) as (url, requests):
                reply = OpenAICompatible(url, "m", api_key=KEY, timeout=0.05).respond(create_plan(small_suite())[0])
                self.assertEqual(reply.error, expected)
                self.assertEqual(len(requests), 1)

    def test_slow_header_has_total_deadline(self):
        class Slow(socketserver.BaseRequestHandler):
            def handle(self):
                self.request.recv(65536)
                try:
                    for byte in b'HTTP/1.1 200 OK\r\nContent-Length: 1\r\n\r\nA':
                        self.request.sendall(bytes([byte]))
                        time.sleep(0.015)
                except OSError:
                    pass
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Slow)
        httpd.daemon_threads = True
        worker = threading.Thread(target=httpd.serve_forever, daemon=True)
        worker.start()
        try:
            start = time.monotonic()
            reply = OpenAICompatible(f"http://127.0.0.1:{httpd.server_address[1]}/v1", "m", api_key=None,
                                     timeout=0.1).respond(create_plan(small_suite())[0])
            self.assertEqual(reply.error, "timeout")
            self.assertLess(time.monotonic() - start, 0.35)
        finally:
            httpd.shutdown()
            httpd.server_close()
            worker.join()

    def test_secret_never_enters_saved_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp, server(answer(KEY)) as (url, requests):
            directory = Path(tmp) / "run"
            report = run_suite(small_suite(), OpenAICompatible(url, "m", api_key=KEY), directory, repeats=1)
            self.assertEqual(report["counts"]["errors"], 2)
            for path in directory.iterdir():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(KEY, text)
                self.assertNotIn(json.dumps(KEY)[1:-1], text)

    def test_secret_in_suite_metadata_is_refused_before_network(self):
        value = small_suite().to_dict()
        value["description"] = "Accidental credential " + KEY
        with tempfile.TemporaryDirectory() as tmp, server(answer()) as (url, requests):
            with self.assertRaises(SuiteError):
                run_suite(Suite.from_dict(value), OpenAICompatible(url, "m", api_key=KEY), Path(tmp) / "new")
            self.assertFalse((Path(tmp) / "new").exists())
            self.assertEqual(requests, [])

    def test_endpoint_and_numeric_safety(self):
        for url in ("http://remote.test/v1", "http://localhost.evil.test/v1", "https://user:pass@host/v1",
                    "https://host/v1?api_key=x", "https://host/v1#x", "file:///tmp/test", "http://host:abc/v1",
                    "http://127.0.0.1/\r\nX: evil"):
            with self.subTest(url=url), self.assertRaises(SuiteError):
                OpenAICompatible(url, "model", api_key=KEY)
        for timeout in (0, -1, float("nan"), float("inf"), True, 121):
            with self.subTest(timeout=timeout), self.assertRaises(SuiteError):
                OpenAICompatible("http://localhost/v1", "m", api_key=None, timeout=timeout)
        with self.assertRaises(SuiteError):
            OpenAICompatible("https://remote.test/v1", "m", api_key=None)


if __name__ == "__main__":
    unittest.main()
