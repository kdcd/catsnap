import multiprocessing
import os
import re
import uuid
from functools import partial
from os.path import basename
from typing import Optional, Mapping, List, Tuple, Dict, Iterable
from collections import defaultdict
from dataclasses import dataclass

import pandas as pd
from tqdm import tqdm
from Bio import SeqIO
from Bio.Seq import translate

from kd_common import logutil, pathutil
from kd_splicing import database
from kd_splicing.utils import extractutil


_logger = logutil.get_logger(__name__)


@dataclass
class ExtractSequenceItem:
    id: uuid.UUID
    file_path: str
    sequence_id: str
    location: database.models.Location


@dataclass
class ExtractedSequenceItem(ExtractSequenceItem):
    sequence: str


def _extract_from_file(file_path: str, seq_id_to_items: Mapping[str, List[ExtractSequenceItem]]) -> List[ExtractedSequenceItem]:
    extracted_file = file_path[:-3]
    extractutil.extract_file(file_path, extracted_file)
    result = []
    for record in SeqIO.parse(extracted_file, "fasta"):
        items = seq_id_to_items.get(record.id)
        if not items:
            continue
        for item in items:
            result.append(ExtractedSequenceItem(  # type: ignore
                **item.__dict__,
                # sequence=translate(item.location.extract(record.seq)),
                sequence=item.location.extract(record.seq),
            ))

    os.remove(extracted_file)
    return result


def _get_seq_file_prefix(file_path: str) -> str:
    file_path = re.sub("\\\\+", "/", file_path)
    return ".".join(basename(file_path).split(".")[:2])


def extract(items: List[ExtractSequenceItem], archive_folder: str) -> Iterable[ExtractedSequenceItem]:
    prefixes = {_get_seq_file_prefix(item.file_path) for item in items}
    files = [
        f
        for f in pathutil.file_list(archive_folder, "fna.gz")
        if any(basename(f).startswith(prefix) for prefix in prefixes)
    ]

    seq_id_to_items: Dict[str, List[ExtractSequenceItem]] = defaultdict(list)
    for item in items:
        seq_id_to_items[item.sequence_id].append(item)

    _logger.info("Start extract sequences")
    item_id_to_item = {item.id: item for item in items}
    with multiprocessing.Pool() as p:
        for results_pack in tqdm(p.map(partial(_extract_from_file, seq_id_to_items=seq_id_to_items), files), total=len(files)):
            for result_item in results_pack:
                yield result_item
