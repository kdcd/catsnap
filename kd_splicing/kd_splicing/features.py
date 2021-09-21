from __future__ import annotations

import itertools
import multiprocessing
import os
import pickle
import string
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from functools import partial
from itertools import chain
from multiprocessing import get_context
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Any
from copy import copy
from Bio.SubsMat import MatrixInfo

from tqdm import tqdm

from kd_common import logutil, pathutil
from kd_splicing import blast, database, location, ml, models, paths
from kd_splicing.location.models import ConvertSegment, Location, LocationPart
from kd_splicing.location.utils import (union, convert_location,
                                        get_alignment_segments, intersection,
                                        merge, nucleotide_to_amino,
                                        relative_to_alignment,
                                        relative_to_location,
                                        symmetric_difference)
from kd_splicing.models import IsoformTuple, Match, Queries, SimpleMatch

_logger = logutil.get_logger(__name__)

_SCORE_TABLE = {
    **{letter: 1 for letter in string.ascii_uppercase},
    "+": 1,
}

def _build_matrix() -> Mapping[Tuple[str, str], float]:
    result: Dict[Tuple[str, str], float] = {}
    for tup, score in MatrixInfo.blosum30.items():
        if score < 0:
            score = 0
        result[(tup[0], tup[1])] = score
        result[(tup[1], tup[0])] = score
    return result

_SCORE_MATRIX = _build_matrix()

def count_all_matches(midline: str) -> float:
    count = 0.
    for m in midline:
        count += _SCORE_TABLE.get(m, 0)
    return count

def count_matches(loc: Location, midline: str) -> float:
    count = 0.
    for part in loc.parts:
        for i in range(part.start, part.end):
            if i >= 0 and i < len(midline):
                count += _SCORE_TABLE.get(midline[i], 0)
    return count

def evaluate_score(loc: Location, seq_a: str, seq_b: str, open_gap: float = 0, extend_gap: float = 0,
                   penalize_extend_when_opening: bool=False) -> float:
    openA = False
    openB = False
    if penalize_extend_when_opening:
        open_gap += extend_gap
    score = .0
    for part in loc.parts:
        for i in range(part.start, part.end):
            if not(i >= 0 and i < len(seq_a)):
                continue
            char_a = seq_a[i]
            char_b = seq_b[i]
            if char_a !='-' and char_b != '-':
                openA, openB = False, False
                score += _SCORE_MATRIX[(char_a, char_b)]
            elif char_a == '-':
                if not openA:
                    score += open_gap
                    openA = True
                    openB = False
                else:
                    score += extend_gap
            elif char_b == '-':
                if not openB:
                    score += open_gap
                    openB = True
                    openA = False
                else:
                    score += extend_gap
    return score


def convert_splicing(splicing: Location, loc: Location, translation_len: int) -> Location:
    converted = relative_to_location(splicing, loc)
    converted = nucleotide_to_amino(converted)
    converted = merge(converted)
    return converted


@dataclass
class CalcMatchContext:
    hit_a: blast.Hit
    hit_b: blast.Hit

    iso_a: uuid.UUID
    iso_b: uuid.UUID
    splicing_a: Location
    splicing_b: Location

    debug: bool = False


@dataclass
class CalcQuery:
    iso_a: uuid.UUID
    iso_a_len: int
    iso_a_location: database.models.Location
    iso_b: uuid.UUID
    iso_b_location: database.models.Location
    iso_b_len: int
    organism: str


@dataclass
class CalcQueriesContext:
    queries: List[CalcQuery]
    iso_to_hits: Mapping[uuid.UUID, List[blast.Hit]]
    q_iso_to_gene: Mapping[uuid.UUID, uuid.UUID]
    hit_tuple: Optional[IsoformTuple] = None
    debug: bool = False


@dataclass
class CalcBatch:
    result_path: str
    ctx: CalcQueriesContext


def _parallel_results_folder(launch_folder: str) -> str:
    return pathutil.create_folder(launch_folder, "parallel_results")


