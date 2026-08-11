# Changelist — Scan & Hash Performance

**Status:** Phase 0 shipped. Phases 1–6 proposed, not yet implemented.
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
| **SQLite catalogue (foundational)** — *shipped* | new `utils/utils_sqlite.py`, `utils/utils_pickle.py`, new `migrate_pickle_to_sqlite.py`, all five stages | Default backend becomes SQLite; pickle stays read-only for legacy | Medium — schema decisions lock later phases in |
| Skip-hash-if-unchanged | `utils/utils_files.py`, `scan_files.py` | Repeat scans skip hashing when `(size, mtime_ns)` match prior record | Low — behaviour preserved on `--mode rehash` |
| Soft-delete + retention | `scan_files.py`, new `purge_files.py`, config schema | Missing files get `deleted_at`; separate purge honours `purge_deleted_after_months` | Low — additive; nothing is lost without an explicit purge |
| `os.scandir` + cached stat | `utils/utils_files.py` | One `stat()` per file instead of two | Low |
| `mtime_ns` field | `utils/utils_files.py`, `scan_files.py`, `export_files.py` | New int field; formatted strings become derived | Low — DB schema is greenfield |
| SHA1-only hash + 4 MB buffer | `utils/utils_files.py`, config schema | MD5 dropped; `hash = {"SHA1": hex}`; larger reads | Medium — downstream code reading `hash.MD5` breaks (must be updated in this phase) |
| Quick vs full mode | `utils/utils_files.py`, `scan_files.py`, config schema | New `scanoptions.mode` flag (default `quick`) | Low |
| Parallel hashing | `utils/utils_files.py`, `scan_files.py` | Thread pool for hash work | Medium — ordering, logging |
| Cross-platform volume ID | `utils/utils_marshallwindows.py` + new `utils/utils_volume.py`, `scan_files.py` | Records keyed by `(volume_id, relative_path)` on Windows/Linux/macOS | Medium — needs identifier probing on each platform |

Total: **~8 code files touched**, **2 new util modules**, **2 new
entry-points** (`migrate_pickle_to_sqlite.py`, `purge_files.py`), **4
docs updated**.

---

## Phase 0 — SQLite catalogue backend (foundational) — **SHIPPED**

**As built.** Matches the design below, with these refinements:

- **`files.name` column added.** The `filenames` inverted index needs the
  basename, and deriving it from `rel_path` in SQL is ugly. `name` is
  populated from the basename regardless of `scanoptions.splitextention`,
  and indexed.
- **Indexes are read-only views.** `exts` / `filenames` / `hashes` /
  `guids` are derived by query, so they cannot drift from `files`.
  Callers that used to build them by hand check
  `utils_pickle.derives_indexes(data)` first; assignment to one of these
  views is ignored with a warning.
- **In-place record mutation is tracked.** `analyze_files.py` and
  `run_rules.py` mutate a record and rely on a later save. `FileRecord`
  marks itself dirty on mutation and is upserted on flush (automatic
  every 2000 records), so neither callsite had to change.
- **Iteration is keyset-paged** (1000 rows), so a stage can mutate and
  save mid-iteration without an open cursor over rows it is rewriting.
- **Pickle writes raise** `CatalogueReadOnlyError` rather than failing
  silently. `locations.data.readonly: false` re-enables them.
- **Transitional hash shape.** The column is a single SHA1 hex string as
  designed, but records are rehydrated as `{"SHA1": <hex>}` so the two
  `hash.SHA1` readers keep working until Phase 3 flips them.
- `deleted_at`, the per-scan change counters and real `volume_id` values
  are provisioned in the schema but not yet driven — Phases 1 and 6.

**Why first.** Every later phase either adds fields to the record
(`mtime_ns`, `deleted_at`, `volume_id`, `hash_algo`) or relies on cheap
prior-record lookup by path. Doing SQLite last would mean shipping a
pickle format we immediately migrate away from.

**Change.**

- New module `utils/utils_sqlite.py` with the same public surface as
  `utils/utils_pickle.py`:
  - `get_data(config)` returns a proxy backed by SQLite.
  - `save_data(data, config)` is a no-op when writes were committed
    incrementally.
  - Prior-record lookup is a single indexed query, not a dict load.
