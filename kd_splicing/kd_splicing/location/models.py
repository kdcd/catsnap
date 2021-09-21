from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

from Bio.Seq import MutableSeq, Seq, reverse_complement

@dataclass
class LocationPart:
    __slots__ = "start", "end", "strand", "data"
    start: int
    end: int
    strand: Optional[int]
    data: Dict[str, Any]

    def __init__(self, start: int, end: int, strand: Optional[int] = None, data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.start = start
        self.end = end
        self.strand = strand
        self.data = data if data else {}

    def __contains__(self, loc: LocationPart) -> bool:
        return self.start <= loc.start and loc.start <= self.end \
            and self.start <= loc.end and loc.end <= self.end
    
    def __lt__(self, other: LocationPart) -> bool:
        if self.start < other.start:
            return True
        if self.start == other.start and self.end < other.end:
            return True
        return False

    def extract(self, seq: Seq) -> str:
        if isinstance(seq, MutableSeq):
            seq = seq.toseq()
        f_seq = seq[self.start:self.end]
        if self.strand == -1:
            try:
                f_seq = f_seq.reverse_complement()
            except AttributeError:
                assert isinstance(f_seq, str)
                f_seq = reverse_complement(f_seq)
        return str(f_seq)

    def length(self) -> int:
        return self.end - self.start


@dataclass
class Location:
    parts: List[LocationPart] = field(default_factory=list)

    def __contains__(self, loc: Location) -> bool:
        for loc_part in loc.parts:
            if not any(loc_part in self_part for self_part in self.parts):
                return False
        return True

    def extract(self, s: Seq) -> str:
        parts = [loc.extract(s) for loc in self.parts]
        f_seq = parts[0]
        for part in parts[1:]:
            f_seq += part
        return f_seq

    def length(self) -> int:
        return sum(
            p.end - p.start
            for p in self.parts
        )

    def sort(self) -> None:
        self.parts.sort()

    def __str__(self) -> str:
        s = "Location(=[\n"
        for p in self.parts:
            s += "  " + str(p) + '\n'
        s += "])"
        return s


@dataclass
class ConvertSegment:
    src_start: int
    src_end: int
    dst_start: int



@dataclass
class _ConvertEvent:
    class Type(Enum):
        END = 0
        START = 1

    src_pos: int
    event_type: Type
    dst_pos: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    

    def get_sort_tuple(self) -> Tuple[int, ...]:
        return (self.src_pos, self.event_type.value, 0 if self.dst_pos is not None else 1)


@dataclass
class LocationEvent:
    pos: int
    start: bool
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, right: LocationEvent) -> bool:
        return self.pos < right.pos or self.pos == right.pos and self.start and not right.start


@dataclass
class _EventWithId:
    id: uuid.UUID
    pos: int
    start: bool
    data: Optional[Dict[str, Any]] = None

    def __lt__(self, right: LocationEvent) -> bool:
        return self.pos < right.pos or self.pos == right.pos and self.start and not right.start

