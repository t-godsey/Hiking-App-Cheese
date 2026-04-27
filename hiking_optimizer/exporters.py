"""Writers for CSV, GeoJSON, and map HTML artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path


def write_csv(output_csv: Path, rows: list[dict[str, float | str]]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "segment_index",
                "start_lat",
                "start_lon",
                "end_lat",
                "end_lon",
                "distance_m",
                "elev_delta_m",
                "grade_pct",
                "recommended_speed_mph",
                "zone",
                "zone_color",
                "start_m",
                "end_m",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_geojson(output_geojson: Path, rows: list[dict[str, float | str]]) -> None:
    output_geojson.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for row in rows:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [row["start_lon"], row["start_lat"]],
                        [row["end_lon"], row["end_lat"]],
                    ],
                },
                "properties": {
                    "segment_index": row["segment_index"],
                    "distance_m": row["distance_m"],
                    "grade_pct": row["grade_pct"],
                    "recommended_speed_mph": row["recommended_speed_mph"],
                    "zone": row["zone"],
                    "zone_color": row["zone_color"],
                },
            }
        )

    with output_geojson.open("w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)


def write_html_map(output_html: Path, geojson_filename: str, title: str) -> None:
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} - Pace Map</title>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
    crossorigin=""
  />
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; }}
    #map {{ height: 100vh; width: 100%; }}
    .legend {{
      background: white;
      padding: 8px 10px;
      line-height: 1.4;
      border-radius: 5px;
      box-shadow: 0 1px 5px rgba(0,0,0,0.25);
      font-size: 12px;
    }}
    .swatch {{
      display: inline-block;
      width: 12px;
      height: 12px;
      margin-right: 6px;
      vertical-align: middle;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
    crossorigin=""></script>
  <script>
    const map = L.map('map');
    L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    fetch('{geojson_filename}')
      .then(r => r.json())
      .then(data => {{
        const layer = L.geoJSON(data, {{
          style: feature => ({{
            color: feature.properties.zone_color || '#3388ff',
            weight: 5,
            opacity: 0.95
          }}),
          onEachFeature: (feature, line) => {{
            const p = feature.properties;
            line.bindPopup(
              `Seg ${{p.segment_index}}<br>Speed: ${{Number(p.recommended_speed_mph).toFixed(2)}} mph<br>Grade: ${{Number(p.grade_pct).toFixed(1)}}%<br>Zone: ${{p.zone}}`
            );
          }}
        }}).addTo(map);
        map.fitBounds(layer.getBounds(), {{ padding: [20, 20] }});
      }});

    const legend = L.control({{position: 'bottomright'}});
    legend.onAdd = function() {{
      const div = L.DomUtil.create('div', 'legend');
      div.innerHTML =
        '<div><span class="swatch" style="background:#d73027"></span>Slowdown zone</div>' +
        '<div><span class="swatch" style="background:#fdae61"></span>Steady zone</div>' +
        '<div><span class="swatch" style="background:#1a9850"></span>Speed-up zone</div>';
      return div;
    }};
    legend.addTo(map);
  </script>
</body>
</html>
"""
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")