- Schema (greenfield — reflects decisions on Phases 1, 3, 5, 6):
  ```sql
  CREATE TABLE volumes(
    id            TEXT PRIMARY KEY,   -- volume identifier (see Phase 6)
    id_source     TEXT NOT NULL,      -- 'win-serial' | 'linux-uuid' | 'macos-uuid' | 'st_dev'
    label         TEXT,
    first_seen    TEXT NOT NULL,
    last_mount    TEXT
  );

  CREATE TABLE files(
    volume_id     TEXT NOT NULL REFERENCES volumes(id),
    rel_path      TEXT NOT NULL,
    ext           TEXT,
    size          INTEGER,
    mtime_ns      INTEGER,
    ctime_ns      INTEGER,
    hash          TEXT,               -- SHA1 hex, may be NULL in quick mode
    guid          TEXT NOT NULL,
    profile       TEXT,               -- name-profile JSON
    meta_json     TEXT,               -- parser output JSON blob
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    deleted_at    TEXT,               -- NULL = present; set = soft-deleted
    PRIMARY KEY(volume_id, rel_path)
  );
  CREATE INDEX idx_files_hash    ON files(hash)       WHERE hash IS NOT NULL;
  CREATE INDEX idx_files_ext     ON files(ext);
  CREATE INDEX idx_files_deleted ON files(deleted_at) WHERE deleted_at IS NOT NULL;

  CREATE TABLE scans(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    volume_id     TEXT NOT NULL REFERENCES volumes(id),
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    root          TEXT NOT NULL,
    mode          TEXT NOT NULL,       -- 'quick' | 'full' | 'rehash'
    added         INTEGER DEFAULT 0,
    modified      INTEGER DEFAULT 0,
    deleted       INTEGER DEFAULT 0,
    unchanged     INTEGER DEFAULT 0
  );

  CREATE TABLE scan_files(
    scan_id       INTEGER NOT NULL REFERENCES scans(id),
    guid          TEXT NOT NULL,
    change        TEXT NOT NULL        -- 'added' | 'modified' | 'deleted' | 'unchanged'
  );
  ```
- WAL mode, `PRAGMA synchronous = NORMAL`, commit after each root.
- `locations.data.backend: "sqlite" | "pickle"` config key.
  Default `"sqlite"` on new configs; existing configs with a
  `.pickle` filename keep pickle read-only until migrated.
- New entry-point `migrate_pickle_to_sqlite.py --pickle <path>
  --sqlite <path>` — one-way, batches inserts inside a single
  transaction, prompts for the current volume id if it can't be
  probed automatically.

### Files

- **New:** `utils/utils_sqlite.py`, `migrate_pickle_to_sqlite.py`.
- **Modified:** `utils/utils_pickle.py` (route `get_data`/`save_data`
  by `locations.data.backend`), every entry-point (no change to
  callsites — they already use `get_data`/`save_data`).

### Expected result

- O(1) prior-record lookup regardless of catalogue size.
- Crash-safe: mid-scan power loss loses at most one root's records.
- Enables ad-hoc SQL reporting alongside `display_files.py`.

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

- Pass `prior=<sqlite proxy scoped to this volume>` when calling
  `scan_files(...)`.
- On `_unchanged=True`: bump `last_seen`, clear `deleted_at` if set,
  record `('unchanged', guid)` on the scan; skip index writes (the row
  is already in place).
- On new / modified: upsert the row, clear `deleted_at`, record
  `('added', guid)` or `('modified', guid)`.
- Track `seen_paths: set[str]` during the walk.
- **Soft delete pass**, after each root:
  ```sql
  UPDATE files
     SET deleted_at = :scan_started_at
   WHERE volume_id = :vol
     AND rel_path LIKE :scanpath_prefix
     AND deleted_at IS NULL
     AND rel_path NOT IN (seen_paths);
  ```
  Metadata, hash, guid are preserved so an audit trail exists.
  Insert `('deleted', guid)` rows into `scan_files` for the delta.
- The `scans` row is updated with `added / modified / deleted /
  unchanged` counters so `display_files.py` can show a per-scan delta
  report.

### Purge (separate, explicit)

- New entry-point `purge_files.py -cp <config>`. Reads
  `scanoptions.purge_deleted_after_months` (default `null` = never).
  If set, deletes rows where
  `deleted_at < date('now', printf('-%d months', :months))`. Prints a
  dry-run count unless `--yes` is passed.
- Never runs automatically as part of a scan (per your decision — a scan
  should never lose data on its own).

### Expected result

Second scan of an unchanged 200 k-file / 500 GB tree drops from **hours
to seconds**. Adds/modifies/deletes are surfaced as a delta report per
scan, and no data is discarded until you run a purge.

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

