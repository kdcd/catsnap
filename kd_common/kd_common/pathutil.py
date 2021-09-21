import os
import re
import shutil
from datetime import datetime
from os.path import join, basename, exists, abspath, dirname
from typing import List, Optional, Tuple


def get_timestamp_str() -> str:
    return datetime.now().strftime("%Y_%m_%d_%H_%M_%S")


def create_folder(*args: str) -> str:
    path = join(*args)
    if not exists(path):
        os.makedirs(path)
    return path


def reset_folder(*args: str) -> None:
    path = join(*args)
    if exists(path):
        shutil.rmtree(path)
    create_folder(path)


def get_sub_directories(directory: str) -> List[str]:
    return [
        os.path.join(directory, o)
        for o in os.listdir(directory)
        if os.path.isdir(os.path.join(directory, o))
    ]


def get_sub_files(directory: str) -> List[str]:
    return [
        os.path.join(directory, o)
        for o in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, o))
    ]


def file_list(folder: str, extension: Optional[str] = None, prefix: Optional[str] = None, absolute: bool = True) -> List[str]:
    result = []
    for f in os.listdir(folder):
        if extension and not f.endswith(extension):
            continue
        if prefix and not f.startswith(prefix):
            continue
        if absolute:
            f = join(folder, f)
        result.append(f)

    return result


TIMESTAMP_STR = get_timestamp_str()

FOLDER_PROJECT_ROOT = abspath(join(__file__, "..", ".."))
FOLDER_PROJECTS_ROOT = abspath(join(__file__, "..", "..", ".."))
FOLDER_CONFIG = join(FOLDER_PROJECT_ROOT, "config")
FOLDER_GOOGLE = join(FOLDER_CONFIG, "google")
