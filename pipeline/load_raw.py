"""Reading the raw inputs.

The trip file is ~656 MB / 7.67M rows, so it is streamed in chunks instead of being loaded into memory at once.
"""

import pandas as pd

from pipeline.config import CHUNK_SIZE, TRIPS_CSV, ZONE_LOOKUP_CSV


def iter_raw_chunks(path=TRIPS_CSV, chunksize=CHUNK_SIZE, nrows=None):
    """"Yield the raw trip CSV chunk by chunk.

    Each chunk gets a leading "source_row column holding the 1-based data row number in the original file, so excluded records can be traced back.
    "nrows" limits how many rows are read (used for quick dev runs).             
    """
    offset = 0
    for chunk in pd.read_csv(path, chunksize=chunksize, nrows=nrows, low_memory=False):
        chunk.insert(0, "source_row", range(
            offset + 1, offset + len(chunk) + 1))
        offset += len(chunk)
        yield chunk


def load_zone_lookup(path=ZONE_LOOKUP_CSV):
    """Load taxi_zone_lookup.csv with snake_case column names."""
    lookup = pd.read_csv(path)
    lookup = lookup.rename(columns={
        "LocationID": "location_id",
        "Borough": "borough",
        "Zone": "zone",
        "service_zone": "service_zone",

    })
    return lookup
