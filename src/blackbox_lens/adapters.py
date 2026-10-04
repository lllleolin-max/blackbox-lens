"""Small adapters. The HTTP adapter makes one bounded, nonredirecting request."""
from __future__ import annotations

import http.client
import hashlib
import ipaddress
import io
import json
import math
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlsplit

from .suite import MAX_RAW_CHARS, SuiteError, decode_json, text_field

if TYPE_CHECKING:
    from .engine import Trial

ERRORS = {"http_error", "network_error", "timeout", "response_too_large", "malformed_response",
          "incomplete_response", "secret_redacted", "adapter_error"}
MAX_RESPONSE_BYTES = 1_048_576


class _DeadlineReader(io.RawIOBase):
    """Apply the remaining total budget to every socket receive, including header lines."""

    def __init__(self, sock, deadline):
        self._sock, self._deadline = sock, deadline
        self._file = sock.makefile("rb", buffering=0)

    def readable(self):
        return True

    def readinto(self, buffer):
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        self._sock.settimeout(remaining)
        return self._file.readinto(buffer)

    def close(self):
        if not self.closed:
            self._file.close()
        super().close()


class _DeadlineResponse(http.client.HTTPResponse):
    def __init__(self, sock, *args, deadline, **kwargs):
        super().__init__(sock, *args, **kwargs)
        raw = _DeadlineReader(sock, deadline)
        self.fp.close()
        self.fp = io.BufferedReader(raw)


@dataclass(frozen=True)
class Reply:
    raw: str | None = None
    error: str | None = None
    evidence: dict | None = None


class Adapter(Protocol):
    @property
    def metadata(self) -> dict: ...

    def respond(self, trial: Trial) -> Reply: ...


class SyntheticAdapter:
    """An intentionally biased fixture; consults expected labels, not a real model."""

    @property
    def metadata(self) -> dict:
        return {"kind": "synthetic", "name": "planted-position-and-hint-bias-v1",
                "description": "Synthetic fixture reads expected answers; never empirical model evidence."}

    def respond(self, trial: Trial) -> Reply:
        mapping = trial.variant.answer_map
        if trial.variant.kind == "option-order":
            return Reply(raw=sorted(mapping)[0])
        if trial.variant.kind == "misleading-hint":
            return Reply(raw=next(k for k in sorted(mapping) if mapping[k] != trial.case.expected))
        return Reply(raw=next(k for k, v in mapping.items() if v == trial.case.expected))