## Phase 3 — SHA1 only, larger buffer

**Problem.** `make_hash` currently computes MD5 **and** SHA1 for every
byte read, in 64 KB chunks. Doing both doubles CPU for no benefit; the
small buffer maximises syscall overhead on USB.

**Change (decided).**

- `make_hash(filepath, bufsize=4*1024*1024) -> str` — returns a SHA1
  hex string. MD5 is gone.
- The DB column is a single `hash TEXT` (SHA1 hex). No `hash_algo` column
  — locked to SHA1.
- `scanoptions.hashbuffer` added to the config schema (default
  `4194304`).

### Breaking change

Downstream code reading `f["hash"]["MD5"]` or `f["hash"]["SHA1"]` breaks.
Grep shows two call sites:

- `scan_files.py` (`f_old.get("hash", {}).get("SHA1", "")`) → replace
  with equality on the top-level `hash` string.
- `export_files.py` (`f.get("hash",{}).get("SHA1")`) → same.

Both are updated in this phase — no compatibility shim (per your Q3
decision).

### Migration

- The pickle→SQLite migrator (Phase 0) extracts `hash.SHA1` from legacy
  records and stores it as the new `hash` string. Records that only had
  MD5 lose the hash on migration; they'll get re-hashed on the next
  scan when their file is seen as changed.

### Expected result

For new/changed files, ≈ **2× faster** than status quo (single algo,
larger buffer, better USB throughput).

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

## Phase 6 — Cross-platform volume-aware keys

**Problem.** Absolute paths embed the drive letter / mount point. Mount
the same USB drive as `E:` today and `F:` next week (or `/media/ms/DISK`
on Linux) and the scanner sees every file as "new" and every prior record
as "deleted".

**Change (decided — cross-platform).**

- New module `utils/utils_volume.py` with a single entry:
  ```python
  def identify(path: str) -> dict:
      """Returns {id, id_source, label, mount_root}."""
  ```
  Implementations, tried in order:
  - **Windows** — `GetVolumeInformationW` via `ctypes` (already partially
    covered in `utils/utils_marshallwindows.py`). Returns
    `id_source="win-serial"`, `id` = 8-hex serial.
  - **Linux** — read `/proc/mounts` to find the mount root for `path`,
    then read `/dev/disk/by-uuid/*` symlinks (or shell out to `blkid`
    only if the sysfs read fails). Returns `id_source="linux-uuid"`.
  - **macOS** — `diskutil info -plist <mount>` and pull `VolumeUUID`.
    Returns `id_source="macos-uuid"`.
  - **Fallback (any OS)** — `os.stat(mount_root).st_dev` as a hex
    string, `id_source="st_dev"`. Ephemeral (changes across reboots) but
    keeps the schema uniform.
- The `volumes` table is populated on first sight (see Phase 0 schema).
  `id_source` is stored so a later pass can upgrade `st_dev` fallback
  records to the real UUID once available.
- Absolute paths on records become **relative to `mount_root`**, e.g.
  `Photos/2024/img.jpg` instead of `E:/Photos/2024/img.jpg`.

### Migration

- `migrate_pickle_to_sqlite.py` probes the current volume of each scan
  root; if the probe fails it prompts for a manual id (or accepts
  `--assume-volume <id>`).
- Records already in SQLite from an earlier phase get a `volume_id` of
  `"legacy"` until the drive is re-seen; the walker upgrades them
  in-place on next scan.

### Risk

- Linux permission on `/proc/mounts` and `/dev/disk/by-uuid/` — needs
  read access, usually fine for the mounting user.
- macOS `diskutil` is a shell-out with a variable-shape plist; parse
  defensively.
- Symlinks across filesystems: report the target's volume, not the
  link's.

### Expected result

Drive letter and mount-point changes are invisible on all three
platforms. Same drive plugged into a different machine is still
recognised.

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
- ~~**Startup — every entry-point** runs
  `logging.config.fileConfig('logging_config.ini', ...)` at import time.~~
  **Done in Phase 0** — the call moved into `if __name__ == "__main__":`
  on all five stages, so a stage can be imported without the ini.

Found while verifying Phase 0, **both now fixed** — full write-ups in
[defect-log.md](defect-log.md):

- ~~**Bug — `analyze_files.py`** iterates the `:ALL:` entry as though it
  held lists of parsers, so every `:ALL:` parser raised
  `'NameParser' object is not iterable` into the surrounding `except`
  and never ran.~~ **DEF-01, fixed** — normalised to a list, matching the
  guard the extension-keyed branch already had.
