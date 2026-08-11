# Changelist — Scan & Hash Performance

**Status:** proposed, not yet implemented.
**Goal:** re-scanning a USB-attached HDD should be fast enough to routinely
detect adds / deletes / modifications without re-reading every byte.
**Primary use case:** plug drive in → run scan → get a delta report in
seconds/minutes, not hours.

Read this document first, then approve (or edit) the phases below. Each
phase is a self-contained commit that can be shipped independently.

---

## Summary of impact

| Area | Files touched | Behaviour change | Risk |
| ---- | ------------- | ---------------- | ---- |
| Skip-hash-if-unchanged | `utils/utils_files.py`, `scan_files.py` | Repeat scans skip hashing when `(size, mtime_ns)` match prior record | Low — behaviour preserved on full scan |
| Delete detection | `scan_files.py` | New `scan.deleted[]` list emitted per scan | Low — additive |
| `os.scandir` + cached stat | `utils/utils_files.py` | One `stat()` per file instead of two | Low |
| `mtime_ns` field | `utils/utils_files.py`, `scan_files.py`, `export_files.py` | New int field; formatted strings become derived | Medium — pickle schema grows a field |
| Single hash + bigger buffer | `utils/utils_files.py`, config schema | MD5 dropped by default; SHA1/BLAKE3 configurable; 4 MB read buffer | Medium — downstream code reading `hash.MD5` breaks |
| Quick vs full mode | `utils/utils_files.py`, `scan_files.py`, config schema | New `scanoptions.mode` flag | Low |
| Parallel hashing | `utils/utils_files.py`, `scan_files.py` | Thread pool for hash work | Medium — ordering, logging |
| Volume-aware paths | `utils/utils_files.py`, `scan_files.py`, `utils/utils_marshallwindows.py` | Records keyed by `(volume_serial, relative_path)` | High — pickle migration required |
| SQLite catalogue (opt-in) | new `utils/utils_sqlite.py`, `utils/utils_pickle.py` | Alternate backend behind `get_data`/`save_data` | Medium — new dep (stdlib only) |

Total: **7 code files touched**, **4 docs updated**, **1 new util module**
if the SQLite phase is taken.

---

## Phase 1 — Stop re-hashing unchanged files (biggest win)

**Problem.** `utils/utils_files.py:168-171` hashes every file inside the
walk. `scan_files.py:70-82` then compares hashes to decide whether the
file was already indexed. The hash is the expensive step — doing it before
the "have we seen this?" check makes repeat scans as slow as first scans.

**Change.** Move prior-record lookup into the walker; hash only when
`(size, mtime_ns)` differ from prior, or when the file is new.

### `utils/utils_files.py`

- `scan_files(folder, options={})` gains a `prior: dict | None = None`
  parameter. Callers pass in `data["files"]` from the pickle.
- Inside the loop:
  - Look up `prior.get(filepath)`.
  - If `(size, mtime_ns)` match, yield a record with `_unchanged=True`,
    reuse `guid` and `hash` from the prior record, skip hashing.
  - Otherwise yield as today (hash if `generatehash`, generate new guid).
- `get_file_metadata` gains `mtime_ns` alongside `modified`.

### `scan_files.py`

- Pass `prior=files` when calling `scan_files(...)`.
- On `_unchanged=True`: append `guid` to `scan.files`, skip the
  `files/exts/filenames/hashes/guids` mutations (they already contain the
  entry).
- Track `seen_paths: set[str]` during the walk.
- After the walk for each root, compute
  `deleted = [p for p in prior if p.startswith(scanpath) and p not in seen_paths]`
  and store on `scan["deleted"] = deleted`.

### Expected result

Second scan of an unchanged 200 k-file / 500 GB tree drops from **hours to
seconds**. First scan is unchanged.

---

## Phase 2 — Cheaper metadata (`scandir` + `mtime_ns`)

**Problem.** `os.walk` + `get_info` = two `os.stat` calls per file.
`time.strftime` runs for every file. Second-precision timestamps miss
edits within the same second.

**Change.**

- Replace `os.walk` with an `os.scandir`-based walker in
  `utils/utils_files.py`.
