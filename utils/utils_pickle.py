"""Catalogue access for the pipeline stages.

``get_data`` / ``save_data`` are the only entry points the pipeline stages
should use. They route to a backend chosen by ``locations.data.backend``:

* ``"sqlite"`` (default) — :mod:`utils.utils_sqlite`, the current store.
* ``"pickle"`` — the legacy store, **read-only**. Run
  ``migrate_pickle_to_sqlite.py`` to move an existing catalogue across, or set
  ``locations.data.readonly: false`` to keep writing to it for now.

When ``backend`` is absent it is inferred from the configured extension, so
existing ``.pickle`` configs keep loading without an edit.
"""
import pickle
import os

from utils.utils_files import get_filename
from utils import utils_sqlite

import logging

logger = logging.getLogger(__name__)

PICKLE_EXTS = (".pickle", ".pkl")


class CatalogueReadOnlyError(RuntimeError):
    """Raised when a write is attempted against the legacy pickle backend."""


def load_pickle(filename):
    data = {}
    if os.path.exists(filename):
        logger.info('Loading Saved Data... [%s]' % filename)
        with open(filename, 'rb') as handle:
            data = pickle.load(handle)
    return data

def save_pickle(data, filename):
    logger.info('Saving Data... [%s]' % filename)
    with open(filename, 'wb') as handle:
        pickle.dump(data, handle)

def get_backend(config: dict = {}) -> str:
    """Return the catalogue backend named (or implied) by *config*.

    Parameters
    ----------
    config: dict
        the scanner config; ``locations.data.backend`` wins, otherwise the
        backend is inferred from ``locations.data.ext``.

    Returns
    -------
    str
        ``"sqlite"`` or ``"pickle"``

    """
    location = config.get("locations", {}).get("data", {})
    backend = location.get("backend")
    if backend:
        return backend.strip().lower()

    ext = (location.get("ext") or "").strip().lower()
    if ext in PICKLE_EXTS:
        return "pickle"
    return "sqlite"

def derives_indexes(data) -> bool:
    """Whether the catalogue maintains its own inverted indexes.

    Parameters
    ----------
    data: dict
        a catalogue returned by :func:`get_data`

    Returns
    -------
    bool
        ``True`` for SQLite (``exts`` / ``filenames`` / ``hashes`` / ``guids``
        are derived by query), ``False`` for the pickle dict, whose caller has
        to build them by hand.

    """
    return bool(getattr(data, "derived_indexes", False))

def get_data(config: dict = {}) -> dict:
    """Open the catalogue for *config*.

    Parameters
    ----------
    config: dict
        the scanner config

    Returns
    -------
    dict
        the pickle dict for the pickle backend, or a
        :class:`~utils.utils_sqlite.SqliteCatalogue` proxy for SQLite. Both
        support ``data.get("files")``, ``data.get("exts")`` and friends.

    """
    if get_backend(config) == "pickle":
        logger.warning(
            "Reading the legacy pickle catalogue. Run migrate_pickle_to_sqlite.py "
            "to move to the SQLite backend."
        )
        return load_pickle(get_filename(config.get("locations", {}).get("data", {})))

    return utils_sqlite.get_data(config=config)

def save_data(data: dict, config: dict) -> None:
    """Persist the catalogue for *config*.

    Parameters
    ----------
    data: dict
        the catalogue returned by :func:`get_data`
    config: dict
        the scanner config

    Returns
    -------
    None

    Raises
    ------
    CatalogueReadOnlyError
        when the pickle backend is selected and ``locations.data.readonly`` has
        not been set to ``false``.

    """
    if get_backend(config) == "pickle":
        location = config.get("locations", {}).get("data", {})
        if location.get("readonly", True):
            raise CatalogueReadOnlyError(
                "The pickle catalogue is read-only. Migrate it with "
                "'python migrate_pickle_to_sqlite.py -cp <config>', or set "
                "locations.data.readonly to false to keep writing pickle."
            )
        save_pickle(data=data, filename=get_filename(location))
        return

    utils_sqlite.save_data(data=data, config=config)
