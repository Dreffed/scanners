# Solution Building Blocks (SBB)

Concrete modules, classes, entry-points and configs that realise the
ABBs in [abb-catalogue.md](abb-catalogue.md). See
[abb-sbb-traceability.md](abb-sbb-traceability.md) for the matrix.

## SBB-01 — File Walker & Hasher

- **Files**: `utils/utils_files.py` (`scan_files`, `get_file_metadata`,
  `make_hash`, `get_info`, `get_filename`, `splitall`).
- **Realises**: ABB-01.
- **Contract**: `scan_files(folder, options)` is a generator yielding
  records with `file, folder, ext, folders?, guid, modified?, accessed?,
  size?, bytes?, hash?`. Hashing is gated by
  `scanoptions.generatehash` and `scanoptions.maxhashsize`.
- **Notes**: `guid` is a `uuid1` per traversal; reused across scans by
  matching prior records on path.

## SBB-02 — Scan Orchestrator (pickle)

- **File**: `scan_files.py`.
- **Realises**: ABB-01, ABB-02, ABB-04.
- **Behaviour**: loads the prior catalogue → walks each root → skips
  files whose `(size, SHA1)` match the prior record → appends `guid` to
  `scan.files` → persists after each root via
  `utils_pickle.save_data`.
- **Index maintenance**: only against the pickle backend. SBB-17 derives
  `exts` / `filenames` / `hashes` / `guids` by query, so the orchestrator
  checks `utils_pickle.derives_indexes(data)` and skips the hand-rolled
  index writes when they are not needed.

## SBB-03 — Scan Orchestrator (Neo4j)

- **File**: `scan_files_gdb.py` + `utils/utils_database.py`.
- **Realises**: ABB-01, ABB-10.
- **Status**: WIP. References `files`, `exts`, `filenames`, `hashes`,
  `guids` without initialising them (DEF-03); needs fixing before use.
  Node classes (`Scan`, `Entity`, `Version`, `Tags`) are declared but not
  wired from the scan loop. It also still writes the inverted indexes by
  hand — see the SBB-02 note on `derives_indexes`.

## SBB-04 — Pickle Catalogue Store (legacy, read-only)

- **File**: `utils/utils_pickle.py` (`load_pickle`, `save_pickle`,
  `get_data`, `save_data`, `get_backend`, `derives_indexes`).
- **Realises**: ABB-02. **Superseded by SBB-17** as the default store.
- **Status**: legacy. Still selected when `locations.data.backend` is
  `"pickle"`, or inferred when `locations.data.ext` is `.pickle` /
  `.pkl`. Reads work as before; writes raise
  `CatalogueReadOnlyError` pointing at SBB-20. Set
  `locations.data.readonly: false` to keep writing pickle for now.
- **Routing contract**: `utils_pickle` is the backend-agnostic front
  door for every stage. `get_backend(config)` picks the store,
  `get_data` / `save_data` delegate to it, and `derives_indexes(data)`
  tells a caller whether the store maintains its own inverted indexes.

## SBB-05 — Parser Loader

- **File**: `parser_loader.py`.
- **Realises**: ABB-03.
- **Contract**: `load(dirname)` returns `{ClassName: class}` for every
  class in `parsers/*_parser.py` whose module name and class name both
  match `.+parser$` (case-insensitive).

## SBB-06 — Base Parser Contract

- **File**: `parsers/base_parser.py`.
- **Realises**: ABB-03.
- **Contract**:
  ```python
  class MyParser(BaseParser):
      name = "my"
      version = "0.0.1"
      def get_extensions(self) -> list[str]: ...
      def get_functions(self) -> dict[str, Callable]:
          return {"metadata": self.get_metadata,
                  "analyze": self.analyze,
                  "contents": self.get_contents}
      def get_metadata(self, filepath) -> dict: ...
      def analyze(self, filepath) -> dict: ...
      def get_contents(self, filepath) -> list: ...
  ```
- **Notes**: Duck-typed — a class does not need to inherit `BaseParser`,
  it only needs the name pattern and the methods.

## SBB-07 — Analyse Orchestrator

- **File**: `analyze_files.py`.
- **Realises**: ABB-03.
- **Behaviour**: builds `functions[ext] = [parser_instances]` from
  active parsers; parsers reporting no extensions and named in
  `analyze.allfiles.parsers` go into `functions[":ALL:"]`. For each
  file, runs each method listed in `analyze.process[].methods` (subject
  to per-process `exts` filter) and every method listed under
  `analyze.allfiles.methods`. Results are memoised as
  `f["<name>.<method>"]`.