- Pass the `os.DirEntry` into `get_file_metadata`; use `entry.stat()`
  once (cached by the OS).
- Store `mtime_ns` (int) and `ctime_ns` (int) on the record.
- Keep the formatted `modified` / `accessed` strings for the moment
  (`export_files.py` and `display_files.py` still use them); mark as
  deprecated in a doc comment.

### Files

- `utils/utils_files.py` — walker rewrite, `get_file_metadata` signature
  change.
- `export_files.py` — read `mtime_ns` for the exported column when
  present, fall back to `modified`.

### Expected result

~30–50 % faster metadata pass on slow media. Sub-second edits are now
detected.

---

## Phase 3 — Single fast hash, larger buffer

**Problem.** `make_hash` currently computes MD5 **and** SHA1 for every
byte read, in 64 KB chunks. Both algorithms are slow on modern hardware
and the small buffer maximises syscall overhead on USB.

**Change.**

- `make_hash(filepath, algo="sha1", bufsize=4*1024*1024)`:
  - `algo` selects one of `sha1` (default, back-compat), `blake3`,
    `xxh3_128`. Returns `{algo_name: hex}` — no more `{MD5, SHA1}`.
  - Buffer default bumped to 4 MB.
- `scanoptions.hashalgo` and `scanoptions.hashbuffer` added to the config
  schema.
- Optional deps: `blake3`, `xxhash` in `requirements.txt`, guarded by
  try/except so the module still imports without them.

### Breaking change

Downstream code that reads `f["hash"]["MD5"]` or `["SHA1"]` will break.
Grep shows two call sites:

- `scan_files.py` (`f_old.get("hash", {}).get("SHA1", "")`) — update to
  read whichever key is present.
- `export_files.py` (`f.get("hash",{}).get("SHA1")`) — same.

Migration: if the pickle contains legacy `{MD5, SHA1}` records they keep
working (the change-detection lookup falls back on size/mtime).

### Expected result

For new/changed files: SHA1 4 MB buffer ≈ **2× faster** than status quo;
BLAKE3 ≈ **5–10× faster**; xxh3 ≈ **10–20× faster** (non-crypto — fine
for change detection, not fine for integrity attestations).

---

## Phase 4 — `scanoptions.mode: "quick" | "full"`

**Problem.** For the day-to-day USB use case, hashing is unnecessary; we
only want the delta. For monthly integrity passes hashing matters.

**Change.**

- New config key `scanoptions.mode`.
  - `"quick"` (new default for USB configs): no hashing at all; deltas
    driven off `(size, mtime_ns)`.
  - `"full"`: hash new/changed files (Phase 1 behaviour after this change).
  - `"rehash"`: force re-hash of everything (audit mode).
- `scan_files_gdb.py` inherits the same flag.

### Files

- `utils/utils_files.py` — read the flag; skip `make_hash` in quick.
- `config/config_scanner_*.json` example — add `"mode": "quick"` to USB
  configs (config folder is gitignored; add to the sample in docs).

### Expected result

Quick scan of a plugged-in HDD becomes a metadata walk only —
IO-bound on the drive's directory-read speed, not on hashing.

---

## Phase 5 — Parallel hashing

**Problem.** Even after Phases 1–3, hashing multiple changed files
happens serially. USB has high per-op latency; overlapping reads across
files smooths the pipeline.

**Change.**

- In `scan_files.py`, collect "needs hashing" file records into a queue
  during the walk; hand them to a `ThreadPoolExecutor` after (or during)
  the walk.
- `scanoptions.hashworkers` (int, default 4). Recommend 2–4 for USB
  spinning disks, 8+ for USB-3 SSDs.
- Keep the walk single-threaded (one spindle, one head).

### Risk

- Logger output interleaves. Fix by prefixing worker id or accepting
  interleave.
- Ensure `save_pickle` isn't called from the worker threads — do it on
  the main thread after each root completes.

### Expected result

For big change sets: near-linear speedup up to the drive's read
saturation point. Small change sets: no measurable effect.

---

## Phase 6 — Volume-aware keys (recommended for USB)