- ~~**Bug — `export_files.py`** builds `w_cols` from `w_fields`, which
  starts at `0`, so `w00` is always requested even when no record has a
  word-type profile part.~~ **DEF-02, fixed** — `f_fields` / `w_fields`
  now start at `-1`, so an unpopulated column is not requested.

Still open, logged while verifying the fixes: DEF-06
(`export_files.py` raises `UnboundLocalError` on an empty catalogue) and
DEF-07 (`analyze.allfiles.fields` is ignored, so `:ALL:` parsers receive
the full path rather than the named fields).

---

## Documentation updates required

Every phase above implies one or more documentation edits. Grouped by
file so the diff review is easy.

**Phase 0 is done**: the SQLite-backend, migration-script, record-shape,
backend-routing and logging-startup edits have landed in `CLAUDE.md`,
`documents/reference-architecture.md`, `documents/abb-catalogue.md`,
`documents/sbb-catalogue.md` (SBB-04 marked legacy; new SBB-17 and
SBB-20) and `documents/abb-sbb-traceability.md`. What is listed below is
what remains, and belongs to Phases 1–6. The root `README.md` rewrite
still waits on Phase 1, as planned.

### `CLAUDE.md`

- **Commands section** — add `python migrate_pickle_to_sqlite.py …`
  (Phase 0) and `python purge_files.py -cp <config>` (Phase 1).
  Document the config key `scanoptions.mode` (Phase 4).
- **Architecture section** — record shape gains `mtime_ns`, `ctime_ns`,
  `deleted_at`, `volume_id`, `rel_path`. `hash: {MD5, SHA1}` becomes a
  single SHA1 hex string. `data["files"]` is no longer a Python dict —
  it's a SQLite-backed proxy (Phase 0).
- **Conventions section** — add a note that `hash` is a SHA1 hex string
  (no MD5) and that catalogue keys are `(volume_id, rel_path)` not
  absolute paths.
- **Gotchas section** — remove the `dicom_parser.py`,
  `scan_files_gdb.py`, and `writer.save()` items as those cleanups land.
  Add: "quick mode does not compute hashes — run `--mode full` if you
  need SHA1 populated on new records."

### `documents/reference-architecture.md`

- **§3 Pipeline** — add "Quick vs Full mode" under Scan; add a
  **Purge** row for `purge_files.py`.
- **§4 Component view** — add `utils/utils_sqlite.py` and
  `utils/utils_volume.py`; add `migrate_pickle_to_sqlite.py` and
  `purge_files.py` to the entry-point layer.
- **§5 Canonical data model** — replace the pickle-centric section with
  the SQLite schema from Phase 0; explain the soft-delete /
  `deleted_at` field; explain volume-aware keys.
- **§6 Extension points** — SQLite is now the default backend; note
  that alternate backends (e.g. Neo4j via SBB-15) still route through
  the same public surface.
- **§7 Known constraints** — remove the pickle-race caveat (SQLite WAL
  handles it); add a "quick-mode does not detect content-only edits
  that preserve size and mtime" caveat.

### `documents/abb-catalogue.md`

- **ABB-01 Filesystem Traversal** — expand "Quality attributes":
  quick / full / rehash modes; delete detection with retention; parallel
  hashing of changed files.
- **ABB-02 Catalogue Store** — expand: SQLite is the default;
  volume-aware keying; soft delete with retention; incremental,
  crash-safe writes.
- **ABB-06** — mention delta reports (added / modified / deleted /
  unchanged counters per scan) as an output.
- Add **ABB-11 Change Detection & Retention** — soft delete, purge
  policy, delta reporting. Distinct from ABB-01 because retention
  policy applies regardless of how changes were spotted.

### `documents/sbb-catalogue.md`

- **SBB-01** — new `prior` parameter, new `mtime_ns`/`ctime_ns` fields,
  `mode` handling, `scandir`-based walker.
- **SBB-02** — soft-delete pass, `_unchanged` fast-path, delta counters
  written to `scans` row.
- **SBB-03** — remove "WIP" caveat once the local-init bug is fixed.
- **SBB-04 Pickle Catalogue Store** — mark as **legacy / read-only**;
  point at SBB-17 for the current default.
- **SBB-08i** — remove defect note once the class rename lands.
- **SBB-11** — remove `writer.save()` caveat once fixed; note that
  export now reads from SQLite.
