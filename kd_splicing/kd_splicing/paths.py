import os
from os.path import abspath, join
from kd_common import pathutil


FOLDER_PROJECT_ROOT = abspath(join(__file__, "..", ".."))
FOLDER_PROJECTS_ROOT = abspath(join(__file__, "..", "..", ".."))
FOLDER_DATA = pathutil.create_folder(FOLDER_PROJECT_ROOT, "data")
FOLDER_STORES = pathutil.create_folder(FOLDER_DATA, "stores")
FOLDER_LUNCHES = pathutil.create_folder(FOLDER_DATA, "lunches")
FOLDER_HDD_DATA = "/media/hdd3/konovalov/data"

PATH_BLAST_DB_WITH_DUPLICATES = os.path.join(pathutil.create_folder(FOLDER_DATA, "blast_db_with_duplicates"), "db")

FOLDER_REFSEQ = pathutil.create_folder(FOLDER_HDD_DATA, "refseq")
FOLDER_GENBANK = pathutil.create_folder(FOLDER_HDD_DATA, "genbank")

FOLDER_CATSNAP = pathutil.create_folder(FOLDER_HDD_DATA, "catsnap")
FOLDER_FILE_DB = pathutil.create_folder(FOLDER_CATSNAP, "file_db")
FOLDER_BLAST_DB = pathutil.create_folder(FOLDER_CATSNAP, "blast_db")