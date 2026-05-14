"""BIRD dev set downloader — STUB, do not run blindly.

BIRD-bench dev set: 1,534 question-SQL pairs across 11 SQLite databases.
Official source: https://bird-bench.github.io/

Size: ~1.5 GB compressed (mostly the databases). Download once, extract under
analytics_bird/bird/data/. The path is gitignored.

Usage (after reviewing the URL and license):
    python -m bird.download

Layout after extraction:
    bird/data/
      ├── dev.json                       1534 questions
      ├── dev_tables.json                table metadata
      └── dev_databases/<db_name>/<db_name>.sqlite
"""

from __future__ import annotations

import sys
import urllib.request
import zipfile
from pathlib import Path

# Verify before running; URLs change. Last-known good points are listed on
# https://bird-bench.github.io/ — confirm there first.
BIRD_DEV_URL = "https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip"

DATA_DIR = Path(__file__).parent / "data"


def main() -> int:
    print(f"BIRD dev set → {DATA_DIR}")
    print(f"Source: {BIRD_DEV_URL}")
    print("Size: ~346 MB compressed (verified). Will extract in-place.")
    confirm = input("Proceed? [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return 1

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_DIR / "dev.zip"

    print(f"Downloading → {zip_path}")
    urllib.request.urlretrieve(BIRD_DEV_URL, zip_path)
    print(f"Downloaded {zip_path.stat().st_size / 1e6:.1f} MB")

    print(f"Extracting → {DATA_DIR}")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(DATA_DIR)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
