from dataclasses import dataclass
import os
import pickle
from typing import Generic, List, Mapping, TypeVar
import uuid
from kd_splicing.database.models import DB, DBFile, Gene, Isoform, RNA, Record
from sqlitedict import SqliteDict
from pathlib import Path
from tqdm import tqdm

def db_to_file(db: DB, path: Path):
    with open(str(path) + "_isoform_to_duplicates.pkl", "wb") as f:
        pickle.dump(db.isoform_to_duplicates, f)

    with open(str(path) + "_protein_id_to_isoform.pkl", "wb") as f:
        pickle.dump(db.protein_id_to_isoform, f)

    with SqliteDict(str(path) + "_files.sqlite", flag="w") as filedb:
        for key, v in tqdm(db.files.items(), total=len(db.files)):
            filedb[str(key)] = v
        filedb.commit()
    
    with SqliteDict(str(path) + "_records.sqlite", flag="w") as filedb:
        for key, v in tqdm(db.records.items(), total=len(db.records)):
            filedb[str(key)] = v
        filedb.commit()

    with SqliteDict(str(path) + "_isoforms.sqlite", flag="w") as filedb:
        for key, v in tqdm(db.isoforms.items(), total=len(db.isoforms)):
            filedb[str(key)] = v
        filedb.commit()

    with SqliteDict(str(path) + "_rnas.sqlite", flag="w") as filedb:
        for key, v in tqdm(db.rnas.items(), total=len(db.rnas)):
            filedb[str(key)] = v
        filedb.commit()

    with SqliteDict(str(path) + "_genes.sqlite", flag="w") as filedb:
        for key, v in tqdm(db.genes.items(), total=len(db.genes)):
            filedb[str(key)] = v
        filedb.commit()


V = TypeVar('V')

class _Wrapper(Generic[V]):
    def __init__(self, path: str):
        self.filedb = SqliteDict(path, flag="r")

    def __getitem__(self, key: uuid.UUID) -> V:
        return self.filedb[str(key)]

    def get(self, key: uuid.UUID) -> V:
        return self.filedb.get(str(key))

    def values(self) -> List[V]:
        return self.filedb.values();


@dataclass
class FileDB:
    files: _Wrapper[DBFile]
    records: _Wrapper[Record]
    isoforms: _Wrapper[Isoform]
    rnas: _Wrapper[RNA]
    genes: _Wrapper[Gene]

    protein_id_to_isoform: Mapping[str, uuid.UUID]
    isoform_to_duplicates: Mapping[uuid.UUID, List[uuid.UUID]]

def build_file_db(path: Path) -> FileDB:
    isoform_to_duplicates = {}
    if os.path.exists(str(path) + "_isoform_to_duplicates.pkl"):
        with open(str(path) + "_isoform_to_duplicates.pkl", "rb") as f:
            isoform_to_duplicates = pickle.load(f)
    with open(str(path) + "_protein_id_to_isoform.pkl", "rb") as f:
        protein_id_to_isoform = pickle.load(f)
    db = FileDB(
        files=_Wrapper(str(path) + "_files.sqlite"),
        records=_Wrapper(str(path) + "_records.sqlite"),
        isoforms=_Wrapper(str(path) + "_isoforms.sqlite"),
        rnas=_Wrapper(str(path) + "_rnas.sqlite"),
        genes=_Wrapper(str(path) + "_genes.sqlite"),
        protein_id_to_isoform = protein_id_to_isoform,
        isoform_to_duplicates = isoform_to_duplicates,
    )
    
    return db


