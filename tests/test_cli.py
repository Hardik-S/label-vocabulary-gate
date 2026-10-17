import json
import subprocess
import sys
from pathlib import Path

import pytest

from label_vocabulary_gate import cli


def write(path: Path, value: bytes | str) -> Path:
    path.write_bytes(value.encode("utf-8") if isinstance(value, str) else value)
    return path


def invoke(rows: Path, vocab: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-m", "label_vocabulary_gate.cli",
                           str(rows), str(vocab)], capture_output=True, text=True)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_all_declared_and_unneeded_vocabulary_is_valid(tmp_path, newline):
    rows = write(tmp_path / "rows", newline.join([
        '{"id":"a","label":"Yes"}', '{"id":"b","label":"No"}']) + newline)
    vocab = write(tmp_path / "vocab", '{"labels":["Yes","No","Unused"]}')
    result = invoke(rows, vocab)
    assert (result.returncode, result.stdout, result.stderr) == (
        0, '{"status":"within_vocabulary","record_count":2,"unknown_lines":[]}\n', "")


def test_unknowns_are_sorted_physical_lines_and_never_echoed(tmp_path):
    rows = write(tmp_path / "rows", '{"id":"PRIVATE_ID","label":"PRIVATE_LABEL"}\n'
                 '{"id":"other","label":"Outside"}\n')
    vocab = write(tmp_path / "vocab", '{"labels":["Known"]}')
    result = invoke(rows, vocab)
    assert result.returncode == 1
    assert result.stdout == '{"status":"unknown_labels","record_count":2,"unknown_lines":[1,2]}\n'
    assert "PRIVATE" not in result.stdout and "Outside" not in result.stdout
    assert result.stderr == ""


def test_empty_rows_are_valid(tmp_path):
    rows = write(tmp_path / "rows", b"")
    vocab = write(tmp_path / "vocab", '{"labels":["unused"]}')
    result = invoke(rows, vocab)
    assert (result.returncode, result.stdout) == (
        0, '{"status":"within_vocabulary","record_count":0,"unknown_lines":[]}\n')


@pytest.mark.parametrize("bad", [
    b'{"id":"x","label":"a"}\n\n',
    b'{"id":"x","label":"a"}\n\n{"id":"y","label":"b"}',
    b'{"id":"x","label":"a"}\xe2\x80\xa8{"id":"y","label":"b"}',
    b'{"id":"x","id":"y","label":"a"}',
    b'{"id":"x","label":"a","extra":0}',
    b'{"id":"x","label":NaN}',
    b'{"id":"x","label":"a"}\xff',
    b'[]', b'{"id":"","label":"a"}', b'{"id":"x","label":""}',
    b'{"id":"x","label":"a"}\n{"id":"x","label":"b"}',
])
def test_invalid_rows_are_quiet_and_atomic(tmp_path, bad):
    rows = write(tmp_path / "rows", bad)
    vocab = write(tmp_path / "vocab", '{"labels":["a"]}')
    result = invoke(rows, vocab)
    assert (result.returncode, result.stdout, result.stderr) == (
        2, '{"status":"invalid_input"}\n', "")


@pytest.mark.parametrize("bad", [
    b'{"labels":[]}', b'{"labels":["a","a"]}', b'{"labels":[""]}',
    b'{"labels":["a"],"extra":0}', b'{"labels":["a"],"labels":["b"]}',
    b'{"labels":[NaN]}', b'{"labels":["a"]}\xff', b'[]', b'{}',
])
def test_invalid_vocabulary_is_quiet(tmp_path, bad):
    rows = write(tmp_path / "rows", '{"id":"x","label":"a"}')
    vocab = write(tmp_path / "vocab", bad)
    result = invoke(rows, vocab)
    assert (result.returncode, result.stdout, result.stderr) == (
        2, '{"status":"invalid_input"}\n', "")


def test_exact_unicode_no_normalization_or_trimming(tmp_path):
    rows = write(tmp_path / "rows", '{"id":"x","label":"é"}')
    vocab = write(tmp_path / "vocab", '{"labels":["e\u0301"]}')
    result = invoke(rows, vocab)
    assert result.returncode == 1
    assert json.loads(result.stdout)["unknown_lines"] == [1]


def test_malformed_argv_is_quiet_and_does_not_leak_valid_private_paths(tmp_path):
    rows = write(tmp_path / "PRIVATE_ROWS.jsonl", '{"id":"PRIVATE_ID","label":"PRIVATE_LABEL"}')
    vocab = write(tmp_path / "PRIVATE_VOCAB.json", '{"labels":["PRIVATE_LABEL"]}')
    for args in ([], [str(rows)], [str(rows), str(vocab), "extra"],
                 ["--private-marker", str(vocab)]):
        result = subprocess.run([sys.executable, "-m", "label_vocabulary_gate.cli", *args],
                                capture_output=True, text=True)
        assert (result.returncode, result.stdout, result.stderr) == (
            2, '{"status":"invalid_input"}\n', "")
        assert "PRIVATE" not in result.stdout + result.stderr


@pytest.mark.parametrize("invalid_side", ["rows", "vocabulary"])
def test_attempts_both_complete_inputs_even_when_first_is_invalid(tmp_path, monkeypatch, invalid_side):
    visited = []
    orig_rows, orig_vocab = cli._rows, cli._vocabulary

    def rows(path):
        visited.append("rows")
        if invalid_side == "rows":
            raise cli.InvalidInput
        return orig_rows(path)

    def vocabulary(path):
        visited.append("vocabulary")
        if invalid_side == "vocabulary":
            raise cli.InvalidInput
        return orig_vocab(path)

    monkeypatch.setattr(cli, "_rows", rows)
    monkeypatch.setattr(cli, "_vocabulary", vocabulary)
    rows_path = write(tmp_path / "rows", '{"id":"x","label":"a"}')
    vocab_path = write(tmp_path / "vocab", '{"labels":["a"]}')
    assert cli.run([str(rows_path), str(vocab_path)]) == (2, '{"status":"invalid_input"}\n')
    assert visited == ["rows", "vocabulary"]


@pytest.mark.parametrize("arg", ["-h", "--help"])
def test_help_succeeds(arg):
    result = subprocess.run([sys.executable, "-m", "label_vocabulary_gate.cli", arg],
                            capture_output=True, text=True)
    assert result.returncode == 0 and "usage:" in result.stdout and result.stderr == ""

