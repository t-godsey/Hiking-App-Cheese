import argparse
import sys
from pathlib import Path
from hiking_optimizer import run_backend


def main() -> None:
    parser = argparse.ArgumentParser(description="Elevation-aware hiking speed optimizer backend")
    parser.add_argument("--gpx", required=True, help="Path to GPX file")
    parser.add_argument("--weight-lbs", required=True, type=float, help="Backpack weight in lbs")
    parser.add_argument(
        "--max-speed-mph",
        required=True,
        type=float,
        help="Maximum hiking speed cap in mph",
    )
    parser.add_argument(
        "--out-dir",
        default="outputs",
        help="Output directory for generated files (default: outputs)",
    )
    args = parser.parse_args()

    if args.weight_lbs <= 0:
        raise SystemExit("weight-lbs must be positive.")
    if args.max_speed_mph <= 0:
        raise SystemExit("max-speed-mph must be positive.")

    run_backend(
        gpx_path=Path(args.gpx),
        weight_lbs=args.weight_lbs,
        max_speed_mph=args.max_speed_mph,
        out_dir=Path(args.out_dir),
    )


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
