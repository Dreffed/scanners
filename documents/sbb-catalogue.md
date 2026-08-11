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
- **Behaviour**: loads prior pickle → walks each root → skips files
  whose `(size, SHA1)` match the prior record → appends `guid` to
  `scan.files` → maintains `files`, `guids`, `exts`, `filenames`,
  `hashes`, `scans[]` indexes → persists after each root.

## SBB-03 — Scan Orchestrator (Neo4j)

- **File**: `scan_files_gdb.py` + `utils/utils_database.py`.
- **Realises**: ABB-01, ABB-10.
- **Status**: WIP. References `files`, `exts`, `filenames`, `hashes`,
  `guids` without initialising them; needs fixing before use. Node
  classes (`Scan`, `Entity`, `Version`, `Tags`) are declared but not
  wired from the scan loop.

## SBB-04 — Pickle Catalogue Store

- **File**: `utils/utils_pickle.py` (`load_pickle`, `save_pickle`,
  `get_data`, `save_data`).
- **Realises**: ABB-02.
- **Contract**: `get_data(config)` returns `{}` if no prior pickle
  exists; falls through to a stubbed DB branch when `config["database"]`
  is set.

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
| SBB-08i DICOM | `parsers/dicom_parser.py` | `.dcm` | via `pydicom`. **Defect:** class named `BaseParser` — will not be picked up by the loader until renamed to `DicomParser`. |

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
  sorted parser-metadata columns.
- **Note**: uses `writer.save()` (deprecated in pandas 2.x — switch to
  `writer.close()` if upgrading).

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
  `logging.config.fileConfig('logging_config.ini', ...)`; `logs/` is
  the conventional sink.
- **Realises**: ABB-09.
- **Constraint**: `logging_config.ini` is gitignored — it must be
  provided at run time or entry-points will fail on import.

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
