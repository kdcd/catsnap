import gzip
import multiprocessing
import os
import pickle
import sys
import uuid
from collections import Counter, defaultdict
from copy import copy, deepcopy
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple
from dataclasses import dataclass, field
from kd_splicing.database import feature_tables

import pandas as pd
from memory_profiler import profile
from tqdm import tqdm

from kd_common import funcutil, logutil, pathutil
from kd_splicing import ct
from kd_splicing.database.models import DB, DBPart, Gene, Isoform, Location, RNA
from kd_splicing.location.models import LocationEvent, LocationPart
from kd_splicing.location.utils import bounding_box, intersection, is_equal, symmetric_difference

_logger = logutil.get_logger(__name__)


def _read_db_part(file_path: str) -> DBPart:
    try:
        with gzip.GzipFile(file_path, "r") as f:
            return pickle.load(f)  # type: ignore
    except Exception as e:
        os.remove(str(file_path))
        _logger.info(f"Read exception {file_path}")

def _convert_location(loc: Location) -> Tuple[Tuple[int, int, Optional[int]], ...]:
    return tuple(
        (p.start, p.end, p.strand)
        for p in loc.parts
    )

def add_part(db: DB, part: DBPart) -> None:
    db.files.update(part.files)
    db.records.update(part.records)
    db.genes.update(part.genes)
    db.isoforms.update(part.isoforms)
    db.rnas.update(part.rnas)

def merge_files(db_parts_files: List[str]) -> DB:
    db = DB()
    for src_file in db_parts_files:
        db_part = _read_db_part(src_file)
        if len(db_part.isoforms) == 0: continue
        add_part(db, db_part)
        del db_part
    return db

def merge(db_parts_folders: List[str]) -> DB:
    src_files = [
        f
        for folder in db_parts_folders
        for f in pathutil.file_list(folder)
    ]
    return merge_files(src_files)

def get_key_to_file(files: List[str]) -> Mapping[str, str]:
    r = {}
    for f in files:
        key = f.split("/")[-1].split(".")[0].split("_")[1]
        r[key] = f
    return r
    
def make_pairs(refseq_files: List[str], genbank_files: List[str]) -> List[Tuple[str, List[str]]]:
    key_to_tuple = defaultdict(dict)
    for f in refseq_files:
        key = f.split("/")[-1].split(".")[0].split("_")[1]
        key_to_tuple[key][0] = f
    for f in genbank_files:
        key = f.split("/")[-1].split(".")[0].split("_")[1]
        key_to_tuple[key][1] = f
    return [(k, v.get(0), v.get(1)) for k, v in key_to_tuple.items()]


def add_isoform_rna_links(db: DB, refseq_protein_id_to_transcript_id: Mapping[str, str], genbank_protein_id_to_rna_uuid: Mapping[str, uuid.UUID]) -> None:
    transcript_id_to_rna = {rna.transcript_id: rna for rna in db.rnas.values()}
    no_protein_id = 0
    no_transcript_id = 0
    no_rna_uuid = 0
    no_transcript_id_from_genbank = 0
    no_rna_with_such_transcript_id_refseq = 0
    no_rna_with_such_transcript_id_genbank = 0
    different_rna_gene = 0
    added_rna_to_isoform_links = 0
    for iso in db.isoforms.values():
        gene = db.genes[iso.gene_uuid]
        record = db.records[gene.record_uuid]
        db_file = db.files[record.file_uuid]

        if not iso.protein_id:
            no_protein_id += 1
            continue

        if db_file.db_name == "refseq":
            transcript_id = refseq_protein_id_to_transcript_id.get(iso.protein_id)
            if not transcript_id:
                no_transcript_id += 1
                continue

            rna = transcript_id_to_rna.get(transcript_id)
            if not rna:
                no_rna_with_such_transcript_id_refseq += 1
                continue

            added_rna_to_isoform_links += 1
            iso.rna_uuid = rna.uuid
        elif db_file.db_name == "genbank":
            rna_uuid = genbank_protein_id_to_rna_uuid.get(iso.protein_id)
            if not rna_uuid:
                no_rna_uuid += 1
                continue

            rna = db.rnas[rna_uuid]
            if iso.gene_uuid != rna.gene_uuid:
                # print(iso.protein_id, db.genes[iso.gene_uuid], db.genes[rna.gene_uuid])
                different_rna_gene += 1
                continue

            iso.rna_uuid = rna.uuid
            added_rna_to_isoform_links += 1

    _logger.info(f"no_protein_id: {no_protein_id}")
    _logger.info(f"no_transcript_id: {no_transcript_id}")
    _logger.info(f"no_rna_uuid: {no_rna_uuid}")
    _logger.info(f"no_transcript_id_from_genbank: {no_transcript_id_from_genbank}")
    _logger.info(f"no_rna_with_such_transcript_id_refseq: {no_rna_with_such_transcript_id_refseq}")
    _logger.info(f"no_rna_with_such_transcript_id_genbank: {no_rna_with_such_transcript_id_genbank}")
    _logger.info(f"different_rna_gene: {different_rna_gene}")
    _logger.info(f"added_rna_to_isoform_links: {added_rna_to_isoform_links}")


