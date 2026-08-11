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
|   (SQLite default, pickle legacy, Neo4j opt)|
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
| Scan | `scan_files.py` | Walk roots, capture metadata, hash files, dedupe against prior scan. | filesystem, catalogue | catalogue |
| Analyse | `analyze_files.py` | Route each file to the parsers claiming its extension; run the requested methods (`metadata`, `contents`, `analyze`). | catalogue | catalogue |
| Rule | `run_rules.py` | Apply regex-driven rules to selected nodes on each record; write extracted tag dicts back. | catalogue, rules JSON | catalogue |
| Export | `export_files.py` | Flatten records to a DataFrame; emit `Document List - <root>.xlsx`. | catalogue | xlsx |
| Display | `display_files.py` | Human-readable summary / duplicates / extensions / per-ext report. | catalogue | log |

Off to one side, run once when moving an existing catalogue across:

| Stage | Entry point | Responsibility | Reads | Writes |
| ----- | ----------- | -------------- | ----- | ------ |
| Migrate | `migrate_pickle_to_sqlite.py` | One-way copy of a legacy pickle catalogue into SQLite. | pickle | sqlite |

Every stage is invoked independently and coordinates through the same
catalogue. Stages are idempotent: results are memoised on each file
record under `"<parser>.<method>"` keys. No stage names a backend — they
all go through `utils_pickle.get_data` / `save_data`, which routes on
`locations.data.backend`.

## 4. Component view

```
+----------------------- scanners repo -----------------------+
|                                                             |
|  Entry-point layer                                          |
|   scan_files.py  analyze_files.py  run_rules.py             |
|   export_files.py  display_files.py  scan_files_gdb.py      |
|   migrate_pickle_to_sqlite.py                               |
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
|   utils_files   utils_pickle   utils_sqlite   utils_json    |
|   utils_rules   utils_database utils_core                   |
|   utils_marshallwindows  utils_screenshots  utils_systems   |
|                                                             |
|  Configuration (config/, gitignored)                        |
|   config_scanner_*.json  config_database.json               |
|                                                             |
|  Persistence                                                |
|   data/*.sqlite   (default, utils_sqlite)                   |
|   data/*.pickle   (legacy, read-only, utils_pickle)         |
|   Neo4j via utils_database (optional)                       |
+-------------------------------------------------------------+
```

## 5. Canonical data model

### 5.1 Record shape

Per-file record, addressed as `data["files"][path]`:

```
file, ext, folder, folders[], guid,
modified, accessed, size, bytes,
first_seen, last_seen,
hash: {SHA1},                   # single SHA1; MD5 is not carried forward
profile: {parts[], profile, expand},
<Parser>.<method>: { ... },     # e.g. words.metadata, PDFParser.contents
<destination>:      { tag: value, ... }  # from run_rules
```

`data["files"]` is a mapping, not a plain dict — with the SQLite backend
it is a proxy over the `files` table, and records are written back when
the catalogue is flushed. `data["exts"]`, `data["filenames"]`,
`data["hashes"]` and `data["guids"]` are read-only inverted indexes;
under SQLite they are derived by query rather than stored.

### 5.2 SQLite schema

```sql
volumes(id PK, id_source, label, first_seen, last_mount)

files(volume_id FK, rel_path, name, ext, size, mtime_ns, ctime_ns,
      hash, guid, profile, meta_json, first_seen, last_seen, deleted_at,
      PRIMARY KEY(volume_id, rel_path))

scans(id PK, volume_id FK, started_at, finished_at, root, mode,
      added, modified, deleted, unchanged)

scan_files(scan_id FK, guid, change)
```

Columns carry what the scanner queries on; every other record field —
`folders`, `bytes`, parser output, rule tags — is JSON in `meta_json`.
Indexes exist on `hash`, `ext`, `name`, `guid` and `deleted_at`.

Three columns are provisioned but not yet driven: `deleted_at` (soft
delete), the per-scan change counters, and `volume_id`, which is
`"legacy"` for every row until volume probing lands. See the
[scan-performance changelist](changelist-scan-performance.md).

## 6. Extension points

- **New file format** → drop a `parsers/<thing>_parser.py` that returns
  its extensions from `get_extensions()` and its callables from
  `get_functions()`; enable it under the `parsers` block in the active
  config. See [SBB catalogue](sbb-catalogue.md) for the interface.
- **New enrichment rule** → append to the rules JSON referenced by
  `locations.rulesfile`; no code change needed.
- **New sink** → wrap a new script alongside `export_files.py`; read the
  catalogue via `utils_pickle.get_data(config)`. Ad-hoc SQL against the
  `.sqlite` file is also fair game for one-off reporting.
- **New store** → mirror the public surface of `utils_sqlite`
  (`get_data(config)` / `save_data(data, config)` plus the dict-like
  catalogue), then add a branch to `utils_pickle.get_backend`. The
  optional Neo4j store (SBB-15) routes the same way.

## 7. Known constraints

- Windows-first: repo ships a Windows virtualenv (`Scripts/`, `Lib/`,
  `Include/`, `pyvenv.cfg`). Paths in config files use Windows separators.
- Pipeline state lives in a single catalogue file. Under SQLite (WAL) a
  reader and a writer can coexist, but two concurrent scans of the same
  catalogue are still not a supported workflow. The legacy pickle
  backend races outright, which is one reason it is read-only.
- `logging_config.ini` must exist in the working directory to run an
  entry-point (importing one no longer requires it).
- `scan_files_gdb.py` and `parsers/dicom_parser.py` have known defects
  called out in the root `CLAUDE.md` "Gotchas" section.
