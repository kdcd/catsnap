from pathlib import Path
import datetime
import shutil
from typing import List, Optional


def get_timestamp_str() -> str:
    return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

def list_dir(folder: Path, extension: Optional[str] = None, prefix: Optional[str] = None, absolute: bool = True) -> List[Path]:
    result = []
    for f in folder.iterdir():
        if extension and not f.name.endswith(extension):
            continue
        if prefix and not f.name.startswith(prefix):
            continue
        if absolute:
            f = f.absolute()
        result.append(f)

    return result

def create_folder(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def reset_folder(p: Path) -> None:
    if p.exists():
        shutil.rmtree(p)
    create_folder(p)

TIMESTAMP_STR = get_timestamp_str()

FOLDER_PROJECT_ROOT = Path(__file__).parent.parent.absolute()
FOLDER_PROJECTS_ROOT = Path(__file__).parent.parent.parent.absolute()
FOLDER_CONFIG = FOLDER_PROJECT_ROOT / "config"
FOLDER_GOOGLE = FOLDER_CONFIG / "google"