def merge_separatly(refseq_folder: str, genbank_folder: str, ) -> DB:
    genbank_files = pathutil.get_sub_files(os.path.join(genbank_folder, "extracted"))
    refseq_files = pathutil.get_sub_files(os.path.join(refseq_folder, "extracted"))
    key_to_genbank_report = get_key_to_file(pathutil.get_sub_files(os.path.join(genbank_folder, "reports")))
    key_to_refseq_features = get_key_to_file(pathutil.get_sub_files(os.path.join(refseq_folder, "feature_tables")))
    key_to_genbank_features = get_key_to_file(pathutil.get_sub_files(os.path.join(genbank_folder, "feature_tables")))
    absent_genbank_features = 0
    absent_refseq_features = 0
    db = DB()
    for key, refseq_file, genbank_file in tqdm(make_pairs(refseq_files, genbank_files)):
        # if key != "001742945": continue
        
        part = merge_files(f for f in [refseq_file, genbank_file] if f is not None)
        if len(part.isoforms) == 0: continue

        # _logger.info(f"key {key} {list(part.records.values())[0].organism}")

        refseq_protein_id_to_transcript_id = {}
        if refseq_file:
            if key in key_to_refseq_features:
                refseq_protein_id_to_transcript_id = feature_tables.read_refseq_protein_id_to_transcript_id(key_to_refseq_features[key])
                pass
            else:
                absent_refseq_features += 1

        genbank_protein_id_to_rna_uuid = {}
        if genbank_file:
            if key in key_to_genbank_features:
                genbank_protein_id_to_rna_uuid = feature_tables.read_genbank_protein_id_to_rna_uuid(part, key_to_genbank_features[key])
                pass
            else:
                absent_genbank_features += 1
        # print(genbank_protein_id_to_rna_uuid, refseq_file, genbank_file)
        add_isoform_rna_links(part, refseq_protein_id_to_transcript_id, genbank_protein_id_to_rna_uuid)

        if refseq_file is not None and genbank_file is not None:
            genbank_to_refseq = get_genbank_to_refseq_files([key_to_genbank_report[key]])
            merge_genes(part, genbank_to_refseq)
            
        leave_only_with_splicing(part)
        add_part(db, part)

        del part
    print("absent_refseq_features", absent_refseq_features, "absent_genbank_features", absent_genbank_features)
    return db



def get_genbank_to_refseq(reports_folder: str) -> Mapping[str, str]:
    report_files = pathutil.file_list(reports_folder)
    return get_genbank_to_refseq_files(report_files)

def get_genbank_to_refseq_files(reports_files: List[str]) -> Mapping[str, str]:
    sequence_id_from = []
    sequence_id_to = []
    for file_path in reports_files:
        df = pd.read_csv(file_path, sep="\t", comment="#",
                         header=None, na_values="na")
        df = df.iloc[:, [4, 6]]
        df = df.dropna()
        sequence_id_from.extend(list(df.iloc[:, 0]))
        sequence_id_to.extend(list(df.iloc[:, 1]))
    df = pd.DataFrame({"from": sequence_id_from, "to": sequence_id_to})
    duplicated_from = df[df["from"].duplicated()]
    duplicated_to = df[df["to"].duplicated()]
    if len(duplicated_from):
        _logger.warn(f"duplicated from sequence ids:\n{duplicated_from}")

    if len(duplicated_to):
        _logger.warn(f"Duplicated to sequence ids:\n{duplicated_to}")

    genbank_to_refseq = dict(zip(df["from"], df["to"]))
    return genbank_to_refseq


