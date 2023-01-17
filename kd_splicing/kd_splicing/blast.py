import json
import multiprocessing
import subprocess
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from functools import partial
from os.path import dirname, join
from typing import Dict, List, Mapping, Set, Optional

import pandas as pd
from tqdm import tqdm

from kd_common import excel, logutil, pathutil
from kd_splicing import database, sequences
from kd_splicing.location.models import ConvertSegment
from kd_splicing.location.utils import get_alignment_segments, symmetric_difference
from kd_splicing.models import Queries


_logger = logutil.get_logger(__name__)

def _deduplicate_isoforms(src_isoforms: List[database.models.Isoform]) -> List[database.models.Isoform]:
    gene_to_isoforms: Dict[uuid.UUID, List[database.models.Isoform]] = defaultdict(list)
    for iso in src_isoforms:
        gene_to_isoforms[iso.gene_uuid].append(iso)
    
    result: List[database.models.Isoform] = []
    for isoforms in tqdm(gene_to_isoforms.values()):
        if len(isoforms) <= 1:
            continue
        isoforms = sorted(isoforms, key= lambda i: 0 if i.src_gene_uuid is None else 1)
        duplicated: Set[uuid.UUID] = set()
        for i in range(len(isoforms)):
            if isoforms[i].uuid in duplicated:
                continue
            for j in range(i + 1, len(isoforms)):
                if isoforms[j].uuid in duplicated:
                    continue
                splicing = symmetric_difference(isoforms[i].location, isoforms[j].location)
                if splicing.length() == 0:
                    duplicated.add(isoforms[j].uuid)
            result.append(isoforms[i])
    return result

def _biggest_isoform_per_gene(src_isoforms: List[database.models.Isoform]) -> List[database.models.Isoform]:
    gene_to_isoform: Dict[uuid.UUID, database.models.Isoform] = {}
    for iso in src_isoforms:
        best_isoform = gene_to_isoform.get(iso.gene_uuid)
        if best_isoform is None or len(iso.translation) > len(best_isoform.translation):
            gene_to_isoform[iso.gene_uuid] = iso
    return list(gene_to_isoform.values())



def create_db(db: database.models.DB, db_path: str, deduplicate_isoforms: bool = True) -> None:
    _logger.info("Start create BLAST DB")
    uniq_isoforms = list(db.isoforms.values())
    uniq_isoforms = [
        i
        for i in uniq_isoforms
    ]
    if deduplicate_isoforms:
        uniq_isoforms = _deduplicate_isoforms(uniq_isoforms)
    _logger.info(f"Uniq isoforms: {len(uniq_isoforms)} {len(uniq_isoforms) / len(db.isoforms)} {len(db.isoforms)}")
    
    pathutil.reset_folder(dirname(db_path))

    with open(db_path, "w") as f:
        for isoform in uniq_isoforms:
            f.write(">" + str(isoform.uuid) + "\n")
            f.write(isoform.translation + "\n")

    _logger.info("Start Makeblastdb")
    _logger.info(subprocess.call(
        ["makeblastdb", "-in", db_path, "-dbtype", "prot"]
    ))


def create_db_from_file_db(db: database.filedb.FileDB, db_path: str, filter: Optional[Set[uuid.UUID]] = None) -> None:
    _logger.info("Start creating BLAST DB")
    pathutil.reset_folder(dirname(db_path))

    
    with open(db_path, "w") as f:
        for isoform in tqdm(db.isoforms.values()):
            if filter is None or isoform.uuid in filter:
                f.write(">" + str(isoform.uuid) + "\n")
                f.write(isoform.translation + "\n")

    _logger.info("Start Makeblastdb")
    _logger.info(subprocess.call(
        ["makeblastdb", "-in", db_path, "-dbtype", "prot"]
    ))



def _queries_folder(launch_folder: str) -> str:
    return pathutil.create_folder(launch_folder, "blast_queries")


def _results_folder(launch_folder: str) -> str:
    return pathutil.create_folder(launch_folder, "blast_results")


def _query_path(launch_folder: str, group: int) -> str:
    return join(_queries_folder(launch_folder), f"{group}.fasta")


