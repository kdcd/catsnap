from collections import defaultdict
import uuid
from copy import copy
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any, Set

from kd_splicing.location.models import (ConvertSegment, Location, _EventWithId,
                                         LocationPart, _ConvertEvent, LocationEvent)


def get_convert_to_local_segments(loc: Location) -> List[ConvertSegment]:
    if not loc.parts:
        return []
    loc.sort()
    current_len = 0
    result = []
    strand = loc.parts[0].strand
    for part in loc.parts[::strand]:
        result.append(ConvertSegment(
            src_start=part.start,
            src_end=part.end,
            dst_start=current_len,
        ))
        current_len += part.end - part.start
    return result


def convert_location(loc: Location, segments: List[ConvertSegment]) -> Location:
    if not loc.parts:
        return loc
    reverse = loc.parts[0].strand == -1
    events = []
    for part in loc.parts:
        events.append(_ConvertEvent(
            src_pos=part.start if not reverse else -part.start,
            event_type=_ConvertEvent.Type.START if not reverse else _ConvertEvent.Type.END,
            data=part.data,
        ))
        events.append(_ConvertEvent(
            src_pos=part.end if not reverse else -part.end,
            event_type=_ConvertEvent.Type.END if not reverse else _ConvertEvent.Type.START,
            data=part.data,
        ))

    for s in segments:
        events.append(_ConvertEvent(
            src_pos=s.src_start if not reverse else -s.src_start,
            event_type=_ConvertEvent.Type.START if not reverse else _ConvertEvent.Type.END,
            dst_pos=s.dst_start if not reverse else None,
        ))
        events.append(_ConvertEvent(
            src_pos=s.src_end if not reverse else -s.src_end,
            event_type=_ConvertEvent.Type.END if not reverse else _ConvertEvent.Type.START,
            dst_pos=s.dst_start if reverse else None,
        ))

    events.sort(key=lambda e: e.get_sort_tuple())
    k = 0
    data: Dict[str, Any] = {}
    prev_src_pos = 0
    prev_dst_pos = 0
    dst_start_pos = None
    result = Location()
    for e in events:
        if e.dst_pos is not None:
            prev_src_pos = e.src_pos
            prev_dst_pos = e.dst_pos

        if e.event_type == _ConvertEvent.Type.START:
            k += 1
            if e.data:
                data.update(e.data)
        else:
            k -= 1

        if e.event_type == _ConvertEvent.Type.START and k == 2:
            dst_start_pos = e.src_pos - prev_src_pos + prev_dst_pos
        elif e.event_type == _ConvertEvent.Type.END and dst_start_pos is not None:
            result.parts.append(LocationPart(
                start=dst_start_pos,
                end=e.src_pos - prev_src_pos + prev_dst_pos,
                strand=None,
                data=copy(data),
            ))
            dst_start_pos = None
    return result


def relative_to_location(loc: Location, other: Location) -> Location:
    segments = get_convert_to_local_segments(other)
    return convert_location(loc, segments)


def get_alignment_segments(s: str, src_from: int, src_len: int) -> List[ConvertSegment]:
    segments = [
        ConvertSegment(
            src_start=0,
            src_end=src_from,
            dst_start=-src_from,
        )
    ]
    src_pos = src_from
    dst_pos = 0
    src_start = src_pos
    dst_start = dst_pos
    prev = "-"
    for c in s:
        if c != "-":
            if prev == '-':
                src_start = src_pos
                dst_start = dst_pos
            src_pos += 1
        else:
            if prev != '-':
                segments.append(ConvertSegment(
                    src_start=src_start,
                    src_end=src_pos,
                    dst_start=dst_start,
                ))
                src_start = src_pos
                dst_start = dst_pos
        dst_pos += 1
        prev = c
    if prev == "-":
        dst_start = dst_pos
    segments.append(ConvertSegment(
        src_start=src_start,
        src_end=src_len,
        dst_start=dst_start,
    ))
    return segments


def relative_to_alignment(loc: Location, alignment: str, query_from: int, query_len: int) -> Location:
    segments = get_alignment_segments(alignment, query_from, query_len)
    return convert_location(loc, segments)


def nucleotide_to_amino(loc: Location) -> Location:
    result = Location()
    for part in loc.parts:
        result.parts.append(LocationPart(
            start=int(math.ceil(part.start / 3.)),
            end=int(math.ceil(part.end / 3.)),
            strand=part.strand,
            data=part.data,
        ))
    return result


def _location_to_events(loc: Location) -> List[LocationEvent]:
    events = []
    for part in loc.parts:
        events.append(LocationEvent(
            pos=part.start,
            start=True,
            data=part.data,
        ))
        events.append(LocationEvent(
            pos=part.end,
            start=False,
            data={key: None for key in part.data.keys()},
        ))
    return events