def _extract_locations(genes: List[Gene], name: str) -> List[Location]:
    locs = []
    for g in genes:
        loc = Location()
        for p in g.location.parts:
            loc.parts.append(LocationPart(
                start=p.start,
                end=p.end,
                strand=p.strand,
                data={name: {g.uuid}},
            ))
        locs.append(loc)
    return locs

def _split_locations_by_strand(locs: List[Location]) -> Tuple[List[Location], List[Location]]:
    straight = []
    inverse = []
    for loc in locs:
        if not loc.parts:
            continue
        if loc.parts[0].strand == 1:
            straight.append(loc)
        else:
            inverse.append(loc)

    return straight, inverse


def _intersect(first_locs: List[Location], second_locs: List[Location]) -> List[LocationPart]:
    first_parts = [p for l in first_locs for p in l.parts]
    second_parts = [p for l in second_locs for p in l.parts]
    parts = first_parts + second_parts
    events = []
    for part in parts:
        events.append(LocationEvent(
            pos=part.start,
            start=True,
            data=part.data,
        ))
        events.append(LocationEvent(
            pos=part.end,
            start=False,
            data=part.data,
        ))
    events.sort()

    pos = 0
    data: Dict[str, Set[str]] = defaultdict(set)
    result = []
    for e in events:
        if len(data) >= 2 and e.pos > pos:
            result.append(LocationPart(
                start=pos,
                end=e.pos,
                strand=None,
                data=deepcopy(data),
            ))

        if e.start:
            for key, value in e.data.items():
                data[key] |= value
        else:
            for key, value in e.data.items():
                data[key] -= value
                if not data[key]:
                    del data[key]
        if data:
            pos = e.pos

    return result

def merge_genes(db: DB, genbank_to_refseq: Mapping[str, str]) -> None:
    no_appropriate_refseq = 0
    multiple_record_ids_for_single_sequence_id = 0
    absent_refseq_record = 0
    refseq_sequence_id_to_record_id: Dict[str, uuid.UUID] = {}
    for record in db.records.values():
        db_file = db.files[record.file_uuid]
        if db_file.db_name != "refseq":
            continue
        record_id = refseq_sequence_id_to_record_id.get(record.sequence_id)
        if record_id is None:
            refseq_sequence_id_to_record_id[record.sequence_id] = record.uuid
        elif record_id != record.uuid:
            multiple_record_ids_for_single_sequence_id += 1

    record_id_to_genes: Dict[uuid.UUID, List[Gene]] = defaultdict(list)
    for gene in db.genes.values():
        record_id_to_genes[gene.record_uuid].append(gene)

    gene_to_isoforms: Dict[uuid.UUID, List[Isoform]] = defaultdict(list)
    for isoform in db.isoforms.values():
        gene_to_isoforms[isoform.gene_uuid].append(isoform)

    genes_with_small_intersection = 0
    matched_genes = 0
    matched_pairs = []
    ratios = []
    for genbank_record in db.records.values():
        db_file = db.files[genbank_record.file_uuid]
        if db_file.db_name != "genbank":
            continue

        refseq_sequence_id = genbank_to_refseq.get(genbank_record.sequence_id)
        if refseq_sequence_id is None:
            no_appropriate_refseq += 1
            continue

        refseq_record_id = refseq_sequence_id_to_record_id.get(
            refseq_sequence_id)
        if refseq_record_id is None:
            absent_refseq_record += 1
            continue

        refseq_record = db.records[refseq_record_id]
        genbank_locs = _extract_locations(
                record_id_to_genes[genbank_record.uuid], "genbank_uuid")
        refseq_locs = _extract_locations(
                record_id_to_genes[refseq_record.uuid], "refseq_uuid")
        genbank_straight, genbank_inverse = _split_locations_by_strand(genbank_locs)
        refseq_straight, refseq_inverse = _split_locations_by_strand(refseq_locs)

        intersected = _intersect(genbank_straight, refseq_straight) + _intersect(genbank_inverse, refseq_inverse)
        gene_pair_to_intersected: Dict[Tuple[uuid.UUID, uuid.UUID], int] = defaultdict(int)
        for p in intersected:
            for refseq_uuid in p.data.get("refseq_uuid", {}):
                for genbank_uuid in p.data.get("genbank_uuid", {}):
                    gene_pair_to_intersected[(genbank_uuid, refseq_uuid)] += p.length()
        
        for gene_pair, intersection_length in gene_pair_to_intersected.items():
            genbank_gene_uuid, refseq_gene_uuid = gene_pair
            genbank_gene = db.genes[genbank_gene_uuid]
            refseq_gene = db.genes[refseq_gene_uuid]
            intersection_ratio = float(2 * intersection_length) / (genbank_gene.location.length() + refseq_gene.location.length())
            ratios.append(intersection_ratio)
            if intersection_ratio < 0.8:
                genes_with_small_intersection += 1
                continue
            matched_pairs.append((genbank_gene.locus_tag, genbank_gene.gene_id, refseq_gene.locus_tag, refseq_gene.gene_id))
            
            matched_genes += 1
            for genbank_iso in gene_to_isoforms[genbank_gene_uuid]:
                genbank_iso.src_gene_uuid = genbank_iso.gene_uuid
                genbank_iso.gene_uuid = refseq_gene.uuid
        
    _logger.info(f"""Merge genes stats:
    no_appropriate_refseq: {no_appropriate_refseq}
    multiple_record_ids_for_single_sequence_id: {multiple_record_ids_for_single_sequence_id}
    absent_refseq_record: {absent_refseq_record}
    genes_with_small_intersection: {genes_with_small_intersection}
    matched_genes:{matched_genes}""")
            