def _extend_splicing(loc: Location) -> None:
    if not loc.parts:
        return
    strand = loc.parts[0].strand
    a_splicing_length = 0
    b_splicing_length = 0
    for part in loc.parts[::strand]:
        if len(part.data["source"]) == 1:
            if "a" in part.data['source']:
                a_splicing_length += part.length()
            else:
                b_splicing_length += part.length()
            part.data["is_splicing"] = True
        elif a_splicing_length % 3 != b_splicing_length % 3:
            part.data["is_splicing"] = True
            a_splicing_length += part.length()
            b_splicing_length += part.length()
        else:
            part.data["is_splicing"] = False

def _add_directed_event_ids(loc: Location, name: str, direction: int) -> None:
    if not loc.parts:
        return
    event_id = 0
    is_prev_splicing = True
    strand = loc.parts[0].strand if loc.parts[0].strand is not None else 1

    for part in loc.parts[::direction * strand]:
        if not is_prev_splicing and part.data["is_splicing"]:
            event_id += 1
        if part.data["is_splicing"]:
            is_prev_splicing = True
            part.data[name] = event_id
        else:
            is_prev_splicing = False

def _add_event_ids(loc: Location) -> None:
    if not loc.parts:
        return
    _add_directed_event_ids(loc, "event_id_forward", 1)
    _add_directed_event_ids(loc, "event_id_backward", -1)
    for part in loc.parts:
        if part.data["is_splicing"]:
            part.data["event_id"] = part.data["event_id_forward"] + 100 * part.data["event_id_backward"] 

def _get_splicings_from_union(loc_union: Location) -> Tuple[Location, Location]:
    a = Location()
    b = Location()
    for union_part in loc_union.parts:
        if union_part.data["is_splicing"] and "a" in union_part.data["source"]:
            a.parts.append(copy(union_part))
        if union_part.data["is_splicing"] and "b" in union_part.data["source"]:
            b.parts.append(copy(union_part))
    return a, b

def _get_splicing(a: Location, b:Location) -> Tuple[Location, Location]:
    loc_union = union(a, b)
    _extend_splicing(loc_union)
    _add_event_ids(loc_union)
    return _get_splicings_from_union(loc_union)


def _loc_per_event(loc: Location, name: str) -> Mapping[int, Location]:
    result: Dict[int, Location] = defaultdict(Location)
    for p in loc.parts:
        result[p.data[name]].parts.append(p)
    return result


def _splicing_intersection_length_weight(length: int) -> float:
    _MIN_LENGTH = 20
    _MIN_W = 1
    _MAX_LENGTH = 100
    _MAX_W = 0.3
    if length < _MIN_LENGTH:
        return _MIN_W
    if length > _MAX_LENGTH:
        return _MAX_W
    x = (length - _MIN_LENGTH) / (_MAX_LENGTH - _MIN_LENGTH)
    return x * x * (_MAX_W - _MIN_W) + _MIN_W


def _normalize_length(length: int) -> float:
    _MIN_LENGTH = 10
    _MIN_W = 1
    _MAX_LENGTH = 100
    _MAX_W = 0.3
    if length < _MIN_LENGTH:
        return length / _MIN_W
    if length > _MAX_LENGTH:
        return length / _MAX_W
    x = float(length - _MIN_LENGTH) / (_MAX_LENGTH - _MIN_LENGTH)
    w = x * (_MAX_W - _MIN_W) + _MIN_W
    return length / w


