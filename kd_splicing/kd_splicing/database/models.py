from __future__ import annotations

from Bio.Seq import MutableSeq, Seq, reverse_complement

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Mapping

import uuid
from kd_splicing.location.models import Location
from kd_common import logutil

_logger = logutil.get_logger(__name__)


@dataclass
class Gene:
    __slots__ = "uuid", "record_uuid", "locus_tag", "gene_id", "db_xref", "location"
    uuid: uuid.UUID
    record_uuid: uuid.UUID
    locus_tag: Optional[str]
    gene_id: Optional[str]
    db_xref: Optional[str]
    location: Location


@dataclass
class Isoform:  
    __slots__ = "uuid", "gene_uuid", "protein_id", "product", "location", "translation", "src_gene_uuid", "rna_uuid"
    uuid: uuid.UUID
    gene_uuid: uuid.UUID
    protein_id: Optional[str]
    product: Optional[str]
    location: Location
    translation: str
    src_gene_uuid: Optional[uuid.UUID]
    rna_uuid: Optional[uuid.UUID]

@dataclass
class RNA:
    __slots__ = "uuid", "gene_uuid", "transcript_id", "location", "src_gene_uuid"
    uuid: uuid.UUID
    gene_uuid: uuid.UUID
    transcript_id: Optional[str]
    location: Location
    src_gene_uuid: Optional[uuid.UUID]

@dataclass
class DBFile:
    __slots__ = "uuid", "src_gb_file", "db_name"
    uuid: uuid.UUID
    src_gb_file: str
    db_name: str


@dataclass
class Record:
    __slots__ = "uuid", "file_uuid", "sequence_id", "organism", "taxonomy"
    uuid: uuid.UUID
    file_uuid: uuid.UUID
    sequence_id: str
    organism: str
    taxonomy: List[str]


@dataclass
class DBPart:
    files: Dict[uuid.UUID, DBFile] = field(default_factory=dict)
    records: Dict[uuid.UUID, Record] = field(default_factory=dict)
    isoforms: Dict[uuid.UUID, Isoform] = field(default_factory=dict)
    rnas: Dict[uuid.UUID, RNA] = field(default_factory=dict)
    genes: Dict[uuid.UUID, Gene] = field(default_factory=dict)

    stats: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: List[str] = field(default_factory=list)

    def warn(self, s: str) -> None:
        _logger.warn(s)
        self.errors.append("[WARN]: " + s)

    def exception(self, s: str) -> None:
        _logger.exception(s)
        self.errors.append("[ERROR]: " + s)

@dataclass
class DB:
    files: Dict[uuid.UUID, DBFile] = field(default_factory=dict)
    records: Dict[uuid.UUID, Record] = field(default_factory=dict)
    isoforms: Dict[uuid.UUID, Isoform] = field(default_factory=dict)
    rnas: Dict[uuid.UUID, RNA] = field(default_factory=dict)
    genes: Dict[uuid.UUID, Gene] = field(default_factory=dict)

    stats: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: List[str] = field(default_factory=list)

    protein_id_to_isoform: Optional[Mapping[str, uuid.UUID]] = None
    isoform_to_duplicates: Optional[Mapping[uuid.UUID, List[uuid.UUID]]] = None

