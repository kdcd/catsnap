from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
import os
import pickle
import shutil
from typing import Dict, Generic, List, Mapping, TypeVar, Optional, Union
import uuid
from kd_splicing.database.models import DB, DBPart, DBFile, Gene, Isoform, RNA, Record
from kd_splicing.database.store import get_isoform_to_duplicates
from sqlitedict import SqliteDict
from pathlib import Path
from tqdm import tqdm
import pandas as pd
import zlib, pickle, sqlite3

from kd_common import pathutil



V = TypeVar('V')


def custom_encode(obj):
    return sqlite3.Binary(zlib.compress(pickle.dumps(obj, pickle.HIGHEST_PROTOCOL)))
def custom_decode(obj):
    return pickle.loads(zlib.decompress(bytes(obj)))

class _Wrapper(Generic[V]):
    def __init__(self, path: str, flag: str = "r", compress: bool = False):
        self.path = path
        if compress:
            self.filedb = SqliteDict(path, flag=flag, outer_stack=False, journal_mode="OFF",  encode=custom_encode, decode=custom_decode)
        else:
            self.filedb = SqliteDict(path, flag=flag, outer_stack=False, journal_mode="OFF")
        self.mem = dict()

    def __setitem__(self, key: uuid.UUID, value: V) -> V:
        self.filedb[str(key)] = value

    def add_mem(self, key: uuid.UUID, value: V):
        self.mem[str(key)] = value

    def __getitem__(self, key: Union[uuid.UUID]) -> V:
        mem_value = self.mem.get(str(key))
        if mem_value is not None: return mem_value
        return self.filedb[str(key)]

    def get(self, key: Union[str, uuid.UUID]) -> V:
        mem_value = self.mem.get(str(key))
        if mem_value is not None: return mem_value
        return self.filedb.get(str(key))

    def values(self) -> List[V]:
        return self.filedb.values()
    
    def items(self) -> List[str, V]:
        return self.filedb.items()

    def commit(self) -> None:
        self.filedb.commit()



def file_db_builder(path: Path) -> FileDB:
    db = FileDB(
        files=_Wrapper(str(path) + "_files.sqlite", "w"),
        records=_Wrapper(str(path) + "_records.sqlite", "w"),
        isoforms=_Wrapper(str(path) + "_isoforms.sqlite", "w"),
        rnas=_Wrapper(str(path) + "_rnas.sqlite", "w"),
        genes=_Wrapper(str(path) + "_genes.sqlite", "w"),
        protein_id_to_isoform = dict(),
        isoform_to_duplicates = defaultdict(list),
        file_path = path,
    )
    
    return db


def add_db_part_old(file_db: FileDB, db: DBPart):
    file_db.protein_id_to_isoform.update({i.protein_id: i.uuid for i in reversed(list(db.isoforms.values())) if i.protein_id is not None})
    file_db.isoform_to_duplicates.update(get_isoform_to_duplicates(db))

    for key, v in db.files.items():
        file_db.files[key] = v

    for key, v in db.records.items():
        file_db.records[key] = v

    for key, v in db.isoforms.items():
        file_db.isoforms[key] = v

    for key, v in db.rnas.items():
        file_db.rnas[key] = v

    for key, v in db.genes.items():
        file_db.genes[key] = v

def build_file_db(path: Union[str, Path]) -> FileDBOld:
    isoform_to_duplicates = {}
    protein_id_to_isoform = {}
    if os.path.exists(str(path) + "_isoform_to_duplicates.pkl"):
        with open(str(path) + "_isoform_to_duplicates.pkl", "rb") as f:
            isoform_to_duplicates = pickle.load(f)
    with open(str(path) + "_protein_id_to_isoform.pkl", "rb") as f:
        protein_id_to_isoform = pickle.load(f)
    db = FileDBOld(
        files=_Wrapper(str(path) + "_files.sqlite"),
        records=_Wrapper(str(path) + "_records.sqlite"),
        isoforms=_Wrapper(str(path) + "_isoforms.sqlite"),
        rnas=_Wrapper(str(path) + "_rnas.sqlite"),
        genes=_Wrapper(str(path) + "_genes.sqlite"),
        protein_id_to_isoform = protein_id_to_isoform,
        isoform_to_duplicates = isoform_to_duplicates,
    )
    
    return db

@dataclass
class FileDB:
    files: _Wrapper[DBFile]
    records: _Wrapper[Record]
    isoforms: _Wrapper[Isoform]
    rnas: _Wrapper[RNA]
    genes: _Wrapper[Gene]

    protein_id_to_isoform: _Wrapper[uuid.UUID]
    isoform_to_duplicates: _Wrapper[List[uuid.UUID]]

    file_path: Path

    @classmethod
    def create(cls, file_path: Union[Path, str],  method: str = "r", compress: bool = False):
        file_path = Path(file_path)
        pathutil.create_folder(file_path.parent)
        return FileDB(
            files=_Wrapper(str(file_path) + "_files.sqlite", method, compress),
            records=_Wrapper(str(file_path) + "_records.sqlite", method, compress),
            isoforms=_Wrapper(str(file_path) + "_isoforms.sqlite", method, compress),
            rnas=_Wrapper(str(file_path) + "_rnas.sqlite", method, compress),
            genes=_Wrapper(str(file_path) + "_genes.sqlite", method, compress),
            protein_id_to_isoform = _Wrapper(str(file_path) + "_protein_id_to_isoform.sqlite", method, compress),
            isoform_to_duplicates = _Wrapper(str(file_path) + "_isoform_to_duplicates.sqlite", method, compress),
            file_path = file_path,
        )

    def commit(self): 
        self.protein_id_to_isoform.commit()
        self.isoform_to_duplicates.commit()

        self.files.commit()
        self.records.commit()
        self.isoforms.commit()
        self.rnas.commit()
        self.genes.commit()

    def add_mem_isoforms(self, file: DBFile, record: Record, gene: Gene, isoforms: List[Isoform]):
        self.files.add_mem(file.uuid, file)
        self.records.add_mem(record.uuid, record)
        self.genes.add_mem(gene.uuid, gene)
        for iso in isoforms:
            self.isoforms.add_mem(iso.uuid, iso)
            self.protein_id_to_isoform.add_mem(iso.protein_id, iso.uuid)
            self.isoform_to_duplicates.add_mem(iso.uuid, iso.uuid)


