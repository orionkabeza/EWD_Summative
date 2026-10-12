"""One command that runs the whole pipeline.

    python pipeline/run_pipeline.py               # full file (~7.67M rows)
    python pipeline/run_pipeline.py --sample 200000    # quick dev run
     
Steps: build zones -> for each raw chunk: clean -> add features -> append to
data/processed/trips_clean.csv. Excluded rows go to logs/excluded_records.csv
and a per-rule summary to logs/exclusion_summary.json.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

from pipeline import config as cfg # noqa: E402
from pipeline.clean import DuplicateTracker, clean_chunk # noqa: E402
from pipeline.exclusion_log import ExclusionLog # noqa: E402
from pipeline.features import FEATURE_COLUMNS, add_features # noqa: E402
from pipeline.load_raw import iter_raw_chunks, load_zone_lookup # noqa: E402
from pipeline.zones import build_zones # noqa: E402


def run(sample=None, chunk_size=cfg.CHUNK_SIZE):
    started = time.time()
    cfg.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/3] Building zones ...")
    zone_summary = build_zones()
    print(f"      {zone_summary['zones_with_polygon']} of {zone_summary['zones_in_lookup']} zones have polygons; "
          f"no polygon for IDs {zone_summary['lookup_ids_without_polygon']}")

    valid_zone_ids = set(load_zone_lookup()["location_id"])
    tracker = DuplicateTracker()
    log = ExclusionLog()
    if cfg.CLEAN_TRIPS_CSV.exists():
        cfg.CLEAN_TRIPS_CSV.unlink()  # start fresh so reruns never append twice

    print("[2/3] Cleaning trips in chunks ...")
    header_written = False
    for number, raw in enumerate(iter_raw_chunks(chunksize=chunk_size, nrows=sample), start=1):
        clean, excluded = clean_chunk(raw, valid_zone_ids, tracker)
        enriched = add_features(clean)[cfg.CLEAN_COLUMNS + FEATURE_COLUMNS]
        enriched.to_csv(cfg.CLEAN_TRIPS_CSV, mode="a", index=False, header=not header_written)
        header_written = True
        log.record_chunk(len(raw), clean, excluded)
        print(f"      chunk {number}: read {log.rows_read:,} kept {log.rows_kept:,} excluded {log.rows_excluded:,}")

    print("[3/3] Writting exclusion summary ...")
    summary = log.write_summary()
    print(f"Done in {time.time() - started:.0f}s: kept {summary['rows_kept']:,} of "
            f"{summary['rows_read']:,} rows ({summary['excluded_percent']}% excluded).")
    for reason, count in summary["reason_counts"].items():
        print(f"       {reason}: {count:,}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the urban mobility data pipeline.")
    parser.add_argument("--sample", type=int, default=None, help="only process the first N raw rows")
    parser.add_argument("--chunk-size", type=int, default=cfg.CHUNK_SIZE)
    args = parser.parse_args()
    run(sample=args.sample, chunk_size=args.chunk_size)





    
    