# Launch note

This release candidate provides a local, offline exact-membership gate for categorical fixture labels. Install from the source tree with `python -m pip install .`; invoke `label-vocabulary-gate ROWS.jsonl VOCAB.json`.

The interface intentionally reports only status, record count, and sorted one-based unknown line numbers. Exit 0 means all labels are in the vocabulary, exit 1 means valid rows contain unknown labels, and exit 2 means invalid arguments or invalid files. Synthetic demonstrations are in `examples/`. This tool does not score models or establish annotation quality, semantic equivalence, or statistical validity. CI covers Ubuntu/Windows on Python 3.10/3.13.
