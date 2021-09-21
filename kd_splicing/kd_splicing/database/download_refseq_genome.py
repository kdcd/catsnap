import os
from os.path import join, isfile
from urllib.request import urlopen, urlretrieve
from typing import List, Optional, Tuple
from dataclasses import dataclass

from tqdm import tqdm
from kd_common import logutil, pathutil
from kd_splicing import paths

from bs4 import BeautifulSoup
import multiprocessing
from multiprocessing import get_context
import urllib.error
import pickle

logger = logutil.get_logger(__name__)


root = "https://ftp.ncbi.nlm.nih.gov/genomes/refseq/plant/"
# timestamp = pathutil.get_timestamp_str()
timestamp = "2021_02_16_17_37_56"
refseq_folder = pathutil.create_folder(paths.FOLDER_REFSEQ, timestamp)
archive_folder = pathutil.create_folder(refseq_folder, "archive")
feature_tables_folder = pathutil.create_folder(refseq_folder, "feature_tables")
_REFSEQ_ARCHIVE_FILES = join(refseq_folder, "genbank_archive_files.pkl")

@dataclass
class Record:
    plant_name: str
    archive_file: Optional[str] = None
    feature_table_file: Optional[str] = None

def _download(record: Record) -> None:
    def try_download():
        logger.info(f"downloading file {record.archive_file}")
        urlretrieve(record.archive_file, archive_file_path)
        logger.info(f"downloading file {record.feature_table_file}")
        urlretrieve(record.feature_table_file, feature_table_path)
    if record.archive_file is None or record.feature_table_file is None:
        return
    archive_file_path = join(archive_folder, record.archive_file.split("/")[-1])
    feature_table_path = join(feature_tables_folder, record.feature_table_file.split("/")[-1])
    try:
        try:
            try:
                try_download()
            except Exception as e:
                logger.exception(f"Couldn't download url first time {record.archive_file}")
                try_download()
        except Exception as e:
            logger.exception(f"Couldn't download url second time {record.archive_file}")
            os.remove(archive_file_path)
    except Exception as e:
        logger.exception(f"Couldn't remove file {archive_file_path}")

def _get_record(plant_name: str) -> Record:
    try:
        plant = root + plant_name

        try:
            html = urlopen(plant).read().decode('utf-8')    
        except Exception as e:
            logger.exception(f"Not found {plant}")
            return Record(plant_name)
        soup = BeautifulSoup(html, features="html.parser")
        references = [a['href'] for a in soup.find_all('a', href=True) if a["href"] in {"reference/", "representative/", "latest_assembly_versions/"}]
        if not references:
            return Record(plant_name)

        url_reference = plant + references[0]
        
        try:
            html = urlopen(url_reference).read().decode('utf-8')    
        except Exception as e:
            logger.exception(f"Not found {url_reference}")
            return Record(plant_name)
        soup = BeautifulSoup(html, features="html.parser")

        version = [a['href'] for a in soup.find_all('a', href=True)][1]
        url = url_reference + version

        try:
            html = urlopen(url).read().decode('utf-8')    
        except Exception as e:
            logger.exception(f"Not found {url}")
            return Record(plant_name)
        soup = BeautifulSoup(html, features="html.parser")
        # print([a['href'] for a in soup.find_all('a', href=True)])
        archive_file = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith("genomic.gbff.gz")][0]
        feature_table = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith("feature_table.txt.gz")][0]
        result = url + archive_file
        return Record(plant_name, url + archive_file, url + feature_table) 
    except urllib.error.HTTPError as e:
        logger.exception(f"Not found plant name {plant_name}. Reason{e.reason}")
    except Exception as e:
        logger.exception(f"Not found plant name {plant_name}")

    return Record(plant_name)


def _get_records() -> None:
    html = urlopen(root).read().decode('utf-8')
    soup = BeautifulSoup(html, features="html.parser")

    plant_names = [
        a["href"]
        for a in soup.find_all('a', href=True) 
    ][1:]
    
    # result: List[Record] = []
    # for plant_name in tqdm(plant_names):
    #     if plant_name == "Setaria_viridis/":
    #         print(_get_record(plant_name))

    with get_context("spawn").Pool() as p:
        records = list(tqdm(p.imap_unordered(_get_record, plant_names), total=len(plant_names)))

    absent_archive_files = [
        record.plant_name
        for record in records
        if record.archive_file is None
    ]
    logger.warning(f"Absent archive files:\n{absent_archive_files}")

    absent_feature_tables = [
        record.plant_name
        for record in records
        if record.feature_table_file is None
    ]
    logger.warning(f"Absent feature tables:\n{absent_feature_tables}")

    with open(_REFSEQ_ARCHIVE_FILES, "wb") as f: 
        pickle.dump(records, f, protocol=pickle.HIGHEST_PROTOCOL) 


def _main() -> None:
    # _get_records()

    with open(_REFSEQ_ARCHIVE_FILES, "rb") as f: 
        records = pickle.load(f) 

    undownloaded = 0
    downloaded = 0
    filtered = []
    for record in records:
        if not record.archive_file: continue
        if os.path.exists(join(archive_folder, record.archive_file.split("/")[-1])):
            downloaded += 1
        else:
            filtered.append(record)
            undownloaded += 1
    print("downloaded", downloaded, "undownloaded", undownloaded)

    with multiprocessing.Pool() as p:
        list(tqdm(p.imap_unordered(_download, filtered), total=len(filtered)))
     
if __name__ == "__main__":
    _main()