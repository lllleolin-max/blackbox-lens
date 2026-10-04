"""Strict, bounded suite input and stable semantic labels."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_SUITE_BYTES = 1_048_576
MAX_REQUESTS = 1000
MAX_RAW_CHARS = 4096
KINDS = {"baseline", "control", "paraphrase", "irrelevant-context", "option-order", "misleading-hint"}
TOKEN = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


class SuiteError(ValueError):
    """Invalid suite or run artifact. Messages never include input payloads."""


def _unique(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise SuiteError("duplicate JSON object key")
        result[key] = value
    return result


def decode_json(data: str | bytes) -> Any:
    try:
        return json.loads(data, object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(SuiteError("nonfinite JSON number")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise SuiteError("invalid strict JSON") from None


def read_json(path: str | Path, limit: int = MAX_SUITE_BYTES) -> Any:
    try:
        with Path(path).open("rb") as stream:
            data = stream.read(limit + 1)
    except OSError:
        raise SuiteError("cannot read JSON input") from None
    if len(data) > limit:
        raise SuiteError("JSON input exceeds size limit")
    return decode_json(data)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def keys(value: Any, expected: set[str], what: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise SuiteError(f"{what} must contain exactly the documented fields")


def token(value: Any, what: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise SuiteError(f"{what} must be a 1–64 character ASCII identifier")
    return value


def text_field(value: Any, what: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        raise SuiteError(f"invalid {what} length")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise SuiteError(f"invalid {what} Unicode") from None
    return value


def integer(value: Any, minimum: int, maximum: int, what: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SuiteError(f"{what} must be an integer in [{minimum}, {maximum}]")
    return value


@dataclass(frozen=True)
class Variant:
    id: str
    kind: str
    prompt: str
    answer_map: dict[str, str]


@dataclass(frozen=True)
class Case:
    id: str
    expected: str
    canonical_labels: tuple[str, ...]
    variants: tuple[Variant, ...]

    @property
    def baseline(self) -> Variant:
        return next(v for v in self.variants if v.kind == "baseline")


@dataclass(frozen=True)
class Suite:
    title: str
    description: str
    cases: tuple[Case, ...]

    @classmethod
    def from_dict(cls, value: Any) -> Suite:
        keys(value, {"schema_version", "title", "description", "cases"}, "suite")
        integer(value["schema_version"], 1, 1, "schema_version")
        title = text_field(value["title"], "title", 200)
        description = text_field(value["description"], "description", 4000, True)
        if not isinstance(value["cases"], list) or not 1 <= len(value["cases"]) <= 100:
            raise SuiteError("suite must have 1–100 cases")
        cases = []
        seen = set()
        for item in value["cases"]:
            keys(item, {"id", "expected", "canonical_labels", "variants"}, "case")
            cid = token(item["id"], "case id")
            if cid in seen:
                raise SuiteError("duplicate case id")
            seen.add(cid)
            labels = item["canonical_labels"]
            if not isinstance(labels, list) or not 2 <= len(labels) <= 16:
                raise SuiteError("case must have 2–16 canonical labels")
            for label in labels:
                token(label, "canonical label")
            if len(set(labels)) != len(labels) or item["expected"] not in labels:
                raise SuiteError("canonical labels must be unique and include expected")
            variants = item["variants"]
            if not isinstance(variants, list) or not 2 <= len(variants) <= 12:
                raise SuiteError("case must have 2–12 explicit variants")
            parsed, vids = [], set()
            for variant in variants:
                keys(variant, {"id", "kind", "prompt", "answer_map"}, "variant")
                vid = token(variant["id"], "variant id")
                kind = variant["kind"]
                if vid in vids or not isinstance(kind, str) or kind not in KINDS:
                    raise SuiteError("duplicate variant id or unknown variant kind")
                vids.add(vid)
                mapping = variant["answer_map"]
                if not isinstance(mapping, dict) or len(mapping) != len(labels):
                    raise SuiteError("answer_map must map every canonical label exactly once")
                for answer in mapping:
                    token(answer, "output label")
                if any(not isinstance(x, str) for x in mapping.values()) or set(mapping.values()) != set(labels):
                    raise SuiteError("answer_map must be a bijection onto canonical labels")
                parsed.append(Variant(vid, kind, text_field(variant["prompt"], "prompt", 32768), dict(mapping)))
            if sum(v.kind == "baseline" for v in parsed) != 1:
                raise SuiteError("case requires exactly one baseline")
            cases.append(Case(cid, item["expected"], tuple(labels), tuple(parsed)))
        suite = cls(title, description, tuple(cases))
        if len(canonical_bytes(suite.to_dict())) > MAX_SUITE_BYTES:
            raise SuiteError("suite exceeds size limit")
        return suite

    def to_dict(self) -> dict:
        return {"schema_version": 1, "title": self.title, "description": self.description,
                "cases": [{"id": c.id, "expected": c.expected, "canonical_labels": list(c.canonical_labels),
                           "variants": [{"id": v.id, "kind": v.kind, "prompt": v.prompt,
                                         "answer_map": dict(v.answer_map)} for v in c.variants]} for c in self.cases]}

    @property
    def sha256(self) -> str:
        return hashlib.sha256(canonical_bytes(self.to_dict())).hexdigest()


def load_suite(path: str | Path) -> Suite:
    return Suite.from_dict(read_json(path))