def _calc_splicing_difference_per_event(
    m: Match,
    query_splicing_a: Location, 
    query_splicing_b: Location, 
    hit_splicing_a: Location, 
    hit_splicing_b: Location,
    symmetric_difference_a: Location, 
    symmetric_difference_b: Location,
    debug: bool
) -> None:
    if debug:
        print("_calc_splicing_difference_per_event")
        print("aligned_query_splicing_a", query_splicing_a)
        print("aligned_query_splicing_b", query_splicing_b)
        print("aligned_hit_splicing_a", hit_splicing_a)
        print("aligned_hit_splicing_b", hit_splicing_b)

    query_a_splicing_loc = _loc_per_event(query_splicing_a, "event_id")
    query_b_splicing_loc = _loc_per_event(query_splicing_b, "event_id")
    hit_a_splicing_loc = _loc_per_event(hit_splicing_a, "event_id")
    hit_b_splicing_loc = _loc_per_event(hit_splicing_b, "event_id")
    events = query_a_splicing_loc.keys() | query_b_splicing_loc.keys() | hit_a_splicing_loc.keys() | hit_b_splicing_loc.keys()

    if not events: 
        m.splicing_difference = 1
        return

    m.splicing_difference = 0
    for event_id in events:
        query_a_event_splicing = query_a_splicing_loc[event_id]
        query_b_event_splicing = query_b_splicing_loc[event_id]
        hit_a_event_splicing = hit_a_splicing_loc[event_id]
        hit_b_event_splicing = hit_b_splicing_loc[event_id]
        a_splicing_length = query_a_event_splicing.length() + hit_a_event_splicing.length()
        b_splicing_length = query_b_event_splicing.length() + hit_b_event_splicing.length()
        splicing_length = max(a_splicing_length, b_splicing_length)
        normalized_splicing_length = splicing_length

        a_event_difference = symmetric_difference(query_a_event_splicing, hit_a_event_splicing)
        b_event_difference = symmetric_difference(query_b_event_splicing, hit_b_event_splicing)

        a_difference = a_event_difference.length() / normalized_splicing_length if normalized_splicing_length else 1
        b_difference = b_event_difference.length() / normalized_splicing_length if normalized_splicing_length else 1
        m.splicing_difference = max(m.splicing_difference, a_difference + b_difference)

        if debug:
            print()
            print("Event id: ", event_id)
            print("_calc_splicing_difference_per_event")
            print("query_a_event_splicing", query_a_event_splicing)
            print("query_b_event_splicing", query_b_event_splicing)
            print("hit_a_event_splicing", hit_a_event_splicing)
            print("hit_b_event_splicing", hit_b_event_splicing)
            print("a_event_difference", a_event_difference)
            print("b_event_difference", b_event_difference)
            print("a_difference", a_difference)
            print("b_difference", b_difference)
            print("normalized_splicing_length", normalized_splicing_length)


###############
# Calc
###############