- **Defects**: DEF-01 (`:ALL:` parsers never ran) fixed; DEF-07
  (`analyze.allfiles.fields` is ignored — `:ALL:` parsers always receive
  the full `filepath`) open. See [defect-log.md](defect-log.md).

## SBB-08 — Format Parsers

Concrete parsers under `parsers/`, all realising ABB-03:

| SBB | File | Extensions | Notes |
| --- | ---- | ---------- | ----- |
| SBB-08a Word | `parsers/word_parser.py` | `.docx` etc. | via `python-docx` / `docx2txt` |
| SBB-08b Excel | `parsers/excel_parser.py` | `.xlsx` | via `openpyxl` |
| SBB-08c PowerPoint | `parsers/powerpoint_parser.py` | `.pptx` | via `python-pptx` |
| SBB-08d PDF | `parsers/pdf_parser.py` | `.pdf` | via `pdfplumber` / `pdfminer.six` / `PyMuPDF` |
| SBB-08e EXIF | `parsers/exif_parser.py` | images | via `Pillow` |
| SBB-08f Image Text | `parsers/imagetext_parser.py` | images | OCR-style text extraction |
| SBB-08g ICS | `parsers/ics_parser.py` | `.ics` | via `ics` |
| SBB-08h ZIP | `parsers/zip_parser.py` | `.zip` | archive contents |
| SBB-08i DICOM | `parsers/dicom_parser.py` | `.dcm` | via `pydicom`. **Defect DEF-04:** class named `BaseParser` — will not be picked up by the loader until renamed to `DicomParser`. |

## SBB-09 — Filename Profiler

- **Files**: `utils/utils_rules.py` (`get_regexes`, `profile`,
  `expand_profile`, `consolidate_profile`, `frequency`);
  `parsers/name_parser.py` (`NameParser`, `:ALL:` parser).
- **Realises**: ABB-04.
- **Output**: `{"parts": [...], "profile": "U2W3N4...", "expand": "..."}`
  attached to each record.

## SBB-10 — Rules Engine

- **File**: `run_rules.py`.
- **Realises**: ABB-05.
- **Behaviour**: loads a JSON rule list from
  `locations.rulesfile`; for each rule, resolves a node from the file
  record (currently only `source.type == "path"` implemented via
  `get_node_from_dict`), runs the rule (currently only
  `rule.type == "regex"` implemented via `run_regex` / `get_regex_tags`),
  writes tags to `f[rule.destination.node]`. `rule.stop=true` short-
  circuits remaining rules for that file.

## SBB-11 — Excel Exporter

- **File**: `export_files.py`.
- **Realises**: ABB-06.
- **Behaviour**: emits `Document List - <last-folder>.xlsx` via
  `pandas` + `xlsxwriter`. Columns are core fields → folder columns
  (`f00..fNN`) → word columns from the name profile (`w00..wNN`) →
  sorted parser-metadata columns. A folder or word column is only
  requested when at least one row populates it.
- **Defects**: DEF-02 (crash when no filename yields a word-type profile
  part) fixed; DEF-05 (`writer.save()`, removed in pandas 2.x) and
  DEF-06 (`UnboundLocalError` on an empty catalogue) open. See
  [defect-log.md](defect-log.md).

## SBB-12 — Human Reporter

- **File**: `display_files.py`.
- **Realises**: ABB-07.
- **Config**: `display.summary`, `display.duplicates`,
  `display.extensions`, `display.sample`, `display.report[]`.

## SBB-13 — JSON Config Loader

- **File**: `utils/utils_json.py` (`get_setup`, `load_json`).
- **Realises**: ABB-08.
- **Path resolution**: `utils/utils_files.get_filename({root, folders,
  name?, ext?})` — `root == "."` resolves to `os.getcwd()` at call time,
  so scripts must be run from the repo root.

## SBB-14 — Logging Configuration

- **Files**: every entry-point calls
  `logging.config.fileConfig('logging_config.ini', ...)` from its
  `if __name__ == "__main__":` block; `logs/` is the conventional sink.
- **Realises**: ABB-09.
- **Constraint**: `logging_config.ini` is gitignored — it must be
  provided in the working directory to *run* a stage. Importing a stage
  (for tests, or `--help`) no longer requires it.

