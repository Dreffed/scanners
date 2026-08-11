# Architecture Building Blocks (ABB)

Technology-neutral capabilities the `scanners` system provides. Each ABB
is realised by one or more Solution Building Blocks; see
[sbb-catalogue.md](sbb-catalogue.md) and
[abb-sbb-traceability.md](abb-sbb-traceability.md).

## ABB-01 — Filesystem Traversal

Capability to enumerate files across configured filesystem roots and
capture stable technical metadata (path, size, timestamps, hashes,
identity).

- **Responsibilities**: recursive walk; per-file metadata capture;
  content hashing; assignment of a durable per-file identifier.
- **Inputs**: list of scan roots; scan options (hashing, extension
  splitting, filters).
- **Outputs**: raw file records keyed by absolute path.
- **Quality attributes**: incremental (skip unchanged files); resilient
  to permission errors on individual files; supports large trees via
  streaming iteration.

## ABB-02 — Catalogue Store

Capability to persist file records and their derived enrichments across
pipeline stages, and to expose inverted indexes (by extension, hash,
filename, GUID).

- **Responsibilities**: durable read/write of the catalogue; index
  maintenance; deduplication signal.
- **Quality attributes**: single source of truth between stages;
  swappable backend.

## ABB-03 — Format Parser Framework

Capability to discover and invoke pluggable, format-specific parsers
against files, and to memoise their output onto the catalogue.

- **Responsibilities**: parser discovery; extension → parser routing;
  method dispatch (`metadata`, `analyze`, `contents`); global (`:ALL:`)
  parsers that run on every file.
- **Quality attributes**: additive plugin model (no core change to add a
  format); safe re-runs (memoised results).

## ABB-04 — Filename Profiling

Capability to derive a compact, comparable "shape" of a filename or path
by classifying character runs (upper, title, digits, punctuation, CJK,
etc.).

- **Responsibilities**: produce a profile string and a list of extracted
  parts suitable for downstream grouping and rule matching.

## ABB-05 — Rule-Based Tagging

Capability to apply a declarative rule set to selected nodes of each
file record and to attach the resulting tag dictionaries back to that
record.

- **Responsibilities**: rule loading; node selection; regex evaluation;
  ordered rule execution with a stop-on-match option.
- **Quality attributes**: rules editable without code change.

## ABB-06 — Tabular Export

Capability to flatten the enriched catalogue into a wide tabular form
and emit it in an interchange format suitable for analysts.

- **Responsibilities**: schema derivation (core fields + folder columns
  + extracted word columns + parser metadata columns); file emission.

## ABB-07 — Human Reporting

Capability to summarise the catalogue for a human operator: totals,
duplicates by hash, extension breakdown, sample records, per-extension
report.

## ABB-08 — Configuration Management

Capability to describe scan roots, parser activation, analysis
selection, rule files, and storage locations declaratively, so behaviour
changes without code changes.

- **Responsibilities**: JSON configuration loading; portable path
  resolution (`{root, folders, name, ext}` triples).

## ABB-09 — Logging & Observability

Capability to emit structured progress and diagnostic information from
every stage under a single logging configuration.

## ABB-10 — Graph-Based Catalogue (optional)

Capability to persist scan results as a graph of scans, entities,
versions and tags, enabling relationship queries the pickle store
cannot answer efficiently.

- **Status**: partial. See "Gotchas" in root `CLAUDE.md`.
