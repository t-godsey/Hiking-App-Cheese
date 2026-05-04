"""
CSV / GeoJSON / HTML exporters for optimizer results.

The HTML map is a self-contained Leaflet page that fetches the GeoJSON by *filename* from the
same directory (works for `file://` opens and for `/artifacts/...` URLs on the web app).
Python f-strings drive the template: literal `{` / `}` in embedded JS/CSS must be doubled as `{{` / `}}`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# CSV — tabular export (one row per trail segment)
# ---------------------------------------------------------------------------


def write_csv(output_csv: Path, rows: list[dict[str, float | str]]) -> None:
    """Per-segment spreadsheet (speed, zone, geometry, along-trail distances)."""
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    # newline="" avoids Windows-only "\r\r\n" quirks when spreadsheets reopen the CSV.
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


# ---------------------------------------------------------------------------
# GeoJSON — RFC 7946 features (Leaflet uses [longitude, latitude] vertex order)
# ---------------------------------------------------------------------------


def write_geojson(output_geojson: Path, rows: list[dict[str, float | str]]) -> None:
    """One two-point LineString per segment; styling keys live in ``properties`` for the map script."""

    output_geojson.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for row in rows:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    # GeoJSON positions are [lon, lat]; GPX rows store lat/lon separately.
                    "coordinates": [
                        [row["start_lon"], row["start_lat"]],
                        [row["end_lon"], row["end_lat"]],
                    ],
                },
                "properties": {
                    "segment_index": row["segment_index"],
                    "distance_m": row["distance_m"],
                    "elev_delta_m": row["elev_delta_m"],
                    "grade_pct": row["grade_pct"],
                    "recommended_speed_mph": row["recommended_speed_mph"],
                    "zone": row["zone"],
                    "zone_color": row["zone_color"],
                },
            }
        )

    with output_geojson.open("w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)


# ---------------------------------------------------------------------------
# Map legend helpers (HTML fragments injected into Leaflet DOM)
# ---------------------------------------------------------------------------


def pace_zone_mph_ranges(segment_rows: list[dict[str, float | str]]) -> dict[str, tuple[float, float]]:
    """Min/max recommended speed per zone label (slowdown | steady | speed-up) after refinement."""
    buckets: dict[str, list[float]] = {}
    for row in segment_rows:
        key = str(row["zone"])
        buckets.setdefault(key, []).append(float(row["recommended_speed_mph"]))
    # Ranges summarize "what mph values appear in this zone on this hike"; zones can overlap in mph across labels.
    return {z: (min(values), max(values)) for z, values in buckets.items() if values}


def _legend_speed_zone_html(label: str, color: str, zone_key: str, ranges: dict[str, tuple[float, float]]) -> str:
    """One legend row: color swatch, name, and (min–max mph) for segments in that zone."""
    pair = ranges.get(zone_key)
    if pair:
        lo, hi = pair
        # Collapse degenerate buckets so the legend reads "2.9 mph" instead of a trivial range.
        if abs(hi - lo) < 0.002:
            span = f"{lo:.1f} mph"
        else:
            span = f"{lo:.1f}–{hi:.1f} mph"
        suffix = f' <span style="font-weight:600;color:#333;">({span})</span>'
    else:
        suffix = ""
    return f'<div><span class="swatch" style="background:{color}"></span>{label}{suffix}</div>'


# ---------------------------------------------------------------------------
# HTML / Leaflet viewer (same folder as sibling GeoJSON is required for relative fetch())
# ---------------------------------------------------------------------------


def write_html_map(
    output_html: Path,
    geojson_filename: str,
    title: str,
    *,
    zone_mph_ranges: dict[str, tuple[float, float]] | None = None,
) -> None:
    """
    Write ``*_pace_map.html`` referencing ``geojson_filename`` (basename only).

    ``zone_mph_ranges`` fills the mph span next to each speed-zone swatch on the exported map legend.
    The HTML body is mostly a large f-string: only ``{geojson_filename}``, ``{title}``,
    ``{legend_inner_js}`` are interpolated; every other curly brace belongs to Leaflet/CSS/JS so it is doubled.
    """
    zr = zone_mph_ranges or {}
    legend_inner = (
        "<div><strong>Speed zones</strong></div>"
        + _legend_speed_zone_html("Slowdown zone", "#d73027", "slowdown", zr)
        + _legend_speed_zone_html("Steady zone", "#fdae61", "steady", zr)
        + _legend_speed_zone_html("Speed-up zone", "#1a9850", "speed-up", zr)
        + '<hr style="margin:6px 0;border:0;border-top:1px solid #ddd;">'
        + "<div><strong>Elevation gain</strong></div>"
        + '<div><span class="swatch" style="background:#6baed6"></span>Flat / downhill</div>'
        + '<div><span class="swatch" style="background:#c7e9c0"></span>Low uphill gain</div>'
        + '<div><span class="swatch" style="background:#31a354"></span>High uphill gain</div>'
        + '<div><span class="swatch" style="background:#006d2c"></span>Very high uphill gain</div>'
    )
    # Embed as one JS string literal — avoids juggling quotes inside the Leaflet snippet below.
    legend_inner_js = json.dumps(legend_inner)

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
    @media print {{
      body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      #map {{ height: 100vh !important; width: 100% !important; page-break-inside: avoid; }}
      /* Print/PDF: hide map chrome only. Hiding `.leaflet-control-container` would also drop the pace legend. */
      .leaflet-control-zoom,
      .leaflet-control-layers,
      .leaflet-control-expand,
      .leaflet-control-attribution {{
        display: none !important;
      }}
      .leaflet-bottom.leaflet-right .leaflet-control.pace-map-legend {{
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        break-inside: avoid;
      }}
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
    const streetLayer = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);
    const topoLayer = L.tileLayer('https://{{s}}.tile.opentopomap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 17,
      subdomains: 'abc',
      attribution: 'Map data: &copy; OpenStreetMap contributors, SRTM | Map style: &copy; OpenTopoMap'
    }});

    // Two overlays share one FeatureCollection: speed paints stored zone_color; elevation rescales uplift hue.
    const speedLayerGroup = L.layerGroup().addTo(map);
    const elevationLayerGroup = L.layerGroup();

    function elevationGainColor(gainMeters, maxGainMeters) {{
      if (gainMeters <= 0) return '#6baed6';
      const ratio = Math.max(0, Math.min(1, gainMeters / Math.max(maxGainMeters, 1)));
      if (ratio < 0.2) return '#c7e9c0';
      if (ratio < 0.4) return '#a1d99b';
      if (ratio < 0.6) return '#74c476';
      if (ratio < 0.8) return '#31a354';
      return '#006d2c';
    }}

    // Relative URL — keep GeoJSON sibling next to this file (outputs dir, Flask artifact folder, etc.).
    fetch('{geojson_filename}')
      .then(r => r.json())
      .then(data => {{
        let maxElevationGain = 0;
        data.features.forEach(feature => {{
          const gain = Number(feature.properties.elev_delta_m || 0);
          if (gain > maxElevationGain) {{
            maxElevationGain = gain;
          }}
        }});

        const speedLayer = L.geoJSON(data, {{
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
        }});
        speedLayer.addTo(speedLayerGroup);

        const elevationLayer = L.geoJSON(data, {{
          style: feature => {{
            const gain = Number(feature.properties.elev_delta_m || 0);
            return {{
              color: elevationGainColor(gain, maxElevationGain),
              weight: 5,
              opacity: 0.95
            }};
          }},
          onEachFeature: (feature, line) => {{
            const p = feature.properties;
            const gain = Math.max(0, Number(p.elev_delta_m || 0));
            line.bindPopup(
              `Seg ${{p.segment_index}}<br>Elevation gain: ${{gain.toFixed(1)}} m<br>Grade: ${{Number(p.grade_pct).toFixed(1)}}%<br>Speed: ${{Number(p.recommended_speed_mph).toFixed(2)}} mph`
            );
          }}
        }});
        elevationLayer.addTo(elevationLayerGroup);

        const baseMaps = {{
          'OpenStreetMap': streetLayer,
          'Topographic': topoLayer
        }};
        const overlays = {{
          'Speed zones': speedLayerGroup,
          'Elevation gain': elevationLayerGroup
        }};
        L.control.layers(baseMaps, overlays, {{ collapsed: false }}).addTo(map);

        map.fitBounds(speedLayer.getBounds(), {{ padding: [20, 20] }});
      }});

    const legend = L.control({{position: 'bottomright', className: 'pace-map-legend'}});
    legend.onAdd = function() {{
      const div = L.DomUtil.create('div', 'legend');
      div.innerHTML = {legend_inner_js};
      return div;
    }};
    legend.addTo(map);
  </script>
</body>
</html>
"""
    # Matching ``*_pace_map.geojson`` file is emitted separately by ``write_geojson`` in the caller.
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")