def calc_single(ctx: CalcMatchContext) -> Match:
    match = Match(
        query_isoforms=IsoformTuple(ctx.iso_a, ctx.iso_b),
        hit_isoforms=IsoformTuple(ctx.hit_a.iso_uuid, ctx.hit_b.iso_uuid),
        hit_organism=ctx.hit_a.organism,
        hit_db_name=ctx.hit_a.db_name,
    )

    hit_global_splicing_a, hit_global_splicing_b = _get_splicing(
        ctx.hit_a.iso_location, ctx.hit_b.iso_location)
    hit_splicing_a = convert_splicing(
        hit_global_splicing_a, ctx.hit_a.iso_location, ctx.hit_a.iso_len)
    hit_splicing_b = convert_splicing(
        hit_global_splicing_b, ctx.hit_b.iso_location, ctx.hit_b.iso_len)

    aligned_splicing_a = convert_location(
        ctx.splicing_a, ctx.hit_a.query_segments)
    aligned_hit_splicing_a = convert_location(
        hit_splicing_a, ctx.hit_a.hit_segments)
    aligned_splicing_b = convert_location(
        ctx.splicing_b, ctx.hit_b.query_segments)
    aligned_hit_splicing_b = convert_location(
        hit_splicing_b, ctx.hit_b.hit_segments)

    splicing_intersection_a = intersection(
        aligned_splicing_a, aligned_hit_splicing_a)
    splicing_intersection_b = intersection(
        aligned_splicing_b, aligned_hit_splicing_b)
    splicing_intersection_a_length = splicing_intersection_a.length()
    splicing_intersection_b_length = splicing_intersection_b.length()

    ########################
    # Splicing difference
    ########################

    splicing_symmetric_difference_a = symmetric_difference(
        aligned_splicing_a, aligned_hit_splicing_a)
    splicing_symmetric_difference_b = symmetric_difference(
        aligned_splicing_b, aligned_hit_splicing_b)
    if ctx.debug:
        print("<---------------------------------->")
        print("ctx.hit_a.iso_location", ctx.hit_a.iso_location)
        print("ctx.hit_b.iso_location", ctx.hit_b.iso_location)
        print("hit_global_splicing_a", hit_global_splicing_a)
        print("hit_global_splicing_b", hit_global_splicing_b)
        print("hit_splicing_a", hit_splicing_a)
        print("hit_splicing_b", hit_splicing_b)

    _calc_splicing_difference_per_event(
        m=match, 
        query_splicing_a=aligned_splicing_a,
        query_splicing_b=aligned_splicing_b,
        hit_splicing_a=aligned_hit_splicing_a,
        hit_splicing_b=aligned_hit_splicing_b,
        symmetric_difference_a=splicing_symmetric_difference_a,
        symmetric_difference_b=splicing_symmetric_difference_b,
        debug=ctx.debug,
    )

    ########################
    # Splicing Similarity
    ########################

    # splicing_score_a = evaluate_score(splicing_intersection_a, ctx.hit_a.qseq, ctx.hit_a.hseq)
    # splicing_score_b = evaluate_score(splicing_intersection_b, ctx.hit_b.qseq, ctx.hit_b.hseq)
    query_splicing_length_a = aligned_splicing_a.length()
    hit_splicing_length_a = aligned_hit_splicing_a.length()
    max_splicing_length_a = max(query_splicing_length_a, hit_splicing_length_a)
    query_splicing_length_b = aligned_splicing_b.length()
    hit_splicing_length_b = aligned_hit_splicing_b.length()
    max_splicing_length_b = max(query_splicing_length_b, hit_splicing_length_b)
    max_splicing_length = max(max_splicing_length_a, max_splicing_length_b)
    normalized_max_splicing_length = _normalize_length(max_splicing_length)

    max_intersection_length = max(splicing_intersection_a_length, splicing_intersection_b_length)
    normalized_max_intersection_length = _normalize_length(max_intersection_length)
    splicing_score_a = count_matches(splicing_intersection_a, ctx.hit_a.midline)
    

    splicing_dissimilarity_a = (max_splicing_length_a - splicing_score_a) / normalized_max_splicing_length \
                                if normalized_max_splicing_length else 0
    splicing_score_b = count_matches(splicing_intersection_b, ctx.hit_b.midline)
    splicing_dissimilarity_b = (max_splicing_length_b - splicing_score_b) / normalized_max_splicing_length \
                               if normalized_max_splicing_length else 0
    splicing_intersection_length = splicing_intersection_a_length + splicing_intersection_b_length
    normalized_length = _splicing_intersection_length_weight(splicing_intersection_length) * splicing_intersection_length
        
    match.splicing_similarity = (splicing_score_a + splicing_score_b) / normalized_length \
         if normalized_length else 0
    match.splicing_dissimilarity = splicing_dissimilarity_a + splicing_dissimilarity_b
        

    if ctx.debug:
        print("<----------->")
        print("Splicing similarity")
        print("ctx.hit_a.qseq   :", ctx.hit_a.qseq)
        print("ctx.hit_a.midline:", ctx.hit_a.midline)
        print("ctx.hit_a.hseq   :", ctx.hit_a.hseq)
        print("ctx.hit_a.hit_from: ", ctx.hit_a.hit_from)
        
        print("splicing_score_a :", splicing_score_a)
        print("splicing_intersection_a_length", splicing_intersection_a_length)
        print("max_splicing_length_a", max_splicing_length_a)
        print("normalized_max_splicing_length", normalized_max_splicing_length)
        print("splicing_dissimilarity_a", splicing_dissimilarity_a)
        print("splicing_intersection_a", splicing_intersection_a)
        print()
        print("ctx.hit_b.qseq   :", ctx.hit_b.qseq)
        print("ctx.hit_b.midline:", ctx.hit_b.midline)
        print("ctx.hit_b.hseq   :", ctx.hit_b.hseq)
        print("ctx.hit_b.hit_from: ", ctx.hit_b.hit_from)
        
        print("splicing_score_b :", splicing_score_b)
        print("splicing_intersection_b_length", splicing_intersection_b_length)
        print("max_splicing_length_b", max_splicing_length_b)
        print("normalized_max_splicing_length", normalized_max_splicing_length)
        print("splicing_dissimilarity_b", splicing_dissimilarity_b)
        print("splicing_intersection_b", splicing_intersection_b)
        print()
        print("splicing_intersection_length", splicing_intersection_length)
        print("normalized_length", normalized_length)
        print("splicing_similarity", match.splicing_similarity)
        print("splicing_dissimilarity", match.splicing_dissimilarity)
        

    ########################
    # isoform blast score
    ########################
    # match.isoform_blast_score = (ctx.hit_a.score + ctx.hit_b.score) / (ctx.hit_a.query_len + ctx.hit_b.query_len + ctx.hit_a.iso_len + ctx.hit_b.iso_len)
    match_score_a = count_all_matches(ctx.hit_a.midline)
    match_score_b = count_all_matches(ctx.hit_b.midline)
    match.isoform_blast_score = (match_score_a + match_score_b) / (ctx.hit_a.query_len + ctx.hit_b.query_len + ctx.hit_a.iso_len + ctx.hit_b.iso_len)
    if ctx.debug:
        print("ctx.hit_a.score", ctx.hit_a.score)
        print("match_score_a", match_score_a)
        print("ctx.hit_a.query_len", ctx.hit_a.query_len)
        print("ctx.hit_a.iso_len", ctx.hit_a.iso_len)

        print("ctx.hit_b.score", ctx.hit_b.score)
        print("match_score_b", match_score_b)
        print("ctx.hit_b.query_len", ctx.hit_b.query_len)
        print("ctx.hit_b.iso_len", ctx.hit_b.iso_len)

        print("match.isoform_blast_score", match.isoform_blast_score)

    return match


