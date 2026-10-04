"""Small adapters. The HTTP adapter makes one bounded, nonredirecting request."""
from __future__ import annotations

import http.client
import ipaddress
import io
import json
import math
import ssl
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol
from urllib.parse import urlsplit

from .suite import MAX_RAW_CHARS, SuiteError, decode_json, text_field

if TYPE_CHECKING:
    from .engine import Trial

ERRORS = {"http_error", "network_error", "timeout", "response_too_large", "malformed_response",
          "incomplete_response", "secret_redacted", "adapter_error"}
MAX_RESPONSE_BYTES = 65536


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
            return Reply(raw=next(k for k, v in mapping.items() if v != trial.case.expected))
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
                 timeout: float = 30, max_tokens: int = 32, token_parameter: str = "max_tokens"):
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
        if type(timeout) not in {int, float} or not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise SuiteError("timeout must be finite and in (0, 120] seconds")
        if type(max_tokens) is not int or not 1 <= max_tokens <= 4096:
            raise SuiteError("max_tokens must be an integer in [1, 4096]")
        if token_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise SuiteError("unsupported token parameter")
        self._scheme, self._host, self._port = parsed.scheme, host, port
        self._path = parsed.path.rstrip("/") + "/chat/completions"
        self._endpoint, self._model = base_url.rstrip("/"), model
        self._api_key, self._timeout = api_key, float(timeout)
        self._max_tokens, self._token_parameter = max_tokens, token_parameter

    @property
    def metadata(self) -> dict:
        return {"kind": "openai-compatible", "base_url": self._endpoint, "model": self._model,
                "timeout_seconds": self._timeout, "max_output_tokens": self._max_tokens,
                "token_parameter": self._token_parameter, "retries": 0,
                "redirects": False, "temperature": 0, "auth_configured": self._api_key is not None,
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
            "temperature": 0, "stream": False, self._token_parameter: self._max_tokens}
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer " + self._api_key
        connection: http.client.HTTPConnection | None = None
        deadline = time.monotonic() + self._timeout
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
            if response.status != 200:
                return Reply(error="http_error")  # Do not copy response bodies, URLs or credentials.
            chunks, total = [], 0
            while True:
                self._remaining(connection, deadline)
                chunk = response.read1(min(8192, MAX_RESPONSE_BYTES + 1 - total))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    return Reply(error="response_too_large")
                chunks.append(chunk)
            return self._parse(b"".join(chunks))
        except TimeoutError:
            return Reply(error="timeout")
        except (OSError, http.client.HTTPException, ValueError):
            return Reply(error="network_error")
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
