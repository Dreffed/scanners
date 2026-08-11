"""One-way migration of a legacy pickle catalogue into the SQLite catalogue.

    python migrate_pickle_to_sqlite.py -cp .\\config\\config_scanner_google.json
    python migrate_pickle_to_sqlite.py --pickle .\\data\\scan.pickle --sqlite .\\data\\scan.sqlite

Inserts are batched inside a single transaction, so an interrupted run leaves
the target untouched rather than half-populated.

Records that only ever carried an MD5 lose their hash (SHA1 is the only hash
the schema keeps); they are re-hashed the next time the file is seen as
changed. Every row is written against the volume id given by
``--assume-volume`` (default ``legacy``) — per-OS volume probing arrives with
Phase 6, which upgrades these rows in place when the drive is next seen.
"""
import logging
import os

from utils.utils_files import get_filename
from utils.utils_json import get_setup
from utils.utils_pickle import load_pickle
from utils.utils_sqlite import DEFAULT_VOLUME, SqliteCatalogue, record_to_row

logger = logging.getLogger(__name__)

BATCH = 5000

INSERT_SQL = """
INSERT INTO files(volume_id, rel_path, name, ext, size, mtime_ns, ctime_ns,
                  hash, guid, profile, meta_json, first_seen, last_seen, deleted_at)
VALUES(:volume_id, :rel_path, :name, :ext, :size, :mtime_ns, :ctime_ns,
       :hash, :guid, :profile, :meta_json, :first_seen, :last_seen, :deleted_at)
ON CONFLICT(volume_id, rel_path) DO UPDATE SET
     name=excluded.name, ext=excluded.ext, size=excluded.size,
     mtime_ns=excluded.mtime_ns, ctime_ns=excluded.ctime_ns,
     hash=excluded.hash, guid=excluded.guid, profile=excluded.profile,
     meta_json=excluded.meta_json, last_seen=excluded.last_seen,
     deleted_at=excluded.deleted_at
"""


def resolve_paths(config: dict, pickle_path: str = None, sqlite_path: str = None) -> tuple:
    """Work out the source pickle and target SQLite paths.

    Parameters
    ----------
    config: dict
        scanner config, used when a path is not given explicitly
    pickle_path: str
        explicit source path, overrides the config
    sqlite_path: str
        explicit target path, overrides the config

    Returns
    -------
    tuple
        (pickle_path, sqlite_path)

    """
    location = dict(config.get("locations", {}).get("data", {}))

    if not pickle_path:
        if not location:
            raise SystemExit("No --pickle given and no locations.data in the config.")
        pickle_path = get_filename(dict(location, ext=location.get("ext", ".pickle")))

    if not sqlite_path:
        base, _ = os.path.splitext(pickle_path)
        sqlite_path = base + ".sqlite"

    return pickle_path, sqlite_path


def migrate_files(catalogue: SqliteCatalogue, files: dict) -> int:
    """Copy the ``files`` dict into the catalogue, batching the inserts."""
    batch = []
    count = 0
    for filepath, record in files.items():
        if not isinstance(record, dict):
            logger.warning("Skipping non-dict record at {}".format(filepath))
            continue

        batch.append(record_to_row(filepath, record, catalogue.volume_id))
        if len(batch) >= BATCH:
            catalogue.connection.executemany(INSERT_SQL, batch)
            count += len(batch)
            logger.info("Migrated {} files...".format(count))
            batch = []

    if batch:
        catalogue.connection.executemany(INSERT_SQL, batch)
        count += len(batch)

    return count


def migrate_scans(catalogue: SqliteCatalogue, scans: list) -> int:
    """Copy the legacy scan history into the ``scans`` / ``scan_files`` tables."""
    count = 0
    for scan in scans:
        if not isinstance(scan, dict):
            logger.warning("Skipping non-dict scan record: {}".format(scan))
            continue
        catalogue["scans"].append(scan)
        count += 1
    return count


def process(pickle_path: str, sqlite_path: str, volume_id: str = DEFAULT_VOLUME) -> dict:
    """Run the migration.

    Parameters
    ----------
    pickle_path: str
        the legacy catalogue to read
    sqlite_path: str
        the SQLite catalogue to write
    volume_id: str
        volume id to record against every migrated row

    Returns
    -------
    dict
        counts of what was migrated

    """
    if not os.path.exists(pickle_path):
        raise SystemExit("Source pickle not found: {}".format(pickle_path))

    logger.info("Reading {}".format(pickle_path))
    data = load_pickle(pickle_path)
    files = data.get("files", {})
    scans = data.get("scans", [])
    logger.info("Found {} files and {} scans".format(len(files), len(scans)))

    catalogue = SqliteCatalogue(path=sqlite_path, volume_id=volume_id)
    try:
        # One transaction: an interrupted run leaves the target as it was.
        with catalogue.connection:
            migrated_files = migrate_files(catalogue, files)
            migrated_scans = migrate_scans(catalogue, scans)
    finally:
        catalogue.close()

    result = {"files": migrated_files, "scans": migrated_scans, "volume": volume_id}
    logger.info(
        "Migrated {files} files and {scans} scans into {path} (volume '{volume}')".format(
            path=sqlite_path, **result
        )
    )
    return result


if __name__ == "__main__":
    import logging.config
    logging.config.fileConfig('logging_config.ini', disable_existing_loggers=False)
    logger.info("Running Pickle to SQLite migration...")

    from argparse import ArgumentParser
    argparser = ArgumentParser(
        prog="migratepickle",
        description="migrates a legacy pickle catalogue into the SQLite catalogue")

    argparser.add_argument('-cp', '--config_path',
        dest="config_path",
        help="The name or path for the config file to use.",
        default=r".\config\config_scanner_google.json")

    argparser.add_argument('--pickle',
        dest="pickle_path",
        help="Source pickle path. Defaults to locations.data from the config.",
        default=None)

    argparser.add_argument('--sqlite',
        dest="sqlite_path",
        help="Target SQLite path. Defaults to the source path with a .sqlite extension.",
        default=None)

    argparser.add_argument('--assume-volume',
        dest="volume",
        help="Volume id to record against migrated rows.",
        default=DEFAULT_VOLUME)

    argparser.add_argument('-v', '--version',
        action='version',
        version='%(prog)s 1.0')

    args = argparser.parse_args()
    config = get_setup(filename=args.config_path) or {}
    source, target = resolve_paths(config, args.pickle_path, args.sqlite_path)
    process(pickle_path=source, sqlite_path=target, volume_id=args.volume)
