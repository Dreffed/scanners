# Defect Log

Known defects in `scanners`, fixed and open. One entry per defect: what you
would observe, why it happens, and what was done about it. Entries stay in the
log after they are fixed — a silent defect that ran for years is worth
remembering, and the SBB it belongs to is the fastest way back to the code.

Open defects are also summarised in the root `CLAUDE.md` "Gotchas" section.
Cross-reference: [sbb-catalogue.md](sbb-catalogue.md).

| ID | Component | Summary | Status |
| -- | --------- | ------- | ------ |
| [DEF-01](#def-01) | SBB-07 `analyze_files.py` | `:ALL:` parsers never ran | **Fixed** |
| [DEF-02](#def-02) | SBB-11 `export_files.py` | Export crashed on all-lowercase filenames | **Fixed** |
| [DEF-03](#def-03) | SBB-03 `scan_files_gdb.py` | Uninitialised locals — `NameError` on first file | Open |
| [DEF-04](#def-04) | SBB-08i `parsers/dicom_parser.py` | Class misnamed, parser never registered | Open |
| [DEF-05](#def-05) | SBB-11 `export_files.py` | `writer.save()` removed in pandas 2.x | Open |
| [DEF-06](#def-06) | SBB-11 `export_files.py` | `UnboundLocalError` on an empty catalogue | Open |
| [DEF-07](#def-07) | SBB-07 `analyze_files.py` | `analyze.allfiles.fields` is ignored | Open |

---

## DEF-01

**`:ALL:` parsers never ran.** Fixed.

- **Component**: SBB-07 Analyse Orchestrator (`analyze_files.py`).
- **Symptom**: every file logged
  `'NameParser' object is not iterable` at ERROR, then analysis carried on.
  No `:ALL:` parser output — `names.metadata` in the stock config — was ever
  written to a record.
- **Root cause**: `functions[":ALL:"]` holds parser *instances*, but the
  dispatch loop treated each entry as a list of parsers:

  ```python
  for cls_list in functions.get(":ALL:", []):
      for cls in cls_list:          # cls_list is a NameParser, not a list
  ```

  The `TypeError` was caught by the broad `except Exception` wrapping the
  per-file body, which logs and moves on — so the pipeline looked healthy
  and simply produced nothing.
- **Why it went unnoticed**: `scan_files.py` attaches its own `profile` to
  every record via `utils_rules.profile()`, so the field the `:ALL:` parser
  was supposed to produce appeared to be present.
- **Fix**: normalise the entry to a list first, matching the guard the
  extension-keyed branch immediately above already had:

  ```python
  for cls_list in functions.get(":ALL:", []):
      if not isinstance(cls_list, list):
          cls_list = [cls_list]
  ```
- **Verified**: analysis over a two-file tree with `NameParser` active now
  persists exactly `{"names.metadata"}` with a populated profile.
- **Note**: `NameParser.get_metadata` receives the full `filepath`, so the
  profile it returns covers the whole path, not just the filename. That is
  existing behaviour and differs from the record's own `profile` field —
  see DEF-07.

## DEF-02

**Export crashed on all-lowercase filenames.** Fixed.

- **Component**: SBB-11 Excel Exporter (`export_files.py`).
- **Symptom**: `KeyError: "['w00'] not in index"` from `df = df[df_cols]`.
  Reproducible on any collection where no filename yields a word-type
  profile part (types `W`, `U`, `N`, `B`) — for example a tree of
  `a.txt`, `b.md`, `notes.pdf`.
- **Root cause**: `w_fields` (and `f_fields`) tracked the highest populated
  column index but started at `0` rather than `-1`, so
  `range(0, w_fields + 1)` always requested `w00` even when no row had one.
  The same latent bug applied to `f00` for records with no `folders`.
- **Fix**: initialise both counters to `-1`, so "nothing populated" produces
  an empty column list.
- **Verified**: an all-lowercase tree now exports with no `w` columns and no
  crash; a mixed-case tree still gets `w00`/`w01` as before.

## DEF-03

**`scan_files_gdb.py` uses uninitialised locals.** Open.

- **Component**: SBB-03 Scan Orchestrator (Neo4j).
- **Symptom**: `NameError` on the first file scanned.
- **Cause**: references `files`, `exts`, `filenames`, `hashes`, `guids`
  without defining them in scope — a partial migration to Neo4j.
- **Blocks**: any Neo4j-backed run. Fix or delete before using.

## DEF-04

**DICOM parser is never registered.** Open.

- **Component**: SBB-08i (`parsers/dicom_parser.py`).
- **Symptom**: no DICOM file is ever parsed; no error is raised.
- **Cause**: the class is named `BaseParser`. `parser_loader` only collects
  classes matching `.+parser$`, so it is silently skipped.
- **Fix**: rename the class to `DicomParser`.

## DEF-05

**`writer.save()` is removed in pandas 2.x.** Open.

- **Component**: SBB-11 (`export_files.py`).
- **Symptom**: `AttributeError` on export after upgrading past pandas 2.0.
  Harmless on the pinned pandas 1.4.2, where it is merely deprecated.
- **Fix**: use `with pd.ExcelWriter(...) as writer:` or call
  `writer.close()`.

## DEF-06

**Export raises `NameError` on an empty catalogue.** Open.

- **Component**: SBB-11 (`export_files.py`).
- **Symptom**: `UnboundLocalError: cannot access local variable 'df_cols'`
  when the catalogue has no file records. Reproduced against an empty
  SQLite catalogue.
- **Cause**: `df_cols` is assigned inside the per-record loop, so it does not
  exist when the loop body never runs.
- **Fix**: seed the core column list before the loop instead of deriving it
  from the last row.

## DEF-07

**`analyze.allfiles.fields` is ignored.** Open.

- **Component**: SBB-07 (`analyze_files.py`).
- **Symptom**: none visible — but the config key implies the `:ALL:` parser
  is fed the named record fields (`["file"]` in the stock config), while the
  dispatch always passes `filepath`. `NameParser` therefore profiles the
  whole absolute path, including drive and folders.
- **Decide before fixing**: whether `fields` should be honoured, or removed
  from the config schema as a design that was never adopted. Honouring it
  changes the shape of every `names.metadata` value already stored.
