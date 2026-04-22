"""
GPX Elevation Gain Calculator

Usage:
    python gpx_elevation.py <path_to_gpx_file>

Reads a GPX file and outputs the total elevation gain in both meters and feet.
"""

import sys
import xml.etree.ElementTree as ET

# Conversion factor from meters to feet
METERS_TO_FEET = 3.28084
# XML namespace used in GPX 1.1 files — required to find elements in the XML tree
GPX_NS = "http://www.topografix.com/GPX/1/1"


def calculate_elevation_gain(gpx_path: str) -> float:
    """Parse a GPX file and return total elevation gain in meters."""
    try:
        tree = ET.parse(gpx_path)
    except FileNotFoundError:
        print(f"Error: File not found: {gpx_path}")
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: Could not parse GPX file: {e}")
        sys.exit(1)

    root = tree.getroot()

    # Walk every track point and grab its elevation value
    elevations = []
    for trkpt in root.iter(f"{{{GPX_NS}}}trkpt"):
        ele_elem = trkpt.find(f"{{{GPX_NS}}}ele")
        if ele_elem is not None and ele_elem.text:
            elevations.append(float(ele_elem.text))

    if len(elevations) < 2:
        print("Error: Not enough track points found to calculate elevation gain.")
        sys.exit(1)

    # Sum only the uphill steps — ignore any drops in elevation
    total_gain_m = sum(
        elevations[i] - elevations[i - 1]
        for i in range(1, len(elevations))
        if elevations[i] > elevations[i - 1]
    )

    return total_gain_m


def get_trail_name(gpx_path: str) -> str:
    """Extract the trail name from the GPX metadata or track name."""
    try:
        tree = ET.parse(gpx_path)
        root = tree.getroot()
        # Try the track name first, then fall back to the file-level metadata name
        name_elem = root.find(f".//{{{GPX_NS}}}trk/{{{GPX_NS}}}name")
        if name_elem is None:
            name_elem = root.find(f".//{{{GPX_NS}}}metadata/{{{GPX_NS}}}name")
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
    except Exception:
        pass
    return "Unknown Trail"


def main():
    # Expect exactly one argument: the path to the GPX file
    if len(sys.argv) != 2:
        print("Usage: python gpx_elevation.py <path_to_gpx_file>")
        print("Example: python gpx_elevation.py GPX_Files/Dollysods.gpx")
        sys.exit(1)

    gpx_path = sys.argv[1]
    trail_name = get_trail_name(gpx_path)
    gain_m = calculate_elevation_gain(gpx_path)
    gain_ft = gain_m * METERS_TO_FEET

    print(f"Trail:              {trail_name}")
    print(f"File:               {gpx_path}")
    print(f"Total Elevation Gain: {gain_m:,.1f} m  /  {gain_ft:,.1f} ft")


if __name__ == "__main__":
    main()
