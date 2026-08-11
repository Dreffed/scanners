# Reference Architecture — scanners

## 1. Purpose

`scanners` inventories filesystem trees and enriches every file with
technical metadata, format-specific metadata, extracted content and
rule-derived tags. The enriched catalogue is intended for downstream
discovery, deduplication, classification and reporting on large,
heterogeneous document estates.

## 2. Context

```
              +------------------+
              | Filesystem roots |   (local disk, NAS, cloud-mounted drives)
              +--------+---------+
                       |
                       v
+--------------------------------------------+
|                 scanners                    |
|                                             |
|  Scan -> Analyse -> Rule -> Export/Display  |
|                                             |
|            Catalogue store                  |
|         (pickle default, Neo4j opt.)        |
+---------------------+-----------------------+
                      |
      +---------------+---------------+
      |               |               |
      v               v               v
   Excel        Log summary       Graph queries
  (xlsx)        (stdout/log)       (Cypher)
```

Stakeholders: data curators, information-governance leads, analysts
looking for duplicates or misplaced sensitive content, and the developer
maintaining the parser plugins.

## 3. Pipeline

| Stage | Entry point | Responsibility | Reads | Writes |
| ----- | ----------- | -------------- | ----- | ------ |
| Scan | `scan_files.py` | Walk roots, capture metadata, hash files, dedupe against prior scan. | filesystem, prior pickle | pickle |
| Analyse | `analyze_files.py` | Route each file to the parsers claiming its extension; run the requested methods (`metadata`, `contents`, `analyze`). | pickle | pickle |
| Rule | `run_rules.py` | Apply regex-driven rules to selected nodes on each record; write extracted tag dicts back. | pickle, rules JSON | pickle |
| Export | `export_files.py` | Flatten records to a DataFrame; emit `Document List - <root>.xlsx`. | pickle | xlsx |
| Display | `display_files.py` | Human-readable summary / duplicates / extensions / per-ext report. | pickle | log |

Every stage is invoked independently and coordinates through the same
pickle file (or graph). Stages are idempotent: results are memoised on
each file record under `"<parser>.<method>"` keys.

## 4. Component view

```
+----------------------- scanners repo -----------------------+
|                                                             |
|  Entry-point layer                                          |
|   scan_files.py  analyze_files.py  run_rules.py             |
|   export_files.py  display_files.py  scan_files_gdb.py      |
|                                                             |
|  Orchestration layer                                        |
|   parser_loader.py  (dynamic import of parsers/*_parser.py) |
|                                                             |
|  Parser plugins (parsers/)                                  |
|   base_parser.py                                            |
|   word_parser.py  excel_parser.py  powerpoint_parser.py     |
|   pdf_parser.py   dicom_parser.py  exif_parser.py           |
|   imagetext_parser.py  ics_parser.py  zip_parser.py         |
|   name_parser.py                                            |
|                                                             |
|  Utilities (utils/)                                         |
|   utils_files   utils_pickle   utils_json                   |
|   utils_rules   utils_database utils_core                   |
|   utils_marshallwindows  utils_screenshots  utils_systems   |
|                                                             |
|  Configuration (config/, gitignored)                        |
|   config_scanner_*.json  config_database.json               |
|                                                             |
|  Persistence                                                |
|   data/*.pickle   (default)                                 |
|   Neo4j via utils_database (optional)                       |
+-------------------------------------------------------------+
```

## 5. Canonical data model

Per-file record, stored under `data["files"][filepath]`:

```
file, ext, folder, folders[], guid,
modified, accessed, size, bytes,
hash: {MD5, SHA1},
profile: {parts[], profile, expand},
<Parser>.<method>: { ... },     # e.g. words.metadata, PDFParser.contents
<destination>:      { tag: value, ... }  # from run_rules
```

Top-level indexes on the pickle: `files`, `exts`, `filenames`, `hashes`,
`guids`, `scans[]`.

## 6. Extension points

- **New file format** → drop a `parsers/<thing>_parser.py` that returns
  its extensions from `get_extensions()` and its callables from
  `get_functions()`; enable it under the `parsers` block in the active
  config. See [SBB catalogue](sbb-catalogue.md) for the interface.
- **New enrichment rule** → append to the rules JSON referenced by
  `locations.rulesfile`; no code change needed.
- **New sink** → wrap a new script alongside `export_files.py`; read the
  pickle via `utils_pickle.get_data(config)`.
- **New store** → follow the pattern in `utils_database.py` and route
  through `get_data` / `save_data` in `utils_pickle`.

## 7. Known constraints

- Windows-first: repo ships a Windows virtualenv (`Scripts/`, `Lib/`,
  `Include/`, `pyvenv.cfg`). Paths in config files use Windows separators.
- Pipeline state lives in a single pickle; parallel runs against the
  same pickle will race.
- `logging_config.ini` must exist in the working directory or entry-points
  fail on import.
- `scan_files_gdb.py` and `parsers/dicom_parser.py` have known defects
  called out in the root `CLAUDE.md` "Gotchas" section.
