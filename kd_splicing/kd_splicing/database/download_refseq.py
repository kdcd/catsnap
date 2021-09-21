import os
from os.path import join, isfile
from urllib.request import urlopen, urlretrieve

from tqdm import tqdm
from kd_common import logutil, pathutil
from kd_splicing import paths

from bs4 import BeautifulSoup
import multiprocessing
import pickle

logger = logutil.get_logger(__name__)


root = "https://ftp.ncbi.nlm.nih.gov/refseq/release/plant/"
# timestamp = pathutil.get_timestamp_str()
timestamp = "2021_03_01_20_44_04"
refseq_folder = pathutil.create_folder(paths.FOLDER_REFSEQ, timestamp)
archive_folder = pathutil.create_folder(refseq_folder, "archive")
feature_tables_folder = pathutil.create_folder(refseq_folder, "feature_tables")
_REFSEQ_ARCHIVE_FILES = join(refseq_folder, "refseq_archive_files.pkl")

def _download(href: str) -> None:
    def try_download():
        logger.info(f"downloading file {href}")
        urlretrieve(href, archive_file_path)
    archive_file_path = join(archive_folder, href.split("/")[-1])
    try:
        try:
            try:
                try_download()
            except Exception as e:
                logger.exception(f"Couldn't download url first time {href}")
                try_download()
        except Exception as e:
            logger.exception(f"Couldn't download url second time {href}")
            os.remove(archive_file_path)
    except Exception as e:
        logger.exception(f"Couldn't remove file {archive_file_path}")

def _get_hrefs() -> None:
    html = urlopen(root).read().decode('utf-8')
    soup = BeautifulSoup(html, features="html.parser")

    hrefs = [
        root + a["href"]
        for a in soup.find_all('a', href=True) 
        if a['href'].endswith("genomic.gbff.gz")
    ]
  
    with open(_REFSEQ_ARCHIVE_FILES, "wb") as f: 
        pickle.dump(hrefs, f, protocol=pickle.HIGHEST_PROTOCOL) 


def _main() -> None:
    _get_hrefs()

    with open(_REFSEQ_ARCHIVE_FILES, "rb") as f: 
        hrefs = pickle.load(f) 

    undownloaded = 0
    downloaded = 0
    filtered = []
    for href in hrefs:
        if os.path.exists(join(archive_folder, href.split("/")[-1])):
            downloaded += 1
        else:
            filtered.append(href)
            undownloaded += 1
    print("downloaded", downloaded, "undownloaded", undownloaded)

    with multiprocessing.Pool() as p:
        list(tqdm(p.imap_unordered(_download, filtered), total=len(filtered)))
     
if __name__ == "__main__":
    _main()