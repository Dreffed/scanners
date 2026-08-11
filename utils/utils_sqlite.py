"""SQLite-backed catalogue store.

Public surface mirrors :mod:`utils.utils_pickle` — ``get_data(config)`` returns a
catalogue proxy and ``save_data(data, config)`` flushes it. Unlike the pickle
store the catalogue is never held in memory in full: ``data["files"]`` is a
SQLite-backed mapping, and the ``exts`` / ``filenames`` / ``hashes`` / ``guids``
indexes are derived by query rather than maintained by hand.

Record round-trip
-----------------
Columns carry the fields the scanner queries on (``ext``, ``size``,
``mtime_ns``, ``hash``, ``guid``, ...); everything else on a record — the
``folders`` list, ``bytes``, parser output such as ``"words.metadata"``, tag
dicts written by ``run_rules.py`` — is JSON-encoded into ``meta_json``.

The ``hash`` column is a single SHA1 hex string (Phase 3 decision). Until that
phase lands, records are rehydrated as ``{"SHA1": <hex>}`` so existing readers
keep working; ``_hash_to_column`` accepts either shape on the way in.

Keys are ``(volume_id, rel_path)``. Volume probing arrives in Phase 6, so until
then every row is written against ``DEFAULT_VOLUME`` and ``rel_path`` holds the
absolute path exactly as the pickle store did.
"""
import json
import logging
import os
import sqlite3
from collections.abc import Mapping, MutableMapping
from datetime import datetime

from utils.utils_files import get_filename

logger = logging.getLogger(__name__)

DEFAULT_VOLUME = "legacy"
"""Volume id used until Phase 6 lands real per-OS volume probing."""

AUTOFLUSH = 2000
"""Dirty records buffered before an implicit flush."""

PAGE_SIZE = 1000
"""Rows fetched per keyset page when iterating the files table."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS volumes(
  id            TEXT PRIMARY KEY,
  id_source     TEXT NOT NULL,
  label         TEXT,
  first_seen    TEXT NOT NULL,
  last_mount    TEXT
);

CREATE TABLE IF NOT EXISTS files(
  volume_id     TEXT NOT NULL REFERENCES volumes(id),
  rel_path      TEXT NOT NULL,
  name          TEXT,
  ext           TEXT,
  size          INTEGER,
  mtime_ns      INTEGER,
  ctime_ns      INTEGER,
  hash          TEXT,
  guid          TEXT NOT NULL,
  profile       TEXT,
  meta_json     TEXT,
  first_seen    TEXT NOT NULL,
  last_seen     TEXT NOT NULL,
  deleted_at    TEXT,
  PRIMARY KEY(volume_id, rel_path)
);
CREATE INDEX IF NOT EXISTS idx_files_hash    ON files(hash)       WHERE hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_files_ext     ON files(ext);
CREATE INDEX IF NOT EXISTS idx_files_name    ON files(name);
CREATE INDEX IF NOT EXISTS idx_files_guid    ON files(guid);
CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(deleted_at) WHERE deleted_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS scans(
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  volume_id     TEXT NOT NULL REFERENCES volumes(id),
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  root          TEXT NOT NULL,
  mode          TEXT NOT NULL,
  added         INTEGER DEFAULT 0,
  modified      INTEGER DEFAULT 0,
  deleted       INTEGER DEFAULT 0,
  unchanged     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scan_files(
  scan_id       INTEGER NOT NULL REFERENCES scans(id),
  guid          TEXT NOT NULL,
  change        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scan_files_scan ON scan_files(scan_id);
"""

