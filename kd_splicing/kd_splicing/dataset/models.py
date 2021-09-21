import uuid
from dataclasses import dataclass, field
from typing import Mapping, Set, Dict, List, Tuple

from kd_splicing.models import IsoformTuple
from collections import defaultdict


@dataclass
class DatasetMatch:
    query: IsoformTuple
    hit: IsoformTuple
    positive: bool


@dataclass
class Dataset:
    matches: List[DatasetMatch]
