import os.path
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from os.path import join
from typing import Dict, List, Mapping
from uuid import UUID

import pandas as pd
from Bio.Seq import translate

from kd_common import logutil, pathutil
from kd_splicing import blast, database, dataset, features, helpers, location, models, paths, pipeline, sequences
from kd_splicing.dataset.models import Dataset
from kd_splicing.dump import dump
from kd_splicing.features import Match
from kd_splicing.database import feature_tables
from kd_splicing.models import IsoformTuple

_logger = logutil.get_logger(__name__)

def main() -> None:
    folder_refseq = join(paths.FOLDER_REFSEQ, "2021_02_16_17_37_56")
    folder_refseq_archive = join(folder_refseq, "archive")
    folder_refseq_extracted = pathutil.create_folder(folder_refseq, "extracted")
    folder_refseq_feature_tables = pathutil.create_folder(folder_refseq, "feature_tables")
    folder_genbank = join(paths.FOLDER_GENBANK, "2021_02_16_20_16_27")
    folder_genbank_archive=join(folder_genbank, "archive")
    folder_genbank_extracted=pathutil.create_folder(folder_genbank, "extracted")
    folder_genbank_reports = join(folder_genbank, "reports")
    folder_genbank_feature_tables = join(folder_genbank, "feature_tables")

    # database.archive.read_folder(
    #     src_folder=folder_refseq_archive,
    #     dst_folder=folder_refseq_extracted,
    #     db_name="refseq",
    #     extension="gbff.gz",
    #     check_existence=True,
    #     parallel=True,
    #     remove_extracted_file=True,
    # )
    # database.archive.read_folder(
    #     src_folder=folder_genbank_archive,
    #     dst_folder=folder_genbank_extracted,
    #     db_name="genbank",
    #     extension="gbff.gz",
    #     check_existence=True,
    #     parallel=True,
    #     remove_extracted_file=True,
    # )
    store_folder = pathutil.create_folder(paths.FOLDER_STORES, "2021_02_16_17_37_56")
    store_merged_path = join(store_folder, "store_merged.pkl")
    db = database.store.merge_separatly(folder_refseq, folder_genbank)
    database.store.write(db, store_merged_path)

if __name__ == "__main__":
    main()