# Record keys that live in their own column rather than in meta_json.
COLUMN_KEYS = frozenset(
    ("name", "ext", "size", "mtime_ns", "ctime_ns", "hash", "guid", "profile",
     "first_seen", "last_seen", "deleted_at")
)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _hash_to_column(value):
    """Normalise a record ``hash`` to the single SHA1 hex string the column holds.

    Accepts the legacy ``{"MD5": ..., "SHA1": ...}`` dict or a bare string.
    Records that only ever had an MD5 lose the hash (Phase 3 decision) and get
    re-hashed the next time the file is seen as changed.
    """
    if not value:
        return None
    if isinstance(value, dict):
        return value.get("SHA1") or None
    return str(value)


def _hash_to_record(value):
    """Rehydrate the ``hash`` column into the record shape readers expect."""
    if not value:
        return None
    return {"SHA1": value}


def _json_loads(text, default=None):
    if not text:
        return default
    try:
        return json.loads(text)
    except ValueError as ex:
        logger.error("Corrupt JSON in catalogue row: {}".format(ex))
        return default


def record_to_row(rel_path, record, volume_id, now=None):
    """Flatten a scanner record into the ``files`` column tuple."""
    now = now or _now()
    meta = {k: v for k, v in record.items() if k not in COLUMN_KEYS}
    return {
        "volume_id": volume_id,
        "rel_path": rel_path,
        "name": record.get("name") or os.path.basename(rel_path),
        "ext": record.get("ext"),
        "size": record.get("size"),
        "mtime_ns": record.get("mtime_ns"),
        "ctime_ns": record.get("ctime_ns"),
        "hash": _hash_to_column(record.get("hash")),
        "guid": record.get("guid") or "",
        "profile": json.dumps(record.get("profile")) if record.get("profile") else None,
        "meta_json": json.dumps(meta, default=str) if meta else None,
        "first_seen": record.get("first_seen") or now,
        "last_seen": record.get("last_seen") or now,
        "deleted_at": record.get("deleted_at"),
    }


def row_to_record(row):
    """Rehydrate a ``files`` row into the record shape the pipeline expects."""
    record = _json_loads(row["meta_json"], {}) or {}
    record["ext"] = row["ext"]
    record["size"] = row["size"]
    record["guid"] = row["guid"]
    record["first_seen"] = row["first_seen"]
    record["last_seen"] = row["last_seen"]

    if row["mtime_ns"] is not None:
        record["mtime_ns"] = row["mtime_ns"]
    if row["ctime_ns"] is not None:
        record["ctime_ns"] = row["ctime_ns"]
    if row["hash"]:
        record["hash"] = _hash_to_record(row["hash"])
    if row["profile"]:
        record["profile"] = _json_loads(row["profile"])
    if row["deleted_at"]:
        record["deleted_at"] = row["deleted_at"]
    return record


class FileRecord(dict):
    """A file record that marks itself dirty on the owning view when mutated.

    ``analyze_files.py`` and ``run_rules.py`` both mutate the record in place and
    rely on a later save to persist it. Tracking writes here keeps that pattern
    working without touching those callsites.
    """

    def __init__(self, view, key, data):
        super().__init__(data)
        self._view = view
        self._key = key

    def _touch(self):
        if self._view is not None:
            self._view.mark_dirty(self._key, self)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._touch()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._touch()

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        self._touch()

    def setdefault(self, key, default=None):
        missing = key not in self
        value = super().setdefault(key, default)
        if missing:
            self._touch()
        return value

    def pop(self, *args):
        value = super().pop(*args)
        self._touch()
        return value


