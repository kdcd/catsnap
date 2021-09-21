import gzip
import os

from kd_common import logutil
_logger = logutil.get_logger(__name__)


def extract_file(src_path: str, dest_path: str) -> None:
    with gzip.open(src_path, 'rb') as infile:
        with open(dest_path, 'wb') as outfile:
            for line in infile:
                outfile.write(line)
