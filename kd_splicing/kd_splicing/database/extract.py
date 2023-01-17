import os.path
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from os.path import join
from typing import Dict, List, Mapping
from uuid import UUID
from pathlib import Path

import pandas as pd
from Bio.Seq import translate

from kd_common import logutil, pathutil
from kd_splicing import blast, database, dataset, features, helpers, location, models, paths, pipeline, sequences
from kd_splicing.dataset.models import Dataset
from kd_splicing.dump import dump
from kd_splicing.features import Match
from kd_splicing.database import feature_tables
from kd_splicing.models import IsoformTuple
from kd_splicing.database import filedb

_logger = logutil.get_logger(__name__)

def main() -> None:
    # folder_refseq = join(paths.FOLDER_REFSEQ, "2021_02_16_17_37_56")
    folder_refseq = join(paths.FOLDER_REFSEQ, "2022_01_22_08_43_34")
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
    # store_folder = pathutil.create_folder(paths.FOLDER_STORES, "2021_02_16_17_37_56")
    # store_merged_path = join(store_folder, "store_merged.pkl")
    db = database.models.DB()
    db = database.store.merge_separatly(db, [folder_refseq], folder_genbank)
    # database.store.write(db, store_merged_path)

def build_file_db():
    file_db = filedb.FileDB.create(os.path.join(pathutil.create_folder(paths.FOLDER_FILE_DB, "pr_2021_02_ar_2022_01_22_pg_2021_02"), "file_db"))
    database.store.merge_separatly(
        db = file_db,
        refseq_folders = [
            join(paths.FOLDER_REFSEQ, "2021_02_16_17_37_56"),
            join(paths.FOLDER_REFSEQ, "2022_01_22_08_43_34"),
        ], 
        genbank_folder = join(paths.FOLDER_GENBANK, "2021_02_16_20_16_27"),
        add_part_method = filedb.add_db_part,
    )

    file_db.commit()

def create_blast_db_with_duplicates():
    timestamp = "pr_2021_02_ar_2022_01_22_pg_2021_02"
    db = filedb.FileDB.create(os.path.join(pathutil.create_folder(paths.FOLDER_FILE_DB, timestamp), "file_db"))
    blast.create_db_from_file_db(db, os.path.join(pathutil.create_folder(paths.FOLDER_BLAST_DB, timestamp), "db"))

def create_blast_db_selected_organisms():
    filedb_timestamp = "pr_2021_02_ar_2022_01_22_pg_2021_02"
    blastdb_timestamp = "selected_orgs_2022_06_29_pr_2021_02_ar_2022_01_22_pg_2021_02"

    db = filedb.FileDB.create(Path(os.path.join(pathutil.create_folder(paths.FOLDER_FILE_DB, filedb_timestamp), "file_db")))
    df = database.filedb.make_df(db)
    selected_organisms = ["Homo sapiens", "Macaca mulatta", "Mus musculus", "Rattus norvegicus", "Ovis aries", "Balaenoptera musculus", "Bos taurus", "Orcinus orca", "Equus caballus", "Felis catus", "Zalophus californianus", "Myotis myotis", "Pteropus giganteus", "Choloepus didactylus", "Manis pentadactyla", "Loxodonta africana", "Trichechus manatus latirostris", "Erinaceus europaeus", "Orycteropus afer afer", "Monodelphis domestica", "Ornithorhynchus anatinus", "Tachyglossus aculeatus", "Gallus gallus", "Aquila chrysaetos chrysaetos", "Falco rusticolus", "Tyto alba", "Passer montanus", "Columba livia", "Calidris pugnax", "Melopsittacus undulatus", "Struthio camelus australis", "Egretta garzetta", "Aptenodytes forsteri", "Picoides pubescens", "Chelonia mydas", "Mauremys reevesii", "Crotalus tigris", "Podarcis muralis", "Alligator mississippiensis", "Xenopus laevis", "Rana temporaria", "Protopterus annectens", "Latimeria chalumnae", "Polypterus senegalus", "Acipenser ruthenus", "Anguilla anguilla", "Scleropages formosus", "Carassius auratus", "Danio rerio", "Pygocentrus nattereri", "Oncorhynchus mykiss", "Salmo salar", "Gadus morhua", "Myripristis murdjan", "Siniperca chuatsi", "Sander lucioperca", "Oreochromis niloticus", "Hippoglossus hippoglossus", "Thunnus albacares", "Hippocampus comes", "Scyliorhinus canicula", "Chiloscyllium plagiosum", "Petromyzon marinus", "Branchiostoma belcheri", "Branchiostoma floridae", "Styela clava", "Ciona intestinalis", "Acanthaster planci", "Procambarus clarkii", "Daphnia magna", "Varroa destructor", "Limulus polyphemus", "Parasteatoda tepidariorum", "Zootermopsis nevadensis", "Drosophila melanogaster", "Bombyx mori", "Nilaparvata lugens", "Apis mellifera", "Folsomia candida", "Photinus pyralis", "Thrips palmi", "Chrysoperla carnea", "Crassostrea gigas", "Pomacea canaliculata", "Octopus vulgaris", "Acropora millepora", "Dendronephthya gigantea", "Hydra vulgaris", "Caenorhabditis elegans", "Priapulus caudatus", "Amphimedon queenslandica", "Schistosoma mansoni", "Trichoplax adhaerens", "Sphaeroforma arctica JP610", "Fonticula alba", "Capsaspora owczarzaki ATCC 30864", "Salpingoeca rosetta"]
    iso_ids = set(df[(df.org_type == "plant") | (df.organism.isin(selected_organisms))].iso_uuid)

    blast.create_db_from_file_db(db, os.path.join(pathutil.create_folder(paths.FOLDER_BLAST_DB, blastdb_timestamp), "db"), filter = iso_ids)


if __name__ == "__main__":
    # main()
    # build_file_db()
    # create_blast_db_with_duplicates()

    create_blast_db_selected_organisms()