**Problem.** Absolute paths embed the drive letter. Mount the same USB
drive as `E:` today and `F:` next week and the scanner sees every file
as "new" and every prior record as "deleted".

**Change.**

- New helper `utils/utils_marshallwindows.get_volume_serial(path) -> str`
  (Windows-only for now; use `GetVolumeInformationW` via `ctypes` or
  `win32api`).
- Catalogue key becomes `(volume_serial, relative_path_from_mount)`.
- New pickle top-level key `volumes: {serial: {label, first_seen,
  last_mount_path}}`.
- Add a one-off migration script `migrate_pickle_to_volume_keys.py` that
  re-keys an existing pickle by prompting for the current serial.

### Risk

- **Pickle schema break.** Migration required. Document the migration.
- Non-Windows fallback: fall back to absolute paths.

### Expected result

Drive letter changes are invisible. Same drive plugged into a different
machine still recognised.

---

## Phase 7 — SQLite catalogue backend (opt-in)

**Problem.** Above ~50 k files, the load-mutate-write-whole-pickle cycle
starts to dominate wall time and a mid-scan crash corrupts the whole
catalogue.

**Change.**

- New module `utils/utils_sqlite.py`, same public surface as
  `utils/utils_pickle.py`:
  - `get_data(config)` returns a lazy proxy backed by a SQLite table.
  - `save_data(data, config)` becomes a no-op if writes were already
    committed (the store writes incrementally).
- Schema:
  ```sql
  CREATE TABLE files(
    volume TEXT, path TEXT, size INTEGER, mtime_ns INTEGER,
    hash TEXT, hash_algo TEXT, guid TEXT, meta_json TEXT,
    PRIMARY KEY(volume, path)
  );
  CREATE INDEX idx_files_hash ON files(hash);
  CREATE INDEX idx_files_ext  ON files(path_ext);
  CREATE TABLE scans(id INTEGER PRIMARY KEY, started_at TEXT, root TEXT);
  CREATE TABLE scan_files(scan_id INTEGER, guid TEXT);
  ```
- WAL mode; commit after each root.
- `locations.data.backend: "pickle" | "sqlite"` in config; default
  stays `pickle` unless the pickle file is missing and a `.sqlite` file
  exists.

### Expected result

- O(1) prior-record lookup regardless of catalogue size.
- Crash-safe.
- Enables SQL reporting alongside `display_files.py`.

---

## Bonus cleanups bundled with the above

Small, low-risk items called out during the review. Ship where
convenient with the relevant phase.

- **Bug — `scan_files_gdb.py`** references `files`, `exts`, `filenames`,
  `hashes`, `guids` without initialising them. Either fix or delete.
  (Blocks any Neo4j-backed run.)
- **Bug — `parsers/dicom_parser.py`** names its class `BaseParser`; the
  loader requires `.+parser$`, so it is silently skipped. Rename to
  `DicomParser`. (Currently no DICOM files are ever parsed.)
- **Deprecation — `export_files.py`** calls `writer.save()`, removed in
  pandas 2.x. Switch to `with pd.ExcelWriter(...) as writer:`.
- **Startup — every entry-point** runs
  `logging.config.fileConfig('logging_config.ini', ...)` at import time.
  `logging_config.ini` is gitignored, so a fresh clone can't even run
  `--help`. Move the call into `if __name__ == "__main__":`.

---

## Documentation updates required

Every phase above implies one or more documentation edits. Grouped by
file so the diff review is easy.

### `CLAUDE.md`

- **Commands section** — add the mode flag once Phase 4 lands:
  `-cp <config> --mode quick|full|rehash` (or note the config key).
- **Architecture section** — update the record shape once Phase 2 lands
  to include `mtime_ns`.
- **Conventions section** — once Phase 3 lands, add a note that
  `f["hash"]` is `{<algo>: hex}` (single key) and that MD5 is no longer
  produced by default.
- **Gotchas section** — remove the `dicom_parser.py` and
  `scan_files_gdb.py` items once fixed; remove the `writer.save()` item
  once fixed.

### `documents/reference-architecture.md`