class FilesView(MutableMapping):
    """Mapping of ``rel_path`` -> record, backed by the ``files`` table.

    Soft-deleted rows (``deleted_at IS NOT NULL``) are hidden from iteration and
    ``__len__`` but remain reachable through :meth:`get_deleted` so Phase 1's
    delete pass can resurrect them.
    """

    def __init__(self, catalogue):
        self._cat = catalogue
        self._dirty = {}

    # -- write buffering -------------------------------------------------
    def mark_dirty(self, key, record):
        self._dirty[key] = record
        if len(self._dirty) >= AUTOFLUSH:
            self.flush()

    def flush(self):
        if not self._dirty:
            return 0
        now = _now()
        rows = [record_to_row(k, v, self._cat.volume_id, now) for k, v in self._dirty.items()]
        self._cat.connection.executemany(
            """INSERT INTO files(volume_id, rel_path, name, ext, size, mtime_ns,
                                 ctime_ns, hash, guid, profile, meta_json,
                                 first_seen, last_seen, deleted_at)
               VALUES(:volume_id, :rel_path, :name, :ext, :size, :mtime_ns,
                      :ctime_ns, :hash, :guid, :profile, :meta_json,
                      :first_seen, :last_seen, :deleted_at)
               ON CONFLICT(volume_id, rel_path) DO UPDATE SET
                    name=excluded.name, ext=excluded.ext, size=excluded.size,
                    mtime_ns=excluded.mtime_ns, ctime_ns=excluded.ctime_ns,
                    hash=excluded.hash, guid=excluded.guid,
                    profile=excluded.profile, meta_json=excluded.meta_json,
                    last_seen=excluded.last_seen, deleted_at=excluded.deleted_at""",
            rows,
        )
        count = len(rows)
        self._dirty.clear()
        logger.debug("Flushed {} file records".format(count))
        return count

    # -- MutableMapping --------------------------------------------------
    def _fetch(self, key, include_deleted=False):
        sql = "SELECT * FROM files WHERE volume_id = ? AND rel_path = ?"
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        cur = self._cat.connection.execute(sql, (self._cat.volume_id, key))
        return cur.fetchone()

    def __getitem__(self, key):
        if key in self._dirty:
            return self._dirty[key]
        row = self._fetch(key)
        if row is None:
            raise KeyError(key)
        return FileRecord(self, key, row_to_record(row))

    def get_deleted(self, key, default=None):
        """Look up a record ignoring its soft-delete marker."""
        row = self._fetch(key, include_deleted=True)
        if row is None:
            return default
        return FileRecord(self, key, row_to_record(row))

    def __setitem__(self, key, value):
        record = value if isinstance(value, FileRecord) else FileRecord(self, key, value)
        record._view, record._key = self, key
        self.mark_dirty(key, record)

    def __delitem__(self, key):
        """Hard delete. Phase 1 adds the soft-delete pass; this stays as the
        escape hatch for a caller that really wants the row gone."""
        buffered = self._dirty.pop(key, None) is not None
        cur = self._cat.connection.execute(
            "DELETE FROM files WHERE volume_id = ? AND rel_path = ?",
            (self._cat.volume_id, key),
        )
        if cur.rowcount == 0 and not buffered:
            raise KeyError(key)

    def __contains__(self, key):
        if key in self._dirty:
            return True
        return self._fetch(key) is not None

    def __iter__(self):
        for key, _ in self.items():
            yield key

    def __len__(self):
        self.flush()
        cur = self._cat.connection.execute(
            "SELECT COUNT(*) FROM files WHERE volume_id = ? AND deleted_at IS NULL",
            (self._cat.volume_id,),
        )
        return cur.fetchone()[0]

    def items(self):
        """Stream records in ``rel_path`` order.

        Paged with a keyset cursor rather than one big SELECT so a caller can
        mutate and flush records mid-iteration (``analyze_files.py`` saves every
        5 %) without holding an open cursor over the rows it is rewriting.
        """
        self.flush()
        last = ""
        while True:
            rows = self._cat.connection.execute(
                """SELECT * FROM files
                    WHERE volume_id = ? AND deleted_at IS NULL AND rel_path > ?
                    ORDER BY rel_path LIMIT ?""",
                (self._cat.volume_id, last, PAGE_SIZE),
            ).fetchall()
            if not rows:
                return
            for row in rows:
                last = row["rel_path"]
                yield last, FileRecord(self, last, row_to_record(row))

    def values(self):
        for _, record in self.items():
            yield record

    def keys(self):
        return iter(self)


