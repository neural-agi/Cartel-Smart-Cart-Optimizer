import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.scrapers.blinkit.parser import BlinkitProductParser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract raw Blinkit product cards.")
    parser.add_argument(
        "source",
        nargs="?",
        help="Path to a rendered Blinkit HTML artifact. Defaults to latest milk HTML.",
    )
    parser.add_argument("--query", default="milk")
    return parser.parse_args()


def latest_blinkit_html() -> Path:
    settings = get_settings()
    candidates = sorted(
        (settings.raw_data_dir / "blinkit").glob("*_milk.html"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("No Blinkit milk HTML artifacts found.")
    return candidates[0]


def main() -> None:
    args = parse_args()
    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_logs=settings.log_json)

    source_path = Path(args.source).resolve() if args.source else latest_blinkit_html()
    parser = BlinkitProductParser()
    result = parser.parse_file(source_path, query=args.query)
    output_path = parser.save_result(result)
    print(f"Extracted {result.product_count} products -> {output_path}")


if __name__ == "__main__":
    main()
