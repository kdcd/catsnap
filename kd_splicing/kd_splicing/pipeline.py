from dataclasses import dataclass
from os.path import join
from typing import Optional

import pandas as pd

from kd_common import logutil, pathutil

from kd_splicing import blast
from kd_splicing import database, paths
import uuid


_logger = logutil.get_logger(__name__)


@dataclass
class Pipeline:
    folder_refseq: str
    folder_archive: str
    folder_extracted: str
    genbank_archive_folder: str
    genbank_extracted_folder: str
    db_store_path: str
    db_merged_store_path: str
    db_file_path: str
    genbank_db_store_path: str
    archive_extension: str
    check_existence: bool
    parallel: bool
    remove_extracted_files: bool
    launch_folder: str
    blast_db_folder: str
    blast_db_name: str
    blast_db_path: str
    blast_query_path: str
    blast_results_folder: str
    blast_results_path: str
    detector_path: str
    queries_path: str
    reports_path: str
    launch_id: str


    def db(self) -> database.models.DB:
        _logger.info("Start reading db")
        return database.store.read(self.db_store_path)



def get_test_pipeline(launch_folder_name: Optional[str] = None) -> Pipeline:
    refseq_folder = join(paths.FOLDER_REFSEQ, "2020_04_14_22_47_08")
    genbank_folder = join(paths.FOLDER_GENBANK, "2020_04_07_23_21_35")
    stores_folder = pathutil.create_folder(paths.FOLDER_DATA, "stores")
    blast_db_folder = "/home/konovalov/src/genome/kd/kd_splicing/data/blast_db/"
    blast_db_name = "db"
    if not launch_folder_name:
        launch_folder_name = str(uuid.uuid4())

    launch_folder = pathutil.create_folder(
        paths.FOLDER_LUNCHES, launch_folder_name)
    blast_results_folder = pathutil.create_folder(
        launch_folder, "blast_results")
    return Pipeline(
        folder_refseq=refseq_folder,
        folder_archive=join(refseq_folder, "archive"),
        folder_extracted=join(refseq_folder, "extracted"),
        genbank_archive_folder=join(genbank_folder, "archive"),
        genbank_extracted_folder=join(genbank_folder, "extracted"),
        archive_extension="genomic.gbff.gz",
        check_existence=False,
        parallel=True,
        remove_extracted_files=True,
        db_store_path=join(stores_folder, "db_store.pkl"),
        db_merged_store_path=join(stores_folder, "db_merged_store.pkl"),
        db_file_path=join(stores_folder, "db.sqlite"),
        genbank_db_store_path=join(genbank_folder, "db_store.pgz"),
        launch_folder=launch_folder,
        blast_db_folder=blast_db_folder,
        blast_db_name=blast_db_name,
        blast_db_path=join(blast_db_folder, blast_db_name),
        blast_query_path=join(launch_folder, "query.fasta"),
        blast_results_folder=blast_results_folder,
        blast_results_path=join(blast_results_folder, "result"),
        detector_path=join(launch_folder, "detector.pkl"),   
        queries_path=join(launch_folder, "queries.pkl"),
        reports_path=join(genbank_folder, "reports"),
        launch_id=launch_folder_name,
    )

def get_train_pipeline(launch_folder_name: Optional[str] = None) -> Pipeline:
    p = get_test_pipeline(launch_folder_name)
    blast_db_folder = "/home/konovalov/src/genome_kd/kd/kd_splicing/data/blast_train_db/"
    p.blast_db_path = join(blast_db_folder, "db")
    return p