- **SBB-16** — extend the example config: `mode`, `hashbuffer`,
  `hashworkers`, `purge_deleted_after_months`,
  `locations.data.backend`.
- **New — SBB-17 SQLite Catalogue Store** — `utils/utils_sqlite.py`,
  schema, WAL settings, incremental commit strategy, pointer to
  `migrate_pickle_to_sqlite.py`.
- **New — SBB-18 Volume Identifier** — `utils/utils_volume.py`, per-OS
  probes, fallback to `st_dev`, records the `id_source` used.
- **New — SBB-19 Purge Utility** — `purge_files.py`, dry-run default,
  reads `scanoptions.purge_deleted_after_months`.
- SBB-17 and **SBB-20** (pickle → SQLite migrator) are already written;
  SBB-18 and SBB-19 stay reserved for the phases above, so the next new
  building block takes SBB-21.

### `documents/abb-sbb-traceability.md`

- Update SBB-04 realisation of ABB-02 to note it is legacy read-only.
- Add SBB-17 → ABB-02.
- Add SBB-18 → ABB-01, ABB-02.
- Add SBB-19 → ABB-11 (new).
- If ABB-11 is added: SBB-01, SBB-02, SBB-17, SBB-19 realise it.

### `README.md` (root)

- Currently 14 lines and out of date. Rewrite once Phase 0 and Phase 1
  ship: overview, install, `scan → analyse → rule → export → display →
  purge` flow, config example including `mode` and
  `purge_deleted_after_months`.

---

## Suggested rollout order

1. ~~**Phase 0 — SQLite backend + migration script.**~~ **Done.**
   Everything else writes against this schema, so it landed first. The
   legacy pickle backend is still readable so
   `migrate_pickle_to_sqlite.py` has a source.
2. **Phase 1 (skip re-hash + soft delete) + Phase 2 (scandir/`mtime_ns`)
   + Phase 4 (quick/full mode).** All three share a walker rewrite —
   ship them together. Add `purge_files.py` in the same PR.
3. **Phase 3 (SHA1-only, 4 MB buffer).** Separate PR because it changes
   the `hash` field shape and touches every reader.
4. **Cleanups** (`dicom_parser.py` rename, `scan_files_gdb.py` init fix,
   `writer.save()` → `writer.close()`, deferred logging config). Any
   time; group with Phase 3 for convenience.
5. **Phase 6 (cross-platform volume keys).** Needs per-OS probing; keep
   isolated so it can be tested independently on Windows / Linux / macOS.
6. **Phase 5 (parallel hashing).** Optional. Measure Phase 3
   performance first — if repeat scans are already fast enough and full
   scans are I/O-bound at the drive limit, parallel hashing adds no
   value.

---

## Decisions (answered)

1. **Hash choice → SHA1 only.** MD5 is dropped. `hash` becomes
   `{"SHA1": "<hex>"}`. No BLAKE3/xxh3 in scope — revisit later if
   throughput on new/changed files becomes the bottleneck.
2. **Volume identification → best available, cross-platform.**
   Windows uses `GetVolumeInformationW` (serial number). Linux uses the
   filesystem UUID from `/proc/mounts` + `blkid`, falling back to the
   `st_dev` of the mount point. macOS uses `diskutil info -plist`
   (`VolumeUUID`), falling back to `st_dev`. Records store
   `volume: {id, id_source, label, first_seen, last_mount_path}` so
   consumers know which identifier they've got.
3. **Config compatibility → new behaviour on by default.** Fresh runs
   get quick-mode, single-SHA1, `mtime_ns`, delete-marking, etc. No
   silent-compatibility shims for MD5. The upfront doc pass (CLAUDE.md
   gotchas, ABB/SBB catalogues) lands with Phase 1.
4. **SQLite → in scope now.** Promoted from optional Phase 7 to
   **foundational Phase 0** — every later phase writes against the new
   schema, so we don't ship a pickle format we'll immediately migrate
   away from. Pickle backend stays available for reading legacy
   catalogues; a one-off `migrate_pickle_to_sqlite.py` script does the
   move.
5. **Deleted-file semantics → soft delete with retention.** Records are
   never dropped mid-scan. When a prior path is not seen on a scan we
   set `deleted_at = <scan timestamp>` and leave everything else
   (metadata, hash, guid) intact. Reappearance clears `deleted_at`. A
   purge is a separate operation controlled by
   `scanoptions.purge_deleted_after_months` (default `null` = never)
   and executed either at the end of a scan or by a new
   `purge_files.py` entry-point.