def prepare_calc_queries(db: database.models.DB, launch_folder: str, query_ctx: Queries, query_tuples: List[IsoformTuple], ) -> CalcQueriesContext:
    isoforms = list(set(chain.from_iterable(
        (query_isoforms.a, query_isoforms.b)
        for query_isoforms in query_tuples
    )))
    iso_to_hits = {}
    for iso_uuid in isoforms:
        iso = db.isoforms[iso_uuid]
        gene = db.genes[iso.gene_uuid]
        record = db.records[gene.record_uuid]
        iso_to_hits[iso_uuid] = blast.get_results(
            db, 
            launch_folder,
            query_len=len(iso.translation),
            result_file=query_ctx.isoform_to_file[iso_uuid],
            query_organism=record.organism,
        )

    queries = []
    for query in query_tuples:
        iso_a = db.isoforms[query.a]
        iso_b = db.isoforms[query.b]
        gene = db.genes[iso_a.gene_uuid]
        record = db.records[gene.record_uuid]

        queries.append(CalcQuery(
            iso_a=iso_a.uuid,
            iso_a_location=iso_a.location,
            iso_a_len=len(iso_a.translation),
            iso_b=iso_b.uuid,
            iso_b_location=iso_b.location,
            iso_b_len=len(iso_b.translation),
            organism=record.organism,
        ))

    q_iso_to_gene = {iso_uuid:db.isoforms[iso_uuid].gene_uuid for iso_uuid in isoforms}

    return CalcQueriesContext(
        queries=queries,
        iso_to_hits=iso_to_hits,
        q_iso_to_gene=q_iso_to_gene,
    )


def calc_queries(ctx: CalcQueriesContext, use_tqdm: bool = True) -> List[Match]:
    if ctx.debug:
        with open(os.path.join(paths.FOLDER_DATA, "calc_queries_ctx.pkl"), "wb") as f:
            pickle.dump(ctx, f)
    hit_groups: Iterable[List[blast.Hit]] = tqdm(
        ctx.iso_to_hits.values(), desc="get_alignment_segments for hits") if use_tqdm else ctx.iso_to_hits.values()
    for hits in hit_groups:
        for hit in hits:
            hit.query_segments = get_alignment_segments(
                hit.qseq, hit.query_from, hit.query_len)
            hit.hit_segments = get_alignment_segments(
                hit.hseq, hit.hit_from, hit.iso_len)
    matches = []
    queries: List[CalcQuery] = tqdm(
        ctx.queries, desc="calc_queires") if use_tqdm else ctx.queries
    for query in queries:
        query_union = union(query.iso_a_location, query.iso_b_location)
        _extend_splicing(query_union)
        _add_event_ids(query_union)
        query_splicing_global_a, query_splicing_global_b = _get_splicings_from_union(query_union)

        hits_a = ctx.iso_to_hits[query.iso_a]
        hits_b = ctx.iso_to_hits[query.iso_b]

        splicing_a = convert_splicing(
            query_splicing_global_a, query.iso_a_location, query.iso_a_len)
        splicing_b = convert_splicing(
            query_splicing_global_b, query.iso_b_location, query.iso_b_len)

        if ctx.debug:
            print("<------------->")
            print("query.iso_a_location", query.iso_a_location)
            print("query.iso_b_location", query.iso_b_location)
            print("query_union", query_union)
            print("query_splicing_global_a", query_splicing_global_a)
            print("query_splicing_global_b", query_splicing_global_b)
            print("splicing_a", splicing_a)
            print("splicing_b", splicing_b)


        gene_to_hits_b: Dict[uuid.UUID, List[blast.Hit]] = defaultdict(list)
        for h in hits_b:
            gene_to_hits_b[h.iso_gene_uuid].append(h)

        for hit_a in hits_a:
            # if hit_a.organism == query.organism:
            #     continue
            hits_b_from_same_gene = gene_to_hits_b.get(hit_a.iso_gene_uuid, [])
            for hit_b in hits_b_from_same_gene:
                if ctx.hit_tuple and not (ctx.hit_tuple.a == hit_a.iso_uuid and ctx.hit_tuple.b == hit_b.iso_uuid):
                    continue
                if hit_b.iso_uuid == hit_a.iso_uuid:
                    continue
                m = calc_single(CalcMatchContext(
                    hit_a=hit_a,
                    hit_b=hit_b,
                    iso_a=query.iso_a,
                    iso_b=query.iso_b,
                    splicing_a=splicing_a,
                    splicing_b=splicing_b,
                    debug=ctx.debug,
                ))
                matches.append(m)

    return matches


