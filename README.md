# Elevation-Aware Hiking Optimization

Python app for generating pace recommendations from GPX trail data, available as both a CLI and a web UI.

## Features

- Upload a GPX file
- Enter backpack weight (lbs)
- Enter a max hiking speed cap (mph)
- Generate pace recommendations by segment
- Visualize the generated Leaflet pace map directly in the browser

## Local Setup

From the project root:

```bash
pip install -r requirements.txt
```

## Run Web App Locally

```bash
python app.py
```

Then open [http://localhost:5000](http://localhost:5000).

## Run CLI Locally

```bash
python hiking_optimizer_backend.py --gpx GPX_Files/Dollysods.gpx --weight-lbs 22 --max-speed-mph 3.2
```

Optional output folder:

```bash
python hiking_optimizer_backend.py --gpx GPX_Files/OilCreek.gpx --weight-lbs 30 --max-speed-mph 2.8 --out-dir outputs
```

## Output Files

Generated under `outputs/` for CLI runs, or under `web_runs/<run_id>/` for web UI runs:

- `*_speed_profile.csv`: tabular segment-level recommendations
- `*_pace_map.geojson`: color-coded line segments (`slowdown`, `steady`, `speed-up`)
- `*_pace_map.html`: Leaflet map that renders the generated GeoJSON

## Deploy to Render

This repo includes `render.yaml` for a Blueprint deploy.

1. Push this repository to GitHub.
2. In Render, create a new Blueprint and point it to the repo.
3. Render will use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`

Render injects `PORT` automatically; `app.py` is already configured for that.

## Project Structure

- `app.py`: Flask web app (upload form + map embed)
- `hiking_optimizer_backend.py`: terminal CLI entrypoint
- `hiking_optimizer/pipeline.py`: end-to-end orchestration
- `hiking_optimizer/gpx_parser.py`: GPX parsing + segment creation
- `hiking_optimizer/model.py`: feature engineering + regression model training/prediction
- `hiking_optimizer/zones.py`: pace-zone classification + summarization
- `hiking_optimizer/exporters.py`: CSV / GeoJSON / HTML map writers
- `hiking_optimizer/pace_model.json`: cached fitted regression (weights + scaler + baseline); loaded on every run instead of retraining

### Pace model cache

Training runs once to produce `hiking_optimizer/pace_model.json`, then subsequent CLI and web requests load that file. If the file is missing, invalid, or out of date, the code retrains and overwrites it. After changing synthetic training data, features, or optimizer hyperparameters in `hiking_optimizer/model.py`, bump `PACE_MODEL_SPEC_VERSION` so old caches are ignored.