- **§3 Pipeline** — add a "Quick vs Full mode" note under Scan.
- **§5 Canonical data model** — add `mtime_ns`, `ctime_ns`; change
  `hash: {MD5, SHA1}` to `hash: {<algo>: hex}`; add `_unchanged` and
  `deleted[]` on scan record.
- **§6 Extension points** — mention the SQLite backend as an alternative
  after Phase 7.
- **§7 Known constraints** — remove pickle-race caveat once SQLite lands;
  add volume-serial caveat once Phase 6 lands.

### `documents/abb-catalogue.md`

- **ABB-01 Filesystem Traversal** — expand "Quality attributes" to
  include: "quick and full modes; delete detection; parallel hashing of
  changed files".
- **ABB-02 Catalogue Store** — expand to acknowledge the SQLite
  alternative and volume-aware keying.
- Consider a new **ABB-11 Change Detection** if the quick-scan
  capability grows further (e.g. filesystem watchers, USN journal on
  Windows). Not needed for Phases 1–6.

### `documents/sbb-catalogue.md`

- **SBB-01** — document new `prior` parameter on `scan_files`, new
  `mtime_ns` field, `mode` handling.
- **SBB-02** — document delete detection and `_unchanged` fast-path.
- **SBB-03** — remove "WIP" caveat once the local-init bug is fixed.
- **SBB-04** — add note about the SQLite alternate (SBB-17 below).
- **SBB-08i** — remove defect note once the class rename lands.
- **SBB-11** — remove `writer.save()` caveat once fixed.
- **SBB-16** — extend the example config sketch with `mode`,
  `hashalgo`, `hashbuffer`, `hashworkers`.
- **New — SBB-17 SQLite Catalogue Store** — added when Phase 7 ships:
  file, contract, index list, migration script pointer.
- **New — SBB-18 Volume Identifier** — added when Phase 6 ships:
  `utils/utils_marshallwindows.get_volume_serial`.

### `documents/abb-sbb-traceability.md`

- Add rows for SBB-17 → ABB-02, ABB-10.
- Add row for SBB-18 → ABB-01, ABB-02.
- If ABB-11 is added, populate its realisers (SBB-01, SBB-02, SBB-17).

### `README.md` (root)

- Currently 14 lines and out of date (no mention of `run_rules.py`,
  `export_files.py`, `scan_files_gdb.py`, parsers, config, or the
  pipeline). Suggest a rewrite that mirrors CLAUDE.md's overview but
  aimed at a first-time human reader.

---

## Suggested rollout order

1. **Phase 1** (skip re-hash) + **Phase 2** (scandir/mtime_ns) —
   one PR, one afternoon. Biggest wall-time win.
2. **Cleanups** — same PR or next, low risk.
3. **Phase 4** (quick/full mode) — trivial config plumbing on top of
   Phase 1.
4. **Phase 3** (single hash + buffer) — separate PR because it changes
   the pickle schema on `hash`.
5. **Phase 5** (parallel hashing) — optional; measure first.
6. **Phase 6** (volume keys) — only if you actually re-mount drives to
   different letters. Requires migration script.
7. **Phase 7** (SQLite) — only if the pickle starts hurting (>50 k
   files or crash-loss becomes a real risk).

---

## Open questions for you

1. **Hash choice.** Are you happy dropping MD5 entirely? SHA1 stays the
   safe default; BLAKE3 is a new dep but a big speedup. Or do you need
   MD5 for anything downstream?
2. **Windows-only volume serials.** Fine to keep the volume-serial
   feature Windows-only for now, or should it fall back to something
   portable (e.g. `os.statvfs` on Linux)?
3. **Config compatibility.** Would you prefer new fields default to
   today's behaviour (safe) or default to the fast behaviour (breaks
   MD5 consumers, needs the CLAUDE.md gotcha updated up-front)?
4. **SQLite now or later.** Do you have any collections that hurt on
   pickle today, or is this a "someday" item?
5. **Deleted-file semantics.** Should a "deleted" record be pruned from
   the catalogue on the next full scan, or kept forever with a
   `deleted_at` timestamp for audit history?
