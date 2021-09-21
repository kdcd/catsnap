from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Mapping, Any, Optional, Sequence
import data
import pydantic
from pathlib import Path

from kd_splicing import database

from kd_common import logutil, strutil

_logger = logutil.get_logger(__name__)



@dataclass(frozen=True)
class IsoformTuple:
    __slots__ = "a", "b"
    a: uuid.UUID
    b: uuid.UUID

    def __getstate__(self) -> Any:
        return dict(
            (slot, getattr(self, slot))
            for slot in self.__slots__
            if hasattr(self, slot)
        )

    def __setstate__(self, state: Any) -> None:
        for slot, value in state.items():
            object.__setattr__(self, slot, value) # <- use object.__setattr__

    def __lt__(self, other:IsoformTuple) -> bool:
        if self.a < other.a:
            return True
        if self.a ==other.a and self.b < other.b:
            return True
        return False


@dataclass
class Match:
    query_isoforms: IsoformTuple
    hit_isoforms: IsoformTuple
    
    hit_organism: str = ""
    hit_db_name: str = ""

    positive: Optional[bool] = None
    predicted_positive: bool = False
    predicted_positive_probability: float = 0

    isoform_blast_score: float = 0
    splicing_difference: float = 0
    splicing_similarity: float = 0
    splicing_dissimilarity: float = 0

@dataclass
class SimpleMatch:
    __slots__ = "hit_isoforms", "predicted_positive", "predicted_positive_probability"
    hit_isoforms: IsoformTuple
    predicted_positive: bool
    predicted_positive_probability: float


@dataclass
class Queries:
    tuples: List[IsoformTuple]
    isoforms: List[uuid.UUID]
    isoform_to_idx: Mapping[uuid.UUID, int]
    isoform_to_group: Mapping[uuid.UUID, int]
    isoform_to_file: Mapping[uuid.UUID, str] = field(default_factory=dict)


class FormattedResultsItem(pydantic.BaseModel):
    name: str
    sequence: str

    class Config:
        alias_generator = strutil.to_camel
        allow_population_by_field_name = True

    

class FormattedResultsQuery(pydantic.BaseModel):
    query: str
    items: List[FormattedResultsItem]

    class Config:
        alias_generator = strutil.to_camel
        allow_population_by_field_name = True

    def to_file(self, file_path: str) -> None:
        with open(file_path, "w") as f:
            for item in self.items:
                f.write(">" + item.name + "\n")
                f.write(item.sequence + "\n")

    @staticmethod
    def from_file(file_path: str) -> FormattedResultsQuery:
        query = FormattedResultsQuery.construct(
            query=file_path.split("/")[-1].split(".fasta")[0],
            items=[]
        )
        with open(file_path, "r") as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                name = lines[i][1:].strip()
                i += 1
                sequence = ""
                while i < len(lines) and not lines[i].startswith(">"):
                    sequence += lines[i].strip()
                    i += 1
                query.items.append(FormattedResultsItem.construct(
                    name=name,
                    sequence=sequence
                ))
                
        return query


class FormattedResults(pydantic.BaseModel):
    query_results: List[FormattedResultsQuery]

    class Config:
        alias_generator = strutil.to_camel
        allow_population_by_field_name = True

    @staticmethod
    def from_files(files_path: List[str]) -> FormattedResults:
        results = FormattedResults.construct(query_results=[])
        for file_path in files_path:
            results.query_results.append(FormattedResultsQuery.from_file(file_path))
        return results

class SearchStatus(pydantic.BaseModel):
    progress: int
    description: str

    def set(self, progress: int, description: str) -> None:
        _logger.info(description + " progress")
        self.progress = progress
        self.description = description


class AlignStatus(pydantic.BaseModel):
    progress: int

    def set(self, progress: int, description: str) -> None:
        self.progress = progress