## SBB-15 — Graph Data Model (optional)

- **File**: `utils/utils_database.py` (`GraphDB`, `Scan`, `Entity`,
  `Version`, `Tags`, `set_connection`).
- **Realises**: ABB-02, ABB-10.
- **Status**: node classes exist; scan-time wiring is incomplete (see
  SBB-03).

## SBB-16 — Configuration Set

- **Directory**: `config/` (gitignored). Example:
  `config_scanner_google.json`, `config_scanner_nas.json`,
  `config_database.json`.
- **Realises**: ABB-08.
- **Structure**: `scanoptions`, `locations`, `parsers`, `analyze`,
  `display` — see `config/config_scanner_google.json` for a worked
  example.
- **Catalogue keys** (`locations.data`):

  | Key | Values | Meaning |
  | --- | ------ | ------- |
  | `backend` | `"sqlite"` \| `"pickle"` | Store to use. Omitted → inferred from `ext` (`.pickle`/`.pkl` → pickle, anything else → sqlite). |
  | `ext` | `".sqlite"` \| `".pickle"` | Catalogue file extension, resolved through `get_filename`. |
  | `volume` | str | Volume id rows are written against. Defaults to `"legacy"` until volume probing lands. |
  | `readonly` | bool | Pickle backend only. Defaults to `true`; set `false` to allow writes to a legacy pickle. |

## SBB-17 — SQLite Catalogue Store

- **File**: `utils/utils_sqlite.py` (`SqliteCatalogue`, `FilesView`,
  `FileRecord`, `IndexView`, `ScansView`, `get_data`, `save_data`,
  `record_to_row`, `row_to_record`).
- **Realises**: ABB-02. Default store since Phase 0 of the
  [scan-performance changelist](changelist-scan-performance.md).
- **Schema**: `volumes`, `files`, `scans`, `scan_files`. `files` is keyed
  `(volume_id, rel_path)` and carries the fields the scanner queries on
  (`name`, `ext`, `size`, `mtime_ns`, `ctime_ns`, `hash`, `guid`,
  `profile`, `first_seen`, `last_seen`, `deleted_at`); every other record
  field is JSON-encoded into `meta_json`. Indexed on `hash`, `ext`,
  `name`, `guid` and `deleted_at`.
- **Settings**: WAL journal, `synchronous = NORMAL`, foreign keys on.
- **Contract**: `get_data(config)` returns a dict-like catalogue —
  `data["files"]` is a `MutableMapping` of `rel_path → record`, and
  `data["exts"]`, `data["filenames"]`, `data["hashes"]`, `data["guids"]`
  are **read-only views derived by query**, so they cannot drift out of
  step with `files`. `data["scans"]` supports `append` / `len` /
  iteration.
- **Write buffering**: records mutated in place (the `analyze_files.py`
  and `run_rules.py` pattern) mark themselves dirty via `FileRecord` and
  are upserted on `flush()`, on `save_data`, or automatically every
  `AUTOFLUSH` (2000) records. Iteration is keyset-paged
  (`PAGE_SIZE` = 1000) so a caller may mutate and save mid-iteration.
- **Hash shape**: the column is a single SHA1 hex string. Until the
  SHA1-only phase lands, records are rehydrated as `{"SHA1": <hex>}` so
  existing readers keep working; a legacy `{"MD5": ..., "SHA1": ...}`
  dict is accepted on write and flattened to its SHA1.
- **Not yet used**: `deleted_at` and per-scan change counters exist in
  the schema but are only populated once the change-detection phase
  lands; `volume_id` is `"legacy"` for every row until volume probing
  (SBB-18) arrives.

## SBB-20 — Pickle → SQLite Migrator

- **File**: `migrate_pickle_to_sqlite.py`.
- **Realises**: ABB-02.
- **Behaviour**: reads a legacy pickle, batches (5000 at a time) the
  `files` dict and the `scans` list into a SQLite catalogue inside a
  single transaction, so an interrupted run leaves the target untouched.
  One-way.
- **Invocation**: `-cp <config>` derives both paths from
  `locations.data` (target defaults to the source with a `.sqlite`
  extension); `--pickle` / `--sqlite` override either. `--assume-volume`
  sets the volume id recorded against migrated rows (default `legacy`).
- **Lossy step**: records that only ever carried an MD5 lose their hash
  — the schema keeps SHA1 only. They are re-hashed the next time the
  file is seen as changed.
