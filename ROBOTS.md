# ROBOTS.md — AI agent orientation

This file describes **repository structure**, **runtime contracts**, and **safe extension points** for automated coding agents. The project was designed to be completed and maintained with AI assistance; treat this document as the canonical map when planning changes.

---

## Product intent

- **Inputs:** GPX track (lat/lon/elevation), backpack weight (lb), max hiking speed (mph).  
- **Outputs:** Per-segment recommended speed, pace zones, CSV + GeoJSON + HTML map artifacts.  
- **Surfaces:** `app.py` (Flask) and `hiking_optimizer_backend.py` (CLI) both call `hiking_optimizer.pipeline.run_backend_job`.

---

## High-level data flow

```
GPX file
  → gpx_parser.parse_gpx_points / build_segments
  → model.load_or_train_pace_model + segment_features → speeds (capped)
  → zones (quantile labels + merge_short_zone_runs)
  → exporters (CSV, GeoJSON, HTML)
  → disk + HTTP (web) or disk only (CLI)
```

Do not bypass `run_backend_job` for product behavior unless you intentionally fork the pipeline.

---

## Directory tree (authoritative)

```
.
├── app.py                      # Flask: /, /optimize, /artifacts/<run_id>/<file>, PDF route if Playwright present
├── hiking_optimizer_backend.py # argparse CLI → run_backend()
├── hiking_optimizer/           # importable package (core logic)
│   ├── __init__.py             # exports run_backend, run_backend_job
│   ├── constants.py            # GPX_NS, unit conversions
│   ├── types.py                # TrackPoint, Segment, Zone dataclasses
│   ├── gpx_parser.py           # ET parse, haversine segments, optional trail naming
│   ├── model.py                # synthetic training, LinearRegressionGD, pace_model.json I/O, PACE_MODEL_SPEC_VERSION
│   ├── zones.py                # classify_pace_zone, quantile refinement, merge_short_zone_runs, summarize_zones, ZONE_COLORS
│   ├── exporters.py            # write_csv, write_geojson, write_html_map (Leaflet; f-string → double {{ }} in embedded JS)
│   ├── pipeline.py             # run_backend_job orchestration; run_backend prints CLI summary
│   └── pace_model.json         # committed cache of fitted weights (invalid if spec_version mismatch)
├── templates/
│   └── index.html              # Web form + map iframe + PDF controls
├── tests/                      # pytest: unit + integration + Flask client
├── GPX_Files/                  # sample GPX (not required at runtime except demos)
├── outputs/                    # typical CLI output dir (may exist locally; not always gitignored)
├── web_runs/                   # per-upload run dirs from Flask (gitignored)
├── requirements.txt            # Flask, gunicorn, playwright pin
├── requirements-dev.txt        # -r requirements.txt + pytest
├── render.yaml                 # Render build/start (2 workers, playwright chromium)
├── pytest.ini
├── README.md                   # human install + usage
└── ROBOTS.md                   # this file


## Entry points (do not duplicate business logic)

| Entry | Calls | Notes |
|-------|--------|--------|
| `python app.py` | `run_backend_job(..., out_dir=web_runs/<id>)` | Serves artifacts from `web_runs/`. |
| `python hiking_optimizer_backend.py` | `run_backend(...)` → `run_backend_job` | Writes to `--out-dir`. |
| `pytest` | imports under `tests/` | Use `requirements-dev.txt`. |

**Rule:** New features that affect optimization or artifacts should live under `hiking_optimizer/` and be invoked from `pipeline.py` (and tests), not reimplemented in `app.py`.

---

## Important contracts

### GPX

- Namespace: GPX 1.1 (`hiking_optimizer.constants.GPX_NS`).  
- Track points: `trkpt` with `lat`, `lon`, and `ele` child required for inclusion.  
- Segments skip near-duplicate consecutive points (very small horizontal distance) to avoid insane grades.

### Model cache (`pace_model.json`)

- Written by `model._save_pace_model`; validated by `_try_load_pace_model`.  
- **Bump `PACE_MODEL_SPEC_VERSION`** when changing: feature vector, training generator, hyperparameters encoded in JSON, or schema.  
- Baseline used for initial zone hints comes from training mean; final map zones use quantiles + merge.

### HTML / GeoJSON exporter

- `write_html_map` embeds JavaScript via Python f-strings: any literal `{` / `}` in the template string must be doubled as `{{` / `}}` or Python will interpret them as format fields.  
- GeoJSON is loaded by relative `fetch(filename)` — keep generated HTML and GeoJSON in the **same directory** for `file://` and for `/artifacts/...` URLs.

### Web security (`app.py`)

- `_resolve_web_run_file` restricts served extensions and path traversal.  
- When adding new artifact types, extend allowlists consistently.

---

## Configuration knobs (agent checklist)

| Knob | Location | Effect |
|------|-----------|--------|
| `PACE_MODEL_SPEC_VERSION` | `model.py` | Invalidates `pace_model.json`. |
| `PACE_MODEL_LEARNING_RATE`, `PACE_MODEL_EPOCHS` | `model.py` | Must match cache JSON or cache reload fails. |
| `min_zone_run_m` | `pipeline.run_backend_job`, CLI `--min-zone-run-m` | Suppresses short zone runs on map/CSV. |
| Gunicorn workers / timeout | `render.yaml` | PDF generation may need multiple workers. |

---

## Testing expectations

- Run `pytest` from repo root after substantive changes to `hiking_optimizer/` or `app.py`.  
- Integration tests cover full pipeline; exporter tests cover HTML/GeoJSON shape.  
- Do not commit contents of `web_runs/` (gitignored).

---

## Extension ideas (safe directions)

- Replace synthetic training with labeled real hikes (new dataset module + train script).  
- Optional geometric simplification in `gpx_parser` (merge segments) — separate from zone smoothing.  
- API JSON endpoint in Flask delegating to `run_backend_job` and returning artifact URLs only.

---

## Maintainer note

Keep **README.md** aligned with user-facing install/run steps and **ROBOTS.md** aligned with architecture when you add modules or rename paths.