def _local(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class OpenAICompatible:
    """Nonstreaming chat/completions subset. No SDK, proxy, retries or redirects."""

    def __init__(self, base_url: str, model: str, *, api_key: str | None,
                 timeout: float = 30, max_tokens: int | None = None, token_parameter: str = "max_tokens",
                 thinking: str | None = None, reasoning_effort: str | None = None):
        if not isinstance(base_url, str) or any(ord(c) < 33 for c in base_url):
            raise SuiteError("invalid base URL")
        try:
            parsed = urlsplit(base_url)
            host, port = parsed.hostname, parsed.port
        except ValueError:
            raise SuiteError("invalid base URL") from None
        if (parsed.scheme not in {"http", "https"} or not host or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment):
            raise SuiteError("base URL requires http(s), host, and no credentials/query/fragment")
        if parsed.scheme == "http" and not _local(host):
            raise SuiteError("remote endpoints require HTTPS")
        if api_key is None and not _local(host):
            raise SuiteError("remote endpoint requires an API key")
        if api_key is not None and (not isinstance(api_key, str) or not api_key or
                                    any(ord(c) < 33 or ord(c) > 126 for c in api_key)):
            raise SuiteError("invalid API key value")
        text_field(model, "model", 200)
        if api_key and (api_key in model or api_key in base_url):
            raise SuiteError("credential must not occur in endpoint or model metadata")
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise SuiteError("timeout must be finite and in (0, 600] seconds")
        if thinking not in {None, "enabled", "disabled"}:
            raise SuiteError("thinking must be enabled, disabled or unspecified")
        if reasoning_effort not in {None, "low", "high", "max"}:
            raise SuiteError("reasoning_effort must be low, high or max")
        if reasoning_effort is not None and thinking != "enabled":
            raise SuiteError("reasoning_effort requires explicit enabled thinking")
        if max_tokens is None:
            max_tokens = 4096 if thinking == "enabled" else 32
        if type(max_tokens) is not int or not 1 <= max_tokens <= 393216:
            raise SuiteError("max_tokens must be an integer in [1, 393216]")
        if token_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise SuiteError("unsupported token parameter")
        self._scheme, self._host, self._port = parsed.scheme, host, port
        self._path = parsed.path.rstrip("/") + "/chat/completions"
        self._endpoint, self._model = base_url.rstrip("/"), model
        self._api_key, self._timeout = api_key, float(timeout)
        self._max_tokens, self._token_parameter = max_tokens, token_parameter
        self._thinking, self._reasoning_effort = thinking, reasoning_effort

    @property
    def metadata(self) -> dict:
        return {"kind": "openai-compatible", "base_url": self._endpoint, "model": self._model,
                "timeout_seconds": self._timeout, "max_output_tokens": self._max_tokens,
                "token_parameter": self._token_parameter, "retries": 0,
                "redirects": False, "temperature": None if self._thinking == "enabled" else 0,
                "temperature_behavior": "omitted_for_thinking" if self._thinking == "enabled" else "sent_zero",
                "thinking": self._thinking, "reasoning_effort": self._reasoning_effort,
                "max_response_bytes": MAX_RESPONSE_BYTES,
                "reasoning_content_meaning": "Provider-returned text; not guaranteed privileged internal reasoning.",
                "auth_configured": self._api_key is not None,
                "system_template": "Return exactly one of these labels, with no explanation: {sorted_labels}",
                "stream": False}

    def respond(self, trial: Trial) -> Reply:
        # A prompt accidentally containing the configured key is never sent or saved by run_suite.
        if self._api_key and self._api_key in trial.variant.prompt:
            return Reply(error="secret_redacted")
        payload = {"model": self._model, "messages": [
            {"role": "system", "content": "Return exactly one of these labels, with no explanation: "
             + ", ".join(sorted(trial.variant.answer_map))},
            {"role": "user", "content": trial.variant.prompt}],
            "stream": False, self._token_parameter: self._max_tokens}
        if self._thinking is not None:
            payload["thinking"] = {"type": self._thinking}
        if self._thinking != "enabled":
            payload["temperature"] = 0
        if self._reasoning_effort is not None:
            payload["reasoning_effort"] = self._reasoning_effort
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer " + self._api_key
        connection: http.client.HTTPConnection | None = None
        deadline = time.monotonic() + self._timeout
        started = time.monotonic()
        evidence = {"started_at": datetime.now(timezone.utc).isoformat(),
                    "request": {"endpoint": self._endpoint + "/chat/completions", "payload": payload,
                                "timeout_seconds": self._timeout, "auth_configured": self._api_key is not None,
                                "temperature_behavior": self.metadata["temperature_behavior"]},
                    "response": {"http_status": None, "body_bytes_received": 0, "body_truncated": False},
                    "reasoning_content_meaning": self.metadata["reasoning_content_meaning"]}
        chunks, total = [], 0
        def result(raw=None, error=None):
            body = b"".join(chunks)
            response_record = evidence["response"]
            response_record["body_bytes_received"] = total
            response_record["retained_body_bytes"] = len(body)
            response_record["retained_body_sha256"] = hashlib.sha256(body).hexdigest()
            response_record["metadata"] = {"id": None, "model": None, "finish_reason": None,
                                           "content": None, "reasoning_content": None, "usage": None}
            response_record["redacted"] = False
            if body:
                try:
                    provider = decode_json(body)
                    response_record["redacted"] = self.contains_secret(body)
                    response_record["provider_response"] = self._redact(provider)
                    if isinstance(provider, dict):
                        info = response_record["metadata"]
                        for name in ("id", "model", "usage"):
                            info[name] = self._redact(provider.get(name))
                        choices = provider.get("choices")
                        if isinstance(choices, list) and len(choices) == 1 and isinstance(choices[0], dict):
                            info["finish_reason"] = self._redact(choices[0].get("finish_reason"))
                            message = choices[0].get("message")
                            if isinstance(message, dict):
                                for name in ("content", "reasoning_content"):
                                    info[name] = self._redact(message.get(name))
                except SuiteError:
                    text = body.decode("utf-8", errors="replace")
                    response_record["body_prefix_utf8"] = self._redact(text)
                    response_record["redacted"] = response_record["body_prefix_utf8"] != text
            evidence["completed_at"] = datetime.now(timezone.utc).isoformat()
            evidence["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
            evidence["error"] = error
            return Reply(raw=raw, error=error, evidence=evidence)
        try:
            if self._scheme == "https":
                connection = http.client.HTTPSConnection(self._host, self._port, timeout=self._timeout,
                                                         context=ssl.create_default_context())
            else:
                connection = http.client.HTTPConnection(self._host, self._port, timeout=self._timeout)
            connection.response_class = lambda sock, **kwargs: _DeadlineResponse(sock, deadline=deadline, **kwargs)
            connection.request("POST", self._path, body=encoded, headers=headers)
            self._remaining(connection, deadline)
            response = connection.getresponse()
            evidence["response"]["http_status"] = response.status
            while True:
                self._remaining(connection, deadline)
                chunk = response.read1(min(8192, MAX_RESPONSE_BYTES + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    chunks.append(chunk[:MAX_RESPONSE_BYTES - sum(map(len, chunks))])
                    evidence["response"]["body_truncated"] = True
                    return result(error="response_too_large")
                chunks.append(chunk)
            if response.status != 200:
                return result(error="http_error")
            reply = self._parse(b"".join(chunks))
            return result(raw=reply.raw, error=reply.error)
        except TimeoutError:
            evidence["response"]["body_truncated"] = True
            return result(error="timeout")
        except (OSError, http.client.HTTPException, ValueError):
            evidence["response"]["body_truncated"] = True
            return result(error="network_error")
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _remaining(connection: http.client.HTTPConnection, deadline: float) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        if connection.sock is not None:
            connection.sock.settimeout(remaining)

    def _parse(self, data: bytes) -> Reply:
        try:
            value = decode_json(data)
            if self.contains_secret(data):
                return Reply(error="secret_redacted")
            choices = value["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                return Reply(error="malformed_response")
            choice = choices[0]
            if choice.get("finish_reason") != "stop":
                return Reply(error="incomplete_response")
            raw = choice["message"]["content"]
            if not isinstance(raw, str):
                return Reply(error="malformed_response")
            raw.encode("utf-8")
            if len(raw) > MAX_RAW_CHARS:
                return Reply(error="response_too_large")
            if self._api_key and self._api_key in raw:
                return Reply(error="secret_redacted")
            return Reply(raw=raw)
        except (SuiteError, KeyError, TypeError, AttributeError, UnicodeError):
            return Reply(error="malformed_response")

    def _redact(self, value):
        """Redact the configured literal key, including its escaped JSON form in bad bodies."""
        if isinstance(value, str) and self._api_key:
            return value.replace(self._api_key, "[REDACTED]").replace(
                json.dumps(self._api_key)[1:-1], "[REDACTED]")
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, dict):
            return {self._redact(k): self._redact(v) for k, v in value.items()}
        return value

    def contains_secret(self, value: bytes) -> bool:
        if self._api_key is None:
            return False
        def contains(item):
            if isinstance(item, str):
                return self._api_key in item
            if isinstance(item, dict):
                return any(contains(k) or contains(v) for k, v in item.items())
            if isinstance(item, list):
                return any(contains(v) for v in item)
            return False
        return contains(decode_json(value))