class IndexView(Mapping):
    """Read-only inverted index derived from the ``files`` table by query.

    The pickle store maintained ``exts`` / ``filenames`` / ``hashes`` / ``guids``
    as hand-built dicts that could drift out of step with ``files``. Here they
    are always a query away, so they cannot drift.
    """

    def __init__(self, catalogue, key_expr, value_expr, where=""):
        self._cat = catalogue
        self._key = key_expr
        self._value = value_expr
        self._where = where

    def _clause(self):
        sql = "FROM files WHERE volume_id = ? AND deleted_at IS NULL"
        if self._where:
            sql += " AND " + self._where
        return sql

    def __getitem__(self, key):
        rows = self._cat.connection.execute(
            "SELECT {} AS v {} AND {} = ?".format(self._value, self._clause(), self._key),
            (self._cat.volume_id, key),
        ).fetchall()
        if not rows:
            raise KeyError(key)
        return [r["v"] for r in rows]

    def __iter__(self):
        rows = self._cat.connection.execute(
            "SELECT DISTINCT {} AS k {}".format(self._key, self._clause()),
            (self._cat.volume_id,),
        )
        for row in rows:
            yield row["k"]

    def __len__(self):
        cur = self._cat.connection.execute(
            "SELECT COUNT(DISTINCT {}) {}".format(self._key, self._clause()),
            (self._cat.volume_id,),
        )
        return cur.fetchone()[0]

    def items(self):
        rows = self._cat.connection.execute(
            "SELECT {} AS k, group_concat({}, char(31)) AS vs {} GROUP BY k".format(
                self._key, self._value, self._clause()
            ),
            (self._cat.volume_id,),
        )
        for row in rows:
            yield row["k"], (row["vs"] or "").split("\x1f")