def _location_to_events_with_ids(loc: Location) -> List[_EventWithId]:
    events = []
    for part in loc.parts:
        event_id = uuid.uuid4()
        events.append(_EventWithId(
            id=event_id,
            pos=part.start,
            start=True,
            data=part.data,
        ))
        events.append(_EventWithId(
            id=event_id,
            pos=part.end,
            start=False,
        ))
    return events


def symmetric_difference(a: Location, b: Location) -> Location:
    if not b.parts:
        return a
    if not a.parts:
        return b
    assert a.parts[0].strand == b.parts[0].strand
    strand = a.parts[0].strand
    events = _location_to_events_with_ids(a) + _location_to_events_with_ids(b)
    events.sort()

    pos = 0
    current_events: Dict[uuid.UUID, Any] = {}
    result = Location()
    for e in events:
        if len(current_events) == 1 and e.pos > pos:
            result.parts.append(LocationPart(
                start=pos,
                end=e.pos,
                strand=strand,
                data=next(iter(current_events.values())),
            ))

        if e.start:
            current_events[e.id] = e.data
        else:
            del current_events[e.id]

        if len(current_events) == 1:
            pos = e.pos
    return result


def intersection(a: Location, b: Location) -> Location:
    if not a.parts or not b.parts:
        return Location()
    events = _location_to_events(a) + _location_to_events(b)
    events.sort()

    pos = 0
    data: Dict[str, Any] = {}
    count = 0
    result = Location()
    for e in events:
        if count == 2 and e.pos > pos:
            result.parts.append(LocationPart(
                start=pos,
                end=e.pos,
                strand=a.parts[0].strand,
                data=copy(data),
            ))

        if e.start:
            count += 1
            if e.data:
                data.update(e.data)
        else:
            count -= 1

        if count == 2:
            pos = e.pos
    return result


def _location_to_union_events(loc: Location, source: str) -> List[LocationEvent]:
    events = []
    for idx, part in enumerate(loc.parts):
        events.append(LocationEvent(
            pos=part.start,
            start=True,
            data={
                "source": source,
                "source_part": f"{source}_{idx}" 
            },
        ))
        events.append(LocationEvent(
            pos=part.end,
            start=False,
            data={
                "source": source,
                "source_part": f"{source}_{idx}"
            },
        ))
    return events


def union(a: Location, b: Location) -> Location:
    if not a.parts and not b.parts:
        return Location()
    strand = a.parts[0].strand if a.parts else b.parts[0].strand
    events = _location_to_union_events(
        a, "a") + _location_to_union_events(b, "b")
    events.sort(key = lambda e: (e.pos, e.start))

    pos = 0
    source: Set[str] = set()
    source_part: Set[str] = set()
    result = Location()
    for e in events:
        if len(source) > 0 and e.pos > pos:
            result.parts.append(LocationPart(
                start=pos,
                end=e.pos,
                strand=strand,
                data={
                    "source": copy(source),
                    "source_part": copy(source_part),
                },
            ))
            pos = e.pos

        assert e.data
        if e.start:
            pos = e.pos
            source.add(e.data["source"])
            source_part.add(e.data["source_part"])
        else:
            # if e.data["source"] not in source:
            #     print(e)
            source.remove(e.data["source"])
            source_part.remove(e.data["source_part"])

    return result


def merge(loc: Location) -> Location:
    if not loc.parts:
        return loc
    assert loc.parts[0].strand != -1
    result = Location([copy(loc.parts[0])])
    for part in loc.parts[1:]:
        if result.parts[-1].end == part.start:
            result.parts[-1].end = part.end
        else:
            result.parts.append(copy(part))
    return result


def bounding_box(loc_parts: List[LocationPart]) -> Location:
    if not loc_parts:
        return Location()
    min_pos = loc_parts[0].start
    max_pos = loc_parts[0].start
    strand = loc_parts[0].strand
    for part in loc_parts:
        min_pos = min(min_pos, part.start)
        max_pos = max(max_pos, part.start)
        min_pos = min(min_pos, part.end)
        max_pos = max(max_pos, part.end)
    return Location([
        LocationPart(min_pos, max_pos, strand)
    ])

def is_equal(a: Location, b: Location) -> bool:
    if len(a.parts) != len(b.parts):
        return False
    for i in range(len(a.parts)):
        first = a.parts[i]
        second = b.parts[i]
        if not (first.start == second.start and first.end == second.end and first.strand == second.strand):
            return False
    return True
