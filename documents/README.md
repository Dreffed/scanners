# Documents

Reference material for the `scanners` toolkit. Files are organised by the TOGAF
building-block model — Architecture Building Blocks describe *what* a capability
does; Solution Building Blocks describe *how* it is implemented in this repo.

| File | Purpose |
| ---- | ------- |
| [reference-architecture.md](reference-architecture.md) | High-level overview: context, pipeline, component diagram, key data flows. Start here. |
| [abb-catalogue.md](abb-catalogue.md) | Architecture Building Blocks — technology-neutral capabilities the system provides. |
| [sbb-catalogue.md](sbb-catalogue.md) | Solution Building Blocks — the concrete Python modules, classes and configs that realise each ABB. |
| [abb-sbb-traceability.md](abb-sbb-traceability.md) | Matrix mapping every ABB to the SBBs that realise it, and back. |
| [changelist-scan-performance.md](changelist-scan-performance.md) | Phased plan to speed up scan/hash for USB HDDs. Phase 0 (SQLite catalogue) has shipped; Phases 1–6 are still proposals. |
| [defect-log.md](defect-log.md) | Known defects, fixed and open, with root cause and the SBB each belongs to. |

Update rules:

- New capability idea → add an ABB, then decide on an SBB when implementing.
- New parser / module / storage backend → add or update an SBB and link it back
  to the ABB(s) it realises in the traceability matrix.
- Keep IDs stable (`ABB-xx`, `SBB-xx`, `DEF-xx`); rename only by adding an alias
  line.
- Defect found → add a `DEF-xx` entry naming the SBB it belongs to. Keep the
  entry when it is fixed; change its status rather than deleting it.
