from dataclasses import dataclass
import uuid
from typing import List, Tuple, Mapping, Set

from kd_splicing.database.models import DB
from kd_splicing.location.models import Location, LocationPart
from kd_splicing.location.utils import bounding_box, intersection, union


def _distance(a: LocationPart, b: LocationPart) -> int:
    return min(
        abs(a.start - b.end),
        abs(a.end - b.start),
    )


def get_as_types(a: Location, b: Location, source_parts: bool = False, debug: bool = False) -> Tuple[Tuple[str, ...], ...]:
    loc = union(a, b)
    if not loc.parts:
        return tuple()

    parts = loc.parts
    if loc.parts[0].strand == -1:
        parts = parts[::-1]
    if debug:
        for p in parts:
            print(p)
    
    begin = 0
    while begin + 1 < len(parts) and len(parts[begin].data["source"]) == 1 and len(parts[begin + 1].data["source"]) == 1:
        begin += 1

    end = len(parts)
    while end - 2 >= 0 and len(parts[end - 1].data["source"]) == 1 and len(parts[end - 2].data["source"]) == 1:
        end -= 1

    as_types: List[List[str]] = []
    count_intron_regions = 0
    for i in range(begin, end):
        part = parts[i]

        if len(part.data["source"]) != 1:
            count_intron_regions = 0
            continue
        count_intron_regions += 1
        if count_intron_regions == 1:
            as_types.append([])

        prev_part = None
        if i - 1 >= begin:
            prev_part = parts[i - 1]
        next_part = None
        if i + 1 < end:
            next_part = parts[i + 1]
        
        if prev_part and next_part:
            if _distance(part, prev_part) == 0 and _distance(part, next_part) == 0:
                as_types[-1].append(("IR", next(iter(part.data["source_part"]))))
            elif _distance(part, prev_part) == 0 and _distance(part, next_part) != 0:
                as_types[-1].append(("AltD", next(iter(part.data["source_part"]))))
            elif _distance(part, prev_part) != 0 and _distance(part, next_part) == 0:
                as_types[-1].append(("AltA", next(iter(part.data["source_part"]))))
            else:
                as_types[-1].append(("ExS", next(iter(part.data["source_part"]))))
        elif prev_part and not next_part:
            as_types[-1].append(("AltF", next(iter(part.data["source_part"]))))
            pass
        elif not prev_part and next_part:
            as_types[-1].append(("AltS", next(iter(part.data["source_part"]))))
            pass
        else:
            as_types[-1].append(("Undefined", next(iter(part.data["source_part"]))))

    if not source_parts:
        as_types = [[tup[0] for tup in intron_as_types] for intron_as_types in as_types]
    
    return tuple(tuple(intron_as_types) for intron_as_types in as_types)

def get_isoforms_as_types(
    db: DB, 
    isoform_to_duplicates: Mapping[uuid.UUID, List[uuid.UUID]], 
    a_uuid: uuid.UUID, 
    b_uuid: uuid.UUID, 
    debug: bool=False
) -> Set[Tuple[Tuple[str, ...], ...]]:
    result = set()
    for iso_a_duplicate in isoform_to_duplicates[a_uuid]:
        for iso_b_duplicate in isoform_to_duplicates[b_uuid]:
            iso_a = db.isoforms[iso_a_duplicate]
            iso_b = db.isoforms[iso_b_duplicate]
            if not iso_a.rna_uuid or not iso_b.rna_uuid:
                continue
            rna_a = db.rnas[iso_a.rna_uuid]
            rna_b = db.rnas[iso_b.rna_uuid]
            if debug:
                print(iso_a.protein_id)
                print(iso_b.protein_id)
                print(iso_a.location)
                print(rna_a.location)
                print(iso_b.location)
                print(rna_b.location)
            iso_union = bounding_box(iso_a.location.parts + iso_b.location.parts)
            rna_a_location = intersection(rna_a.location, iso_union)
            rna_b_location = intersection(rna_b.location, iso_union)
            as_types = get_as_types(rna_a_location, rna_b_location, debug)
            if debug:
                print(as_types)
            if as_types:
                result.add(as_types)
    return result

@dataclass
class IsoformsTypesResults:
    rna_a_location: Location
    rna_b_location: Location
    as_types: Tuple[Tuple[Tuple[str, str], ...], ...]

def get_isoforms_as_types_no_duplicates(
    db: DB, 
    a_uuid: uuid.UUID, 
    b_uuid: uuid.UUID, 
    debug: bool=False
) -> IsoformsTypesResults:
    try:
        iso_a = db.isoforms[a_uuid]
        iso_b = db.isoforms[b_uuid]
        rna_a = db.rnas[iso_a.rna_uuid]
        rna_b = db.rnas[iso_b.rna_uuid]
        iso_union = bounding_box(iso_a.location.parts + iso_b.location.parts)
        rna_a_location = intersection(rna_a.location, iso_union)
        rna_b_location = intersection(rna_b.location, iso_union)
        as_types = get_as_types(rna_a_location, rna_b_location, source_parts = True, debug=debug)
        return IsoformsTypesResults(
            rna_a_location=rna_a_location,
            rna_b_location=rna_b_location,
            as_types = as_types,
        )
    except:
        return None
