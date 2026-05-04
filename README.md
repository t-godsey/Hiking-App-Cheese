# Elevation-Aware Hiking Optimization

This project analyzes a hiking route from a **GPX file** (track points with elevation), estimates **recommended pace per segment** using a small regression model, and produces **maps and tables** you can open in a browser or spreadsheet. It is available as a **Flask web app** and as a **command-line tool**.

**Live app (Render):** https://hiking-app-cheese-forked.onrender.com/

---

## What you get

- **Per-segment speed** (mph), capped by your maximum hiking speed  
- **Pace zones**: slowdown, steady, speed-up (with optional smoothing so tiny zones do not flicker on the map)  
- **Artifacts** for each run: CSV profile, GeoJSON trail lines, HTML Leaflet map (street or topographic basemap; optional overlays for speed zones and elevation gain)  
- **Web UI**: optional PDF export via Playwright (Chromium)

---

## Requirements

- **Python** 3.10 or newer (3.11+ recommended)  
- **pip**  
- For the **web app PDF** feature: **Playwright** with Chromium (installed after `pip`; see below)

---

## Install

From the repository root:

```bash
python -m venv .venv
```

Activate the virtual environment (Windows PowerShell):

```bash
.\.venv\Scripts\Activate.ps1
```

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

If you will use **Download PDF** in the web UI (or run tests that cover PDF), install Chromium once:

```bash
playwright install chromium
```

For **development** (tests, pytest):

```bash
pip install -r requirements-dev.txt
```

---

## Run the web application

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) (or `http://127.0.0.1:5000`).

1. Upload a `.gpx` file with track points and elevation.  
2. Enter **backpack weight (lbs)** and **max hiking speed (mph)**.  
3. Submit to generate the map and summary.  

Each run writes files under `web_runs/<run_id>/` (that folder is gitignored). Use **Download PDF** or the browser print dialog if you want a PDF.

**Production / hosting:** the repo includes `render.yaml` (Gunicorn with two workers, Playwright at build time). Render sets `PORT` automatically; `app.py` reads it.

---

## Run the command-line tool

Minimal example (paths relative to repo root):

```bash
python hiking_optimizer_backend.py --gpx GPX_Files/Dollysods.gpx --weight-lbs 22 --max-speed-mph 3.2
```

### CLI options

| Option | Required | Description |
|--------|----------|-------------|
| `--gpx` | Yes | Path to a GPX 1.1 file with `trkpt` elements and `ele` per point. |
| `--weight-lbs` | Yes | Backpack weight in pounds (must be positive). |
| `--max-speed-mph` | Yes | Upper cap on recommended speed in mph (must be positive). |
| `--out-dir` | No | Directory for generated files (default: `outputs`). |
| `--min-zone-run-m` | No | Minimum along-trail length (meters) for a pace zone before merging short runs into neighbors (default: `200`). Increase (e.g. `350`) for fewer, longer zones on the map. |

Additional examples:

```bash
python hiking_optimizer_backend.py --gpx GPX_Files/OilCreek.gpx --weight-lbs 30 --max-speed-mph 2.8 --out-dir outputs
```

```bash
python hiking_optimizer_backend.py --gpx GPX_Files/Dollysods.gpx --weight-lbs 22 --max-speed-mph 3.2 --min-zone-run-m 350
```

---

## Output files

After a successful run, you will find (names depend on the GPX filename stem):

| File | Description |
|------|-------------|
| `*_speed_profile.csv` | One row per trail segment: coordinates, distance, elevation change, grade, recommended speed, zone, colors. |
| `*_pace_map.geojson` | GeoJSON `LineString` features with pace and elevation properties for mapping. |
| `*_pace_map.html` | Standalone Leaflet page: open in a browser; layer control for basemap (street / topo) and overlays (speed zones, elevation gain). |

- **CLI:** files go under `--out-dir` (default `outputs/`).  
- **Web:** files go under `web_runs/<run_id>/`.

---

## Pace model (cached weights)

The regressor is defined in `hiking_optimizer/model.py`. Fitted weights and feature scaling are stored in **`hiking_optimizer/pace_model.json`** so normal runs **load** the model instead of retraining.

- If the JSON is missing, invalid, or does not match the current spec, the app **retrains once** and overwrites the file.  
- After you change training data, features, learning rate, epochs, or file format, bump **`PACE_MODEL_SPEC_VERSION`** in `model.py` so old caches are ignored.

---

## Run tests

```bash
pytest
```

Tests live under `tests/` and cover the GPX parser, model, zones, exporters, pipeline integration, and the Flask app.

---

## Project layout (short)

| Path | Role |
|------|------|
| `app.py` | Flask app: upload, optimize, serve artifacts, optional PDF. |
| `hiking_optimizer_backend.py` | CLI entrypoint. |
| `hiking_optimizer/` | Core library: GPX → segments → model → zones → CSV/GeoJSON/HTML. |
| `templates/` | Jinja templates for the web UI. |
| `GPX_Files/` | Sample GPX files for local trials. |
| `tests/` | Pytest suite. |
| `render.yaml` | Render.com Blueprint-style deploy. |
| `requirements.txt` / `requirements-dev.txt` | Runtime and dev dependencies. |

For a **machine-readable** map aimed at AI coding agents (structure, contracts, extension points), see **`ROBOTS.md`**.

---

## Deploy to Render

1. Push this repository to GitHub (or another Git provider Render supports).  
2. In Render, create a **Blueprint** and select the repo.  
3. Confirm `render.yaml`: install dependencies, `playwright install chromium` at build time, start with `gunicorn app:app --workers 2 --timeout 180`.

---

## Attribution (tooling)

This repository was developed with **Cursor**, using a mix of **Auto (agentic) mode** and **Claude Sonnet 4.6**.
