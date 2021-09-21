from typing import List, Mapping
import os
import uuid
from kd_splicing.database.models import DB

import pandas as pd

from kd_common import pathutil
from kd_splicing.utils import extractutil
from kd_splicing import paths
from tqdm import tqdm

def read_refseq_protein_id_to_transcript_id(table_file: str) -> Mapping[str, str]:
    result = {}
    tmp_file = table_file[:-3]
    extractutil.extract_file(table_file, tmp_file)

    df = pd.read_csv(tmp_file, sep="\t")
    df = df.rename(columns = {"# feature": "feature"})
    cds = df[df.feature == "CDS"]
    result.update(dict(zip(cds.product_accession, cds.related_accession)))

    os.remove(tmp_file)
    
    return result

def read_genbank_protein_id_to_rna_uuid(db: DB, table_file: str) -> Mapping[str, uuid.UUID]:
    tmp_file = table_file[:-3]
    extractutil.extract_file(table_file, tmp_file)


    df = pd.read_csv(tmp_file, sep="\t")
    print(df)
    df = df.rename(columns = {"# feature": "feature"})
    rnas = df[df.feature == "mRNA"]
    result = {}
    db_rnas = []
    print("db_rnas", len(db.rnas.values()))
    for rna in list(db.rnas.values()):
        gene = db.genes[rna.gene_uuid]
        record = db.records[gene.record_uuid]
        file_db = db.files[record.file_uuid]
        if file_db.db_name == "genbank":
            db_rnas.append(rna)
    print("filtered db_rnas", len(db_rnas))
    for rna, related_accession in zip(db_rnas, rnas.related_accession): 
        result[related_accession] = rna.uuid
    os.remove(tmp_file)
    return result

        
if __name__== "__main__":
    mapping = read_cds_to_rna_map(os.path.join(paths.FOLDER_REFSEQ, "2020_04_14_22_47_08"))