class ScansView:
    """List-like view over the ``scans`` table.

    ``scan_files.py`` currently appends a legacy scan dict
    (``{"scandate", "files": [guid], "basepaths": [path]}``); that shape is
    mapped onto the new columns here. Phase 1 replaces it with explicit
    added/modified/deleted/unchanged counters.
    """

    def __init__(self, catalogue):
        self._cat = catalogue

    def append(self, scan):
        conn = self._cat.connection
        basepaths = scan.get("basepaths") or []
        cur = conn.execute(
            """INSERT INTO scans(volume_id, started_at, finished_at, root, mode,
                                 added, modified, deleted, unchanged)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self._cat.volume_id,
                scan.get("scandate") or scan.get("started_at") or _now(),
                scan.get("finished_at") or _now(),
                basepaths[0] if basepaths else scan.get("root", ""),
                scan.get("mode", "full"),
                scan.get("added", len(scan.get("files", []))),
                scan.get("modified", 0),
                scan.get("deleted", 0),
                scan.get("unchanged", 0),
            ),
        )
        scan_id = cur.lastrowid
        changes = scan.get("changes")
        if changes is None:
            changes = [(guid, "added") for guid in scan.get("files", [])]
        if changes:
            conn.executemany(
                "INSERT INTO scan_files(scan_id, guid, change) VALUES(?, ?, ?)",
                [(scan_id, guid, change) for guid, change in changes],
            )
        return scan_id

    def _row_to_scan(self, row):
        guids = self._cat.connection.execute(
            "SELECT guid FROM scan_files WHERE scan_id = ?", (row["id"],)
        ).fetchall()
        return {
            "id": row["id"],
            "scandate": row["started_at"],
            "finished_at": row["finished_at"],
            "mode": row["mode"],
            "basepaths": [row["root"]],
            "added": row["added"],
            "modified": row["modified"],
            "deleted": row["deleted"],
            "unchanged": row["unchanged"],
            "files": [g["guid"] for g in guids],
        }

    def __iter__(self):
        rows = self._cat.connection.execute(
            "SELECT * FROM scans WHERE volume_id = ? ORDER BY id", (self._cat.volume_id,)
        ).fetchall()
        for row in rows:
            yield self._row_to_scan(row)

    def __len__(self):
        cur = self._cat.connection.execute(
            "SELECT COUNT(*) FROM scans WHERE volume_id = ?", (self._cat.volume_id,)
        )
        return cur.fetchone()[0]

    def __getitem__(self, idx):
        rows = list(self)
        return rows[idx]


class SqliteCatalogue:
    """Dict-like catalogue: ``data["files"]``, ``data["exts"]``, ``data["scans"]``, ...

    Stands in for the dict the pickle store returned, so the pipeline stages do
    not need to know which backend they are talking to.
    """

    VIEWS = ("files", "exts", "filenames", "hashes", "guids", "scans")

    derived_indexes = True
    """The inverted indexes are queries, so callers must not maintain them."""

    def __init__(self, path, volume_id=DEFAULT_VOLUME):
        self.path = path
        self.volume_id = volume_id
        folder = os.path.dirname(os.path.abspath(path))
        if folder and not os.path.exists(folder):
            os.makedirs(folder)

        logger.info("Opening SQLite catalogue... [{}]".format(path))
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = NORMAL")
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)

        self._files = FilesView(self)
        self._views = {
            "files": self._files,
            "exts": IndexView(self, "lower(ext)", "guid"),
            "filenames": IndexView(self, "name", "guid"),
            "hashes": IndexView(self, "hash", "guid", where="hash IS NOT NULL"),
            "guids": IndexView(self, "guid", "rel_path"),
            "scans": ScansView(self),
        }
        self.ensure_volume(volume_id)

    def ensure_volume(self, volume_id, id_source="legacy", label=None, mount=None):
        """Register a volume if it is not already known, and stamp ``last_mount``."""
        self.connection.execute(
            """INSERT INTO volumes(id, id_source, label, first_seen, last_mount)
               VALUES(?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                    last_mount = COALESCE(excluded.last_mount, volumes.last_mount)""",
            (volume_id, id_source, label, _now(), mount),
        )
        self.connection.commit()

    # -- mapping surface -------------------------------------------------
    def __getitem__(self, key):
        return self._views[key]

    def __setitem__(self, key, value):
        """Accept the pipeline's ``data["files"] = files`` write-back.

        Re-assigning the same view is the common case and needs no work. The
        derived indexes cannot be assigned — they are queries, not stored dicts.
        """
        if key in self._views and value is self._views[key]:
            return
        if key in self.VIEWS:
            logger.warning(
                "Ignoring assignment to derived catalogue view '{}' "
                "(SQLite backend keeps indexes in sync by query)".format(key)
            )
            return
        raise KeyError("Unknown catalogue key: {}".format(key))

    def __contains__(self, key):
        return key in self._views

    def __len__(self):
        return len(self._views)

    def get(self, key, default=None):
        return self._views.get(key, default)

    def keys(self):
        return self._views.keys()

    def items(self):
        return self._views.items()

    def values(self):
        return self._views.values()

    # -- lifecycle -------------------------------------------------------
    def flush(self):
        """Persist buffered records and commit."""
        self._files.flush()
        self.connection.commit()

    def close(self):
        self.flush()
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def get_data(config=None):
    """Open the catalogue named by ``locations.data`` in *config*."""
    config = config or {}
    location = config.get("locations", {}).get("data", {})
    volume = location.get("volume", DEFAULT_VOLUME)
    return SqliteCatalogue(path=get_filename(location), volume_id=volume)


def save_data(data, config=None):
    """Flush the catalogue.

    Writes are committed incrementally, so this only has to drain the buffer —
    but it is kept on the public surface so the pipeline stages can stay
    backend-agnostic.
    """
    if isinstance(data, SqliteCatalogue):
        data.flush()
    else:
        logger.warning("save_data called with a non-SQLite catalogue: {}".format(type(data)))
