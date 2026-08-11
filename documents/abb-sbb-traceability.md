# ABB ↔ SBB Traceability

Maps each Architecture Building Block to the Solution Building Blocks
that realise it. Keep in sync when adding either an ABB or an SBB.

## ABB → SBB

| ABB | Capability | Realised by |
| --- | ---------- | ----------- |
| ABB-01 | Filesystem Traversal | SBB-01, SBB-02, SBB-03 |
| ABB-02 | Catalogue Store | SBB-04, SBB-15 |
| ABB-03 | Format Parser Framework | SBB-05, SBB-06, SBB-07, SBB-08a…SBB-08i |
| ABB-04 | Filename Profiling | SBB-09 (utils_rules + NameParser), SBB-02 (invocation site) |
| ABB-05 | Rule-Based Tagging | SBB-10 |
| ABB-06 | Tabular Export | SBB-11 |
| ABB-07 | Human Reporting | SBB-12 |
| ABB-08 | Configuration Management | SBB-13, SBB-16 |
| ABB-09 | Logging & Observability | SBB-14 |
| ABB-10 | Graph-Based Catalogue (optional) | SBB-03, SBB-15 |

## SBB → ABB

| SBB | Component | Realises |
| --- | --------- | -------- |
| SBB-01 | File walker & hasher (`utils/utils_files.py`) | ABB-01 |
| SBB-02 | Scan orchestrator, pickle (`scan_files.py`) | ABB-01, ABB-02, ABB-04 |
| SBB-03 | Scan orchestrator, Neo4j (`scan_files_gdb.py`) | ABB-01, ABB-10 |
| SBB-04 | Pickle catalogue store (`utils/utils_pickle.py`) | ABB-02 |
| SBB-05 | Parser loader (`parser_loader.py`) | ABB-03 |
| SBB-06 | Base parser contract (`parsers/base_parser.py`) | ABB-03 |
| SBB-07 | Analyse orchestrator (`analyze_files.py`) | ABB-03 |
| SBB-08a…SBB-08i | Format parsers (`parsers/*_parser.py`) | ABB-03 |
| SBB-09 | Filename profiler (`utils/utils_rules.py`, `parsers/name_parser.py`) | ABB-04 |
| SBB-10 | Rules engine (`run_rules.py`) | ABB-05 |
| SBB-11 | Excel exporter (`export_files.py`) | ABB-06 |
| SBB-12 | Human reporter (`display_files.py`) | ABB-07 |
| SBB-13 | JSON config loader (`utils/utils_json.py`) | ABB-08 |
| SBB-14 | Logging configuration | ABB-09 |
| SBB-15 | Graph data model (`utils/utils_database.py`) | ABB-02, ABB-10 |
| SBB-16 | Configuration set (`config/*.json`) | ABB-08 |

## Coverage notes

- **ABB-05 rule engine**: only `source.type == "path"` and
  `rule.type == "regex"` are implemented. New source or rule types are
  additive changes to `run_rules.py` and go against ABB-05 without
  needing a new ABB.
- **ABB-10 graph catalogue**: partial. SBB-15 has node classes; SBB-03
  is not yet wiring them from the scan loop.
- **Parser plugins**: new parsers extend ABB-03 as new SBB-08x rows —
  do not add a new ABB per format.
