# Elevation-Aware Hiking Optimization (Backend)

Python backend for generating pace recommendations from GPX trail data.

## Current Scope

Terminal-only backend that accepts:
- GPX file (coordinates + elevation)
- Backpack weight in pounds
- User-defined maximum speed (mph)

And produces:
- Per-segment speed recommendation profile
- Highlighted slowdown/speed-up zones
- Color-coded trail map artifacts (`GeoJSON` + `HTML` viewer)

## Run

From the project root:

```bash
python hiking_optimizer_backend.py --gpx GPX_Files/Dollysods.gpx --weight-lbs 22 --max-speed-mph 3.2
```

Optional:

```bash
python hiking_optimizer_backend.py --gpx GPX_Files/OilCreek.gpx --weight-lbs 30 --max-speed-mph 2.8 --out-dir outputs
```

## Output Files

Generated under `outputs/` (or the folder passed via `--out-dir`):

- `*_speed_profile.csv`: tabular segment-level recommendations
- `*_pace_map.geojson`: color-coded line segments (`slowdown`, `steady`, `speed-up`)
- `*_pace_map.html`: Leaflet map that renders the generated GeoJSON

Open the HTML file in a browser to view the color-coded pace map.

## Model Notes

The backend uses a lightweight regression model (implemented in Python, no external ML dependency required):

- Trains on synthetic but terrain-realistic samples
- Uses grade and backpack weight features
- Predicts recommended speed per segment
- Applies user maximum speed cap
- Classifies pace zones using trail-relative speed quantiles

## Backend Structure

The implementation is split for easier iteration:

- `hiking_optimizer_backend.py`: terminal CLI entrypoint
- `hiking_optimizer/gpx_parser.py`: GPX parsing + segment creation
- `hiking_optimizer/model.py`: feature engineering + regression model training/prediction
- `hiking_optimizer/zones.py`: pace-zone classification + summarization
- `hiking_optimizer/exporters.py`: CSV / GeoJSON / HTML map writers
- `hiking_optimizer/pipeline.py`: end-to-end orchestration used by CLI