def calc(
    db: database.models.DB,
    launch_folder: str,
    queries: Queries,
    query_tuples: Optional[List[IsoformTuple]] = None,
    hit_tuple: Optional[IsoformTuple] = None,
    debug: bool = False,
) -> List[Match]:
    if query_tuples is None:
        query_tuples = queries.tuples
    ctx = prepare_calc_queries(db, launch_folder, queries, query_tuples,)
    ctx.hit_tuple = hit_tuple
    ctx.debug = debug
    return calc_queries(ctx)

def _check_connections(two_level_dict: Dict[uuid.UUID, Dict[Any, uuid.UUID]], m: Match, iso_from: uuid.UUID, mid: Any, iso_to: uuid.UUID) -> None:
    sub_dict = two_level_dict[iso_from]
    saved_iso_to = sub_dict.get(mid)
    if saved_iso_to is None:
        sub_dict[mid] = iso_to
    elif saved_iso_to != iso_to:
        m.predicted_positive = False


def transform(ctx: CalcQueriesContext, matches: List[Match], detector: ml.Detector) -> List[Match]:
    detector.transform(matches)
    query_to_organism_to_match: Dict[IsoformTuple,
                                     Dict[Tuple[str, str], Match]] = defaultdict(dict)
    for m in matches:
        organism_to_match = query_to_organism_to_match[m.query_isoforms]
        key = m.hit_organism, m.hit_db_name
        simple_match = organism_to_match.get(key)
        if simple_match is None or simple_match.predicted_positive_probability < m.predicted_positive_probability:
            organism_to_match[key] = m

    matches = [
        m
        for organism_to_match in query_to_organism_to_match.values()
        for m in organism_to_match.values()    
    ]
    matches.sort(key=lambda m: m.predicted_positive_probability, reverse=True)
    q_iso_to_organism_h_iso: Dict[uuid.UUID, Dict[str, uuid.UUID]] = defaultdict(dict)
    h_iso_to_q_gene_to_q_iso: Dict[uuid.UUID, Dict[uuid.UUID, uuid.UUID]] = defaultdict(dict)
    for m in matches:
        _check_connections(q_iso_to_organism_h_iso, m, m.query_isoforms.a, m.hit_organism, m.hit_isoforms.a)
        _check_connections(q_iso_to_organism_h_iso, m, m.query_isoforms.b, m.hit_organism, m.hit_isoforms.b)
        _check_connections(h_iso_to_q_gene_to_q_iso, m, m.hit_isoforms.a, ctx.q_iso_to_gene[m.query_isoforms.a], m.query_isoforms.a)
        _check_connections(h_iso_to_q_gene_to_q_iso, m, m.hit_isoforms.b, ctx.q_iso_to_gene[m.query_isoforms.b], m.query_isoforms.b)
    
    return matches
   