def _results_path(launch_folder: str, group: int) -> str:
    return join(pathutil.create_folder(
        _results_folder(launch_folder),
        f"group_{group}"
    ), "result")


def run_single(group: int, launch_folder: str, db_path: str, max_target_seqs: int) -> None:
    blast_args = [
        "blastp", "-query", _query_path(launch_folder, group), "-db", db_path,
        "-out", _results_path(launch_folder, group),  "-outfmt", "13", "-num_threads", "19",
        "-max_target_seqs", str(max_target_seqs), "-evalue", "0.000000001"
    ]
    _logger.info("Start blast")
    _logger.info(subprocess.call(blast_args))
    _logger.info("Finish blast")

def create_queires(db: database.models.DB, queries: Queries, launch_folder: str) -> None:
    group_to_isoforms: Dict[int, List[uuid.UUID]] = defaultdict(list)
    for iso in queries.isoforms:
        group_to_isoforms[queries.isoform_to_group[iso]].append(iso)
    pathutil.reset_folder(_queries_folder(launch_folder))
    pathutil.reset_folder(_results_folder(launch_folder))
    for group, isoforms in group_to_isoforms.items():
        with open(_query_path(launch_folder, group), "w") as f:
            for isoform_uuid in isoforms:
                isoform = db.isoforms[isoform_uuid]
                f.write(f">{isoform.uuid}\n")
                f.write(isoform.translation + "\n")

def run(launch_folder: str,  blast_db_path: str, max_target_seqs: int=2000, num_groups: int = 20, parallel: bool = True) -> None:
    if parallel:
        with multiprocessing.Pool(num_groups) as p:
            list(tqdm(p.imap(
                partial(
                    run_single,
                    launch_folder=launch_folder,
                    db_path=blast_db_path,
                    max_target_seqs=max_target_seqs,
                ),
                list(range(num_groups))
            )))
    else:
        for group in list(range(1)):
            run_single(
                group=group,
                launch_folder=launch_folder,
                db_path=blast_db_path,
                max_target_seqs=max_target_seqs
            )


@dataclass
class Hit:
    iso_uuid: uuid.UUID
    iso_len: int
    iso_gene_uuid: uuid.UUID
    iso_location: database.models.Location
    organism: str
    db_name: str
    score: int
    query_from: int
    query_to: int
    query_len: int
    hit_from: int
    hit_to: int
    qseq: str
    hseq: str
    midline: str
    query_segments: List[ConvertSegment] = field(default_factory=list)
    hit_segments: List[ConvertSegment] = field(default_factory=list)


@dataclass
class Results:
    hits: Mapping[uuid.UUID, List[Hit]]


def get_results(db: database.models.DB, launch_folder: str, query_len: int, result_file: str, query_organism: str) -> List[Hit]:
    hits = []
    with open(result_file, "r") as f:
        data = json.load(f)
        search = data["BlastOutput2"]["report"]["results"]["search"]
        blast_hits = search["hits"]
        for hit in blast_hits:
            hsps = hit["hsps"][0]
            qseq = hsps["qseq"]
            hseq = hsps["hseq"]
            iso_uuid = uuid.UUID(hit["description"][0]["title"])
            iso = db.isoforms.get(iso_uuid)
            if not iso:
                _logger.warn(f"Iso not found in db {iso_uuid}")
                continue
            gene = db.genes[iso.gene_uuid]
            record = db.records[gene.record_uuid]
            # if record.organism == query_organism: continue
            db_file = db.files[record.file_uuid]
            hit_from = hsps["hit_from"] - 1
            query_from = hsps["query_from"] - 1
            hits.append(Hit(
                iso_uuid=iso.uuid,
                iso_len=len(iso.translation),
                iso_gene_uuid=iso.gene_uuid,
                iso_location=iso.location,
                organism=record.organism,
                db_name=db_file.db_name,
                score=hsps["bit_score"],
                query_from=hsps["query_from"] - 1,
                query_to=hsps["query_to"],
                query_len=query_len,
                hit_from=hsps["hit_from"] - 1,
                hit_to=hsps["hit_to"],
                qseq=qseq,
                hseq=hseq,
                midline=hsps["midline"],
            ))
    return hits
