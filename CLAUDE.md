# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project overview

`scanners` is a Python file-inventory and content-extraction toolkit. It walks configured filesystem roots, indexes each file (metadata, hashes, name-profile), then runs a pluggable set of parsers to extract per-format metadata and content. Output is persisted to a pickle store (default) or a Neo4j graph, and can be exported to Excel.

Primary use case: cataloguing large, heterogeneous document collections (Word, Excel, PowerPoint, PDF, images, DICOM, ZIP, ICS, ...) and enriching entries with tags extracted via regex rules.

## Pipeline (run in this order)

1. `scan_files.py` — walk `locations.scanpaths`, capture metadata + SHA1/MD5, dedupe against prior scans, persist to pickle.
2. `analyze_files.py` — load parsers matching `parsers/*_parser.py`, dispatch each file to parsers by extension (plus `:ALL:` parsers like `NameParser`), store the results back into the pickle.
3. `run_rules.py` — apply regex rules from `locations.rulesfile` to values selected out of each file record; write tag dicts back onto the record.
4. `export_files.py` — flatten records into a pandas DataFrame and emit `Document List - <last-scanpath-folder>.xlsx`.
5. `display_files.py` — human-readable summary/duplicates/extensions report driven by the `display` config block.

A Neo4j-backed variant of step 1 lives in `scan_files_gdb.py` (uses `utils/utils_database.py`; NB: it currently references `files/exts/...` locals without initializing them — treat as WIP).

All entry-points take `--config_path` (default `.\config\config_scanner_google.json`); the graph variant also takes `--database` (default `.\config\config_database.json`).

## Architecture

- `parser_loader.py` — dynamic loader. Imports every `parsers/*_parser.py` module and returns the classes whose names match `.+parser$` (case-insensitive). New parsers are picked up automatically; they only need to be listed in the config `parsers` block to be activated.
- `parsers/base_parser.py` — contract for all parsers: `get_extensions()`, `get_functions()` returning `{"metadata", "analyze", "contents"}` callables. Parsers set `name` and `version` class attrs. A parser returning `[]` from `get_extensions()` is treated as an `:ALL:` parser (e.g. `NameParser`).
- `utils/utils_files.py` — `scan_files()` generator, hash generation, `get_filename()` which resolves `{root, folders, name?, ext?}` config records into absolute paths (`.` → `os.getcwd()`).
- `utils/utils_pickle.py` — pickle load/save + `get_data(config)` (falls through to pickle when a `database` key is not on the config; DB branch is stubbed).
- `utils/utils_rules.py` — character-class regexes and `profile()` which turns a filename into a compact type-profile string (e.g. `U2W3N4`) plus extracted `parts`.
- `utils/utils_database.py` — Neo4j `GraphDB` + `neomodel` node classes (`Scan`, `Entity`, `Version`, `Tags`).
- `utils/utils_json.py` — config loader (`get_setup`).

Data record shape (produced by `scan_files` → stored in `data["files"][filepath]`):
```
{
  "file", "ext", "folder", "folders"[], "guid",
  "modified", "accessed", "size", "bytes",
  "hash": {"MD5", "SHA1"},
  "profile": {"parts"[], "profile", "expand"},
  # per-parser output keyed as "<Parser.name>.<method>", e.g. "words.metadata"
}
```
The top-level pickle also maintains inverted indexes: `exts`, `filenames`, `hashes`, `guids`, and `scans[]`.

## Commands

Environment: this repo ships a Windows virtualenv in `Lib/`, `Scripts/`, `Include/` with `pyvenv.cfg`. Activate with `Scripts\activate` (cmd) or `Scripts\Activate.ps1` (PowerShell).

Install deps:
```
pip install -r requirements.txt
```

Typical run (PowerShell):
```
python scan_files.py    -cp .\config\config_scanner_google.json
python analyze_files.py -cp .\config\config_scanner_google.json
python run_rules.py     -cp .\config\config_scanner_google.json
python export_files.py  -cp .\config\config_scanner_google.json
python display_files.py -cp .\config\config_scanner_google.json
```

Logging is configured from `logging_config.ini` in the working directory (not checked in — `.gitignore` excludes `*.ini`). Every entry-point calls `logging.config.fileConfig('logging_config.ini', ...)` at import time, so it must exist to run any script.

## Conventions

- Parsers live in `parsers/`, filename `<thing>_parser.py`, class name matching `.+Parser$`. Inherit intent from `BaseParser` — you may implement it as a duck-typed class (see `parsers/name_parser.py`, `parsers/dicom_parser.py`), the loader only checks the name pattern.
- Config is JSON. Paths are expressed as `{"root": ".", "folders": [...], "name": "...", "ext": "..."}` triples and resolved through `get_filename()`. `root: "."` means `os.getcwd()` at run time, not the repo root — run scripts from the repo root.
- The pickle store is the source of truth between stages; each stage reads it, mutates, and writes it back. Do not run stages against different pickle paths in the same session.
- `config/`, `data/`, `logs/`, `archive/`, `*.ini`, `*.xlsx`, `*.csv` are all `.gitignore`d. Config files under `config/` are user-specific — do not commit them.

## Gotchas

- `scan_files_gdb.py` references `files`, `exts`, `filenames`, `hashes`, `guids` without defining them in scope. It will `NameError` on the first hit; treat as a partial migration to Neo4j and fix before using.
- `parsers/dicom_parser.py` defines its class as `BaseParser`, not `DicomParser`. The loader requires the class name to match `.+parser$`, so it won't currently be picked up — rename to `DicomParser` if you want it registered.
- `pandas.ExcelWriter.save()` in `export_files.py` is deprecated in newer pandas; use `writer.close()` or a `with` block if you upgrade past pandas 2.x.
- Parser results are memoized on the file record: `"<name>.<method>"` keys are skipped if already present, so delete them (or the record) to force re-analysis after a parser change.

## Documents

Architecture references (ABB / SBB and related) live in `documents/`. Start there for the conceptual model of the system.
