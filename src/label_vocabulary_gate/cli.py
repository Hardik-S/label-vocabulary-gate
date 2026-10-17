"""Strict, privacy-preserving command line interface."""

import json
import sys
from pathlib import Path
from typing import Any


class InvalidInput(Exception):
    """An input file violates the frozen input contract."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise InvalidInput


def _json_value(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=_reject_constant)
    except (ValueError, TypeError, RecursionError):
        raise InvalidInput from None


def _read_text(path: str) -> str:
    try:
        return Path(path).read_bytes().decode("utf-8", errors="strict")
    except (OSError, UnicodeError, ValueError):
        raise InvalidInput from None


def _rows(path: str) -> tuple[list[str], int]:
    text = _read_text(path)
    if not text:
        return [], 0
    # JSONL permits LF, CRLF, and CR. Unicode separators remain ordinary data.
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.endswith("\n"):
        normalized = normalized[:-1]
    records = normalized.split("\n")
    labels: list[str] = []
    ids: set[str] = set()
    for record in records:
        if not record:
            raise InvalidInput
        value = _json_value(record)
        if not isinstance(value, dict) or set(value) != {"id", "label"}:
            raise InvalidInput
        identifier, label = value["id"], value["label"]
        if not isinstance(identifier, str) or not identifier:
            raise InvalidInput
        if not isinstance(label, str) or not label or identifier in ids:
            raise InvalidInput
        ids.add(identifier)
        labels.append(label)
    return labels, len(records)


def _vocabulary(path: str) -> set[str]:
    value = _json_value(_read_text(path))
    if not isinstance(value, dict) or set(value) != {"labels"}:
        raise InvalidInput
    labels = value["labels"]
    if (not isinstance(labels, list) or not labels
            or any(not isinstance(item, str) or not item for item in labels)
            or len(set(labels)) != len(labels)):
        raise InvalidInput
    return set(labels)


def _help() -> str:
    return ("usage: label-vocabulary-gate ROWS.jsonl VOCAB.json\n\n"
            "Check exact categorical label membership without printing labels or IDs.\n"
            "Exit 0: all labels are declared; exit 1: unknown labels; exit 2: invalid input.\n")


def run(argv: list[str]) -> tuple[int, str]:
    if argv in (["-h"], ["--help"]):
        return 0, _help()
    if len(argv) != 2 or any(arg.startswith("-") for arg in argv):
        return 2, '{"status":"invalid_input"}\n'

    # Always attempt both complete file validations before producing any result.
    rows_result: tuple[list[str], int] | None = None
    vocabulary_result: set[str] | None = None
    invalid = False
    try:
        rows_result = _rows(argv[0])
    except InvalidInput:
        invalid = True
    try:
        vocabulary_result = _vocabulary(argv[1])
    except InvalidInput:
        invalid = True
    if invalid or rows_result is None or vocabulary_result is None:
        return 2, '{"status":"invalid_input"}\n'

    labels, count = rows_result
    unknown = sorted(index for index, label in enumerate(labels, 1)
                     if label not in vocabulary_result)
    status = "unknown_labels" if unknown else "within_vocabulary"
    return (1 if unknown else 0,
            json.dumps({"status": status, "record_count": count,
                        "unknown_lines": unknown}, separators=(",", ":")) + "\n")


def main() -> None:
    code, output = run(sys.argv[1:])
    sys.stdout.write(output)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
