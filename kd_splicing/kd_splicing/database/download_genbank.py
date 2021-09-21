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


root = "https://ftp.ncbi.nlm.nih.gov/genomes/genbank/plant/"
# timestamp = pathutil.get_timestamp_str()
timestamp = "2021_02_16_20_16_27"
genbank_folder = pathutil.create_folder(paths.FOLDER_GENBANK, timestamp)
archive_folder = pathutil.create_folder(genbank_folder, "archive")
reports_folder = pathutil.create_folder(genbank_folder, "reports")
records_folder = pathutil.create_folder(genbank_folder, "records")
feature_tables_folder = pathutil.create_folder(genbank_folder, "feature_tables")
_GENBANK_ARCHIVE_FILES = join(genbank_folder, "genbank_archive_files.pkl")

@dataclass
class Record:
    plant_name: str
    archive_file: Optional[str] = None
    report_file: Optional[str] = None
    feature_table: Optional[str] = None

def _download(record: Record) -> None:
    if record.archive_file is None or record.report_file is None:
        return
    archive_file_path = join(archive_folder, record.archive_file.split("/")[-1])
    report_file_path = join(reports_folder, record.report_file.split("/")[-1])
    feature_tables_path = join(feature_tables_folder, record.feature_table.split("/")[-1])
    try:
        try:
            try:
                # if not os.path.exists(archive_file_path):
                #     logger.info(f"downloading file {record.archive_file}")
                #     urlretrieve(record.archive_file, archive_file_path)
                if not os.path.exists(report_file_path):
                    logger.info(f"downloading file {record.report_file}")
                    urlretrieve(record.report_file, report_file_path)
                if not os.path.exists(feature_tables_path):
                    logger.info(f"downloading file {record.feature_table}")
                    urlretrieve(record.feature_table, feature_tables_path)
            except Exception as e:
                logger.exception(f"Couldn't download url first time")
                # if not os.path.exists(archive_file_path):
                #     logger.info(f"downloading file {record.archive_file}")
                #     urlretrieve(record.archive_file, archive_file_path)
                if not os.path.exists(report_file_path):
                    logger.info(f"downloading file {record.report_file}")
                    urlretrieve(record.report_file, report_file_path)
                if not os.path.exists(feature_tables_path):
                    logger.info(f"downloading file {record.feature_table}")
                    urlretrieve(record.feature_table, feature_tables_path)
        except Exception as e:
            logger.exception(f"Couldn't download url second time {record.archive_file}")
            # os.remove(archive_file_path)
    except Exception as e:
        logger.exception(f"Couldn't remove file {archive_file_path}")

def _get_archive_file(plant_name: str) -> Record:
    try:
        # print(plant_name)
        plant = os.path.join(root, plant_name)
        # print(representative)

        try:
            html = urlopen(plant).read().decode('utf-8')    
        except Exception as e:
            logger.exception(f"Not found {plant}")
            return Record(plant_name)
        soup = BeautifulSoup(html, features="html.parser")
        hrefs = [a['href'] for a in soup.find_all('a', href=True)]
        references = [ref for ref in ["reference/", "representative/", "latest_assembly_versions/"] if any(ref in h for h in hrefs)]
        if not references:
            logger.exception(f"No References {plant}")
            return Record(plant_name)

        url_reference = os.path.join(plant, references[0])

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
        assembly_report = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith("assembly_report.txt")][0]
        record = Record(plant_name, url + archive_file, url + assembly_report) 

        feature_tables = [a['href'] for a in soup.find_all('a', href=True) if a['href'].endswith("feature_table.txt.gz")]
        if feature_tables:
            record.feature_table = url + feature_tables[0]
        return record
    except urllib.error.HTTPError as e:
        logger.exception(f"Not found plant name {plant_name}. Reason{e.reason}")
    except Exception as e:
        logger.exception(f"Not found plant name {plant_name}")

    return Record(plant_name)

def _record_path(plant_name: str) -> str:
    return os.path.join(records_folder, plant_name.strip("/") + ".pkl")

def _archive_files() -> None:
    html = urlopen(root).read().decode('utf-8')
    soup = BeautifulSoup(html, features="html.parser")

    plant_names = [
        a["href"]
        for a in soup.find_all('a', href=True) 
    ][1:]

    filtered = []
    for plant_name in plant_names:
        if os.path.exists(_record_path(plant_name)): continue
        filtered.append(plant_name)

    print("All", len(plant_names), "filtered", len(filtered))

    # result = []
    # for plant_name in tqdm(plant_names):
    #     print(_get_archive_file(plant_name))

    with get_context("spawn").Pool() as p:
        records = list(tqdm(p.imap_unordered(_get_archive_file, filtered), total=len(filtered)))

    absent_archive_files = [
        record.plant_name
        for record in records
        if record.archive_file is None
    ]
    logger.warning(f"Absent archive files:\n{absent_archive_files}")

    absent_report_files = [
        record.plant_name
        for record in records
        if record.report_file is None
    ]
    logger.warning(f"Absent report files:\n{absent_report_files}")

    for record in records:
        if not record.archive_file: continue
        with open(_record_path(record.plant_name), "wb") as f: 
            pickle.dump(record, f, protocol=pickle.HIGHEST_PROTOCOL) 


def _main() -> None:
    # _archive_files()

    records = []
    for record_file in pathutil.file_list(records_folder):
        with open(record_file, "rb") as f: 
            records.append(pickle.load(f) )

    filtered_records = []
    
    absent_report = 0
    absent_archive = 0
    not_downloaded_archive = 0
    downloaded_archive = 0
    absent_feature_table = 0
    not_downloaded_feature_table = 0
    downloaded_feature_table = 0
    for record in records:
        absent_report += record.report_file is None
        if record.archive_file is None or record.report_file is None:
            print(record.plant_name)
            continue
        archive_file_path = join(archive_folder, record.archive_file.split("/")[-1]) if record.archive_file else ""
        report_file_path = join(reports_folder, record.report_file.split("/")[-1]) if record.report_file else ""
        feature_table_path = join(feature_tables_folder, record.feature_table.split("/")[-1]) if record.feature_table else ""
        if not ((record.archive_file is None or os.path.exists(archive_file_path)) and \
           (record.report_file is None or os.path.exists(report_file_path)) and \
           (record.feature_table is None or os.path.exists(feature_table_path))):
            filtered_records.append(record)

        if record.feature_table is None:
            absent_feature_table += 1
        else:
            if os.path.exists(feature_table_path):
                downloaded_feature_table += 1
            else:
                not_downloaded_feature_table += 1
        if record.archive_file is None:
            absent_archive += 1
        else:
            if os.path.exists(archive_file_path):
                downloaded_archive += 1
            else:
                not_downloaded_archive += 1


    print("Records: ", len(records), "filtered records", len(filtered_records), "absent_archive", absent_archive, "absent_report", absent_report)
    print("absent_archive", absent_archive, "not_downloaded_archive", not_downloaded_archive, "downloaded_archive", downloaded_archive)
    print("absent_feature_table", absent_feature_table, "not_downloaded_feature_table", not_downloaded_feature_table, "downloaded_feature_table", downloaded_feature_table)

    # with multiprocessing.Pool() as p:
    #     list(tqdm(p.imap_unordered(_download, filtered_records), total=len(filtered_records)))
     
if __name__ == "__main__":
    _main()