# CLAUDE.md

Guidance for Claude Code working in this repository.

## Project overview

`scanners` is a Python file-inventory and content-extraction toolkit. It walks configured filesystem roots, indexes each file (metadata, hashes, name-profile), then runs a pluggable set of parsers to extract per-format metadata and content. Output is persisted to a pickle store (default) or a Neo4j graph, and can be exported to Excel.

Primary use case: cataloguing large, heterogeneous document collections (Word, Excel, PowerPoint, PDF, images, DICOM, ZIP, ICS, ...) and enriching entries with tags extracted via regex rules.

## Pipeline (run in this order)

1. `scan_files.py` — walk `locations.scanpaths`, capture metadata + SHA1/MD5, dedupe against prior scans, persist to the catalogue.
2. `analyze_files.py` — load parsers matching `parsers/*_parser.py`, dispatch each file to parsers by extension (plus `:ALL:` parsers like `NameParser`), store the results back into the catalogue.
3. `run_rules.py` — apply regex rules from `locations.rulesfile` to values selected out of each file record; write tag dicts back onto the record.
4. `export_files.py` — flatten records into a pandas DataFrame and emit `Document List - <last-scanpath-folder>.xlsx`.
5. `display_files.py` — human-readable summary/duplicates/extensions report driven by the `display` config block.

Run once when moving an existing pickle catalogue to SQLite: `migrate_pickle_to_sqlite.py`.

A Neo4j-backed variant of step 1 lives in `scan_files_gdb.py` (uses `utils/utils_database.py`; NB: it currently references `files/exts/...` locals without initializing them — treat as WIP).

All entry-points take `--config_path` (default `.\config\config_scanner_google.json`); the graph variant also takes `--database` (default `.\config\config_database.json`).

## Architecture

- `parser_loader.py` — dynamic loader. Imports every `parsers/*_parser.py` module and returns the classes whose names match `.+parser$` (case-insensitive). New parsers are picked up automatically; they only need to be listed in the config `parsers` block to be activated.
- `parsers/base_parser.py` — contract for all parsers: `get_extensions()`, `get_functions()` returning `{"metadata", "analyze", "contents"}` callables. Parsers set `name` and `version` class attrs. A parser returning `[]` from `get_extensions()` is treated as an `:ALL:` parser (e.g. `NameParser`).
- `utils/utils_files.py` — `scan_files()` generator, hash generation, `get_filename()` which resolves `{root, folders, name?, ext?}` config records into absolute paths (`.` → `os.getcwd()`).
- `utils/utils_pickle.py` — the backend-agnostic front door every stage uses: `get_data(config)` / `save_data(data, config)` route on `locations.data.backend` (`"sqlite"` default, `"pickle"` legacy; inferred from `locations.data.ext` when absent). `derives_indexes(data)` reports whether the store maintains its own inverted indexes. Pickle writes raise `CatalogueReadOnlyError` unless `locations.data.readonly` is `false`.
- `utils/utils_sqlite.py` — the default catalogue store. `data["files"]` is a mapping proxied over the `files` table; `exts` / `filenames` / `hashes` / `guids` are read-only views derived by query; `scans` supports `append`. Records mutated in place mark themselves dirty and are upserted on flush (automatically every 2000 records). Iteration is keyset-paged, so a stage may mutate and save mid-iteration.
- `utils/utils_rules.py` — character-class regexes and `profile()` which turns a filename into a compact type-profile string (e.g. `U2W3N4`) plus extracted `parts`.
- `utils/utils_database.py` — Neo4j `GraphDB` + `neomodel` node classes (`Scan`, `Entity`, `Version`, `Tags`).
- `utils/utils_json.py` — config loader (`get_setup`).

Data record shape (produced by `scan_files` → stored in `data["files"][filepath]`):
```
{
  "file", "ext", "folder", "folders"[], "guid",
  "modified", "accessed", "size", "bytes",
  "first_seen", "last_seen",
  "hash": {"SHA1"},
  "profile": {"parts"[], "profile", "expand"},
  # per-parser output keyed as "<Parser.name>.<method>", e.g. "words.metadata"
}
```
The catalogue also exposes inverted indexes: `exts`, `filenames`, `hashes`, `guids`, and `scans[]`.

SQLite schema — `volumes`, `files`, `scans`, `scan_files`. `files` is keyed `(volume_id, rel_path)`; columns cover what the scanner queries on (`name`, `ext`, `size`, `mtime_ns`, `ctime_ns`, `hash`, `guid`, `profile`, `first_seen`, `last_seen`, `deleted_at`) and every other record field is JSON in `meta_json`. `deleted_at`, the per-scan change counters and real `volume_id` values are provisioned but not yet driven — see `documents/changelist-scan-performance.md`.

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

Move a legacy pickle catalogue to SQLite (one-way, run once):
```
python migrate_pickle_to_sqlite.py -cp .\config\config_scanner_google.json
python migrate_pickle_to_sqlite.py --pickle .\data\scan.pickle --sqlite .\data\scan.sqlite
```
Then point `locations.data` at the `.sqlite` file (or set `"backend": "sqlite"`).

Logging is configured from `logging_config.ini` in the working directory (not checked in — `.gitignore` excludes `*.ini`). Every entry-point calls `logging.config.fileConfig('logging_config.ini', ...)` from its `__main__` block, so it must exist to run a script — but not to import one.

## Conventions

- Parsers live in `parsers/`, filename `<thing>_parser.py`, class name matching `.+Parser$`. Inherit intent from `BaseParser` — you may implement it as a duck-typed class (see `parsers/name_parser.py`, `parsers/dicom_parser.py`), the loader only checks the name pattern.
- Config is JSON. Paths are expressed as `{"root": ".", "folders": [...], "name": "...", "ext": "..."}` triples and resolved through `get_filename()`. `root: "."` means `os.getcwd()` at run time, not the repo root — run scripts from the repo root.
- The catalogue is the source of truth between stages; each stage reads it, mutates, and writes it back. Do not run stages against different catalogue paths in the same session.
- Stages must not name a backend. Go through `utils_pickle.get_data` / `save_data` — never `save_pickle` directly — so the same code works against SQLite and the legacy pickle.
- Do not hand-maintain the `exts` / `filenames` / `hashes` / `guids` indexes when `derives_indexes(data)` is true; SQLite derives them by query, and assignments to those views are ignored.
- `hash` on a record is `{"SHA1": <hex>}`. MD5 is not carried forward — a record migrated with only an MD5 loses its hash and is re-hashed when the file next changes.
- `config/`, `data/`, `logs/`, `archive/`, `*.ini`, `*.xlsx`, `*.csv` are all `.gitignore`d. Config files under `config/` are user-specific — do not commit them.

## Gotchas

- `scan_files_gdb.py` references `files`, `exts`, `filenames`, `hashes`, `guids` without defining them in scope. It will `NameError` on the first hit; treat as a partial migration to Neo4j and fix before using.
- `parsers/dicom_parser.py` defines its class as `BaseParser`, not `DicomParser`. The loader requires the class name to match `.+parser$`, so it won't currently be picked up — rename to `DicomParser` if you want it registered.
- `pandas.ExcelWriter.save()` in `export_files.py` is deprecated in newer pandas; use `writer.close()` or a `with` block if you upgrade past pandas 2.x.
- Parser results are memoized on the file record: `"<name>.<method>"` keys are skipped if already present, so delete them (or the record) to force re-analysis after a parser change.
- The pickle backend is read-only. A stage writing to a `.pickle` catalogue raises `CatalogueReadOnlyError` — migrate it, or set `locations.data.readonly: false` to opt back in.
- `export_files.py` raises `UnboundLocalError` on an empty catalogue (`df_cols` is only assigned inside the per-record loop).
- `analyze.allfiles.fields` is ignored — `:ALL:` parsers always receive the full `filepath`, so `names.metadata` profiles the whole path, not just the filename.

Full register with root causes, including defects already fixed: `documents/defect-log.md`.

## Documents

Architecture references (ABB / SBB and related) live in `documents/`. Start there for the conceptual model of the system.
