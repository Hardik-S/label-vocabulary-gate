# Label Vocabulary Gate

An offline Python 3.10+ command that checks whether each categorical label in a JSONL file is an exact member of a declared vocabulary. It prints counts and physical line numbers only; it never prints labels, identifiers, file paths, or input content. It has no runtime dependencies and makes no network calls.

## Install and run

```console
python -m pip install .
label-vocabulary-gate ROWS.jsonl VOCAB.json
```

Rows use one strict JSON object per physical line, each exactly `{"id":"...","label":"..."}`. IDs must be nonempty and unique within the file. An empty rows file is valid. The vocabulary is one strict JSON object exactly `{"labels":["..."]}` with a nonempty array of unique, nonempty strings. Strings compare exactly: no trimming, case folding, or Unicode normalization. One final line terminator is allowed; LF, CRLF, and CR record delimiters work.

Output is one deterministic JSON object. Exit 0 means every label is declared; exit 1 means some labels are unknown and lists their sorted one-based physical line numbers; exit 2 means invalid command arguments or invalid input. Invalid input always emits only `{"status":"invalid_input"}` and an empty stderr. Both files are attempted before any result is emitted. No partial results are printed.

## Synthetic demonstrations

From the repository root after installation:

```console
label-vocabulary-gate examples/empty/ROWS.jsonl examples/empty/VOCAB.json
# exit 0: {"status":"within_vocabulary","record_count":0,"unknown_lines":[]}
label-vocabulary-gate examples/known/ROWS.jsonl examples/known/VOCAB.json
# exit 0: {"status":"within_vocabulary","record_count":2,"unknown_lines":[]}
label-vocabulary-gate examples/unknown/ROWS.jsonl examples/unknown/VOCAB.json
# exit 1: {"status":"unknown_labels","record_count":2,"unknown_lines":[2]}
label-vocabulary-gate --help
```

Examples contain synthetic records only. Membership is a data-integrity check, not a model run, annotation adapter, semantic-equivalence judgment, or accuracy/quality/statistical claim. Memory grows with input size.

## Development

```console
python -m pip install pytest
python -m pytest -q
```

CI runs the full suite on Ubuntu and Windows with Python 3.10 and 3.13.