def read(store_path: str) -> DB:
    with open(store_path, "rb") as f:
        db = pickle.load(f)
        db.protein_id_to_isoform = {i.protein_id: i.uuid for i in db.isoforms.values()}
        db.isoform_to_duplicates = get_isoform_to_duplicates(db)
        return db

def leave_only_with_splicing(db: DB) -> None:
    genes_to_isoforms_count: Dict[uuid.UUID, int]= defaultdict(int)
    for iso in db.isoforms.values():
        genes_to_isoforms_count[iso.gene_uuid] += 1

    genes_to_hold: Set[uuid.UUID]= set()
    for iso in db.isoforms.values():
        if genes_to_isoforms_count[iso.gene_uuid] > 1:
            genes_to_hold.add(iso.gene_uuid)
            genes_to_hold.add(iso.src_gene_uuid)

    isoforms: Dict[uuid.UUID, Isoform] = {}
    rna_to_hold = set()
    for iso in db.isoforms.values():
        if iso.gene_uuid in genes_to_hold:
            isoforms[iso.uuid] = iso
            rna_to_hold.add(iso.rna_uuid)
    db.isoforms = isoforms

    # TODO Check iso rna uuid 
    rnas: Dict[uuid.UUID, RNA] = {}
    for rna in db.rnas.values():
        if rna.gene_uuid in genes_to_hold or rna.uuid in rna_to_hold:
            rnas[rna.uuid] = rna
    db.rnas = rnas

    genes: Dict[uuid.UUID, Gene] = {}
    for g in db.genes.values():
        if g.uuid in genes_to_hold:
            genes[g.uuid] = g
    db.genes = genes

def write(db: DB, merged_store_path: str) -> None:
    with open(merged_store_path, "wb") as f:
        pickler = pickle.Pickler(f, protocol=pickle.HIGHEST_PROTOCOL)
        pickler.fast = True
        pickler.dump(db)


def get_isoform_to_duplicates(db: DB) -> Mapping[uuid.UUID, List[uuid.UUID]]:
    gene_to_isoforms: Dict[uuid.UUID, List[Isoform]] = defaultdict(list)
    for iso in tqdm(db.isoforms.values()):
        gene_to_isoforms[iso.gene_uuid].append(iso)
    
    result: Mapping[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    for isoforms in tqdm(gene_to_isoforms.values()):
        for i in range(len(isoforms)):
            for j in range(len(isoforms)):
                if i == j:
                    result[isoforms[i].uuid].append(isoforms[j].uuid)
                elif is_equal(isoforms[i].location, isoforms[j].location):
                    result[isoforms[i].uuid].append(isoforms[j].uuid)
    return result     