def add_db_part(file_db: FileDB, db: DBPart):
    for key, v in get_isoform_to_duplicates(db).items():
        file_db.isoform_to_duplicates[key] = v

    for i in reversed(list(db.isoforms.values())):
        if i.protein_id is None: continue
        file_db.protein_id_to_isoform[i.protein_id] = i.uuid

    for key, v in db.files.items():
        file_db.files[key] = v

    for key, v in db.records.items():
        file_db.records[key] = v

    for key, v in db.isoforms.items():
        file_db.isoforms[key] = v

    for key, v in db.rnas.items():
        file_db.rnas[key] = v

    for key, v in db.genes.items():
        file_db.genes[key] = v


def compress(file_db_old: FileDB, dst_path: Path):
    file_db = FileDB.create(dst_path, "w", compress=True)

    for key, v in tqdm(file_db_old.isoform_to_duplicates.items()):
        file_db.isoform_to_duplicates[key] = v
    file_db.commit()

    for k, v in tqdm(file_db_old.protein_id_to_isoform.items()):
        file_db.protein_id_to_isoform[k] = v
    file_db.commit()

    for k, v in tqdm(file_db_old.files.items()):
        file_db.files[k] = v
    file_db.commit()

    for k, v in tqdm(file_db_old.records.items()):
        file_db.records[k] = v
    file_db.commit()

    for k, v in tqdm(file_db_old.isoforms.items()):
        file_db.isoforms[k] = v
    file_db.commit()

    for k, v in tqdm(file_db_old.rnas.items()):
        file_db.rnas[k] = v
    file_db.commit()

    for k, v in tqdm(file_db_old.genes.items()):
        file_db.genes[k] = v
    file_db.commit()

def make_df(file_db: FileDB) -> pd.DataFrame:
    files = []
    for r in tqdm(file_db.files.values()):
        files.append({
            "file_uuid": r.uuid, 
            "file": r.src_gb_file,
        })
    files = pd.DataFrame(files)
    files["db"] = files.file.str.split("/").str[-4].astype("category")
    files["db_version"] = files.file.str.split("/").str[-3].astype("category")
    files = files.drop(columns = "file")

    records = []
    organisms = {}
    for r in tqdm(file_db.records.values()):
        org = organisms.get(r.organism)
        if org is None:
            org = {
                "organism_id": len(organisms),
                "organism": r.organism,
                "taxonomy": r.taxonomy,
            }
            organisms[r.organism] = org
        
        records.append({
            "file_uuid": r.file_uuid,
            "record_uuid": r.uuid, 
            "organism_id": org["organism_id"],
        })
        
    organisms = pd.DataFrame(organisms.values())
    organisms = organisms.set_index("organism_id")
    records = pd.DataFrame(records)

    genes = []
    for r in tqdm(file_db.genes.values()):
        genes.append({
            "gene_uuid": r.uuid, 
            "record_uuid": r.record_uuid,
        })
    genes = pd.DataFrame(genes)

    isoforms = []
    for r in tqdm(file_db.isoforms.values()):
        isoforms.append({
            "iso_uuid": r.uuid, 
            "gene_uuid": r.gene_uuid,
        })
    isoforms = pd.DataFrame(isoforms)

    df = pd.merge(isoforms, genes, on = "gene_uuid", how = "left")
    df = pd.merge(df, records, on = "record_uuid", how = "left")
    df = pd.merge(df, files, on = "file_uuid", how = "left")
    df = pd.merge(df, organisms, on = "organism_id", how = "left")

    df["org_type"] = "plant"
    df.loc[(df.db == "refseq") & (df.db_version == "2022_01_22_08_43_34"), "org_type"] = "animal"

    return df

# def db_to_file(db: DB, path: Path):
#     with open(str(path) + "_isoform_to_duplicates.pkl", "wb") as f:
#         pickle.dump(db.isoform_to_duplicates, f)

#     with open(str(path) + "_protein_id_to_isoform.pkl", "wb") as f:
#         pickle.dump(db.protein_id_to_isoform, f)

#     with SqliteDict(str(path) + "_files.sqlite", flag="w") as filedb:
#         for key, v in tqdm(db.files.items(), total=len(db.files)):
#             filedb[str(key)] = v
#         filedb.commit()
    
#     with SqliteDict(str(path) + "_records.sqlite", flag="w") as filedb:
#         for key, v in tqdm(db.records.items(), total=len(db.records)):
#             filedb[str(key)] = v
#         filedb.commit()

#     with SqliteDict(str(path) + "_isoforms.sqlite", flag="w") as filedb:
#         for key, v in tqdm(db.isoforms.items(), total=len(db.isoforms)):
#             filedb[str(key)] = v
#         filedb.commit()

#     with SqliteDict(str(path) + "_rnas.sqlite", flag="w") as filedb:
#         for key, v in tqdm(db.rnas.items(), total=len(db.rnas)):
#             filedb[str(key)] = v
#         filedb.commit()

#     with SqliteDict(str(path) + "_genes.sqlite", flag="w") as filedb:
#         for key, v in tqdm(db.genes.items(), total=len(db.genes)):
#             filedb[str(key)] = v
#         filedb.commit()