def calc_single_batch_parallel(batch: CalcBatch, detector: ml.Detector) -> None:
    matches = calc_queries(batch.ctx, use_tqdm=False)
    matches = transform(batch.ctx, matches, detector)

    query_to_matches: Dict[IsoformTuple, List[SimpleMatch]] = defaultdict(list)
    for m in matches:
        query_to_matches[m.query_isoforms].append(SimpleMatch(
            hit_isoforms=m.hit_isoforms,
            predicted_positive=m.predicted_positive,
            predicted_positive_probability=m.predicted_positive_probability,
        ))
    with open(batch.result_path, "wb") as f:
        pickle.dump(dict(query_to_matches), f,
                    protocol=pickle.HIGHEST_PROTOCOL)


def build_calc_batch_generator(
    db: database.models.DB,
    launch_folder: str,
    queries: Queries,
    query_tuples: List[IsoformTuple],
    batch_size: int = 10,
) -> Iterable[CalcBatch]:
    batch_idx = itertools.count()
    results_folder = _parallel_results_folder(launch_folder)
    gene_to_tuples: Dict[uuid.UUID, List[IsoformTuple]] = defaultdict(list)
    for query_tuple in query_tuples:
        gene_to_tuples[db.isoforms[query_tuple.a].gene_uuid].append(query_tuple)
    tuple_groups = list(gene_to_tuples.values())

    for i in range(0, len(tuple_groups), batch_size):
        result_path = os.path.join(
            results_folder, f"batch_{next(batch_idx)}.pkl")
        if os.path.exists(result_path): continue
        batch_tuples = [
            query_tuple
            for tuple_group in tuple_groups[i:i + batch_size]
            for query_tuple in tuple_group
        ]
        ctx = prepare_calc_queries(db, launch_folder,  queries, batch_tuples)
        yield CalcBatch(
            result_path=result_path,
            ctx=ctx,
        )


def calc_batches(
        db: database.models.DB,
        launch_folder: str,
        queries: Queries,
        query_tuples: List[IsoformTuple],
        detector: ml.Detector,
        batch_size: int = 10
) -> None:
    _logger.info("Start calc batches")
    batches = build_calc_batch_generator(
        db, launch_folder, queries, query_tuples)
    for batch in tqdm(batches, total=len(query_tuples) / batch_size, desc="calc_batches"):
        calc_single_batch_parallel(batch, detector=detector)


def calc_parallel(
        db: database.models.DB,
        launch_folder: str,
        queries: Queries,
        query_tuples: List[IsoformTuple],
        detector: ml.Detector,
        batch_size: int = 10
) -> None:
    _logger.info("Start calc parallel")
    pathutil.reset_folder(_parallel_results_folder(launch_folder))
    generator = build_calc_batch_generator(
        db, launch_folder, queries, query_tuples)
    with get_context("spawn").Pool(19, maxtasksperchild=50) as p:
        list(tqdm(p.imap_unordered(
            partial(
                calc_single_batch_parallel,
                detector=detector,
            ),
            generator,
            chunksize=1,
        ), total=len(query_tuples) / batch_size))


###############
# Helpers
###############

def read_simple_matches(launch_folder: str) -> Mapping[IsoformTuple, List[SimpleMatch]]:
    results_folder = _parallel_results_folder(launch_folder)
    result: Dict[IsoformTuple, List[SimpleMatch]] = {}
    for file_path in tqdm(pathutil.file_list(results_folder), desc="read_simple_matches"):
        with open(file_path, "rb") as f:
            result.update(pickle.load(f))
    return result


def convert_matches(simple_matches: Dict[IsoformTuple, List[SimpleMatch]]) -> List[Match]:
    result = []
    for query_isoforms, matches in simple_matches.items():
        for m in matches:
            result.append(Match(
                query_isoforms=query_isoforms,
                hit_isoforms=m.hit_isoforms,
                predicted_positive=m.predicted_positive,
                predicted_positive_probability=m.predicted_positive_probability,
                hit_organism="",
            ))
    return result


if __name__ == "__main__":
    with open(os.path.join(paths.FOLDER_DATA, "calc_queries_ctx.pkl"), "rb") as f:
        ctx = pickle.load(f)
    ctx.debug = True
    calc_queries(ctx, use_tqdm=False)