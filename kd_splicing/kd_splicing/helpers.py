import os
import uuid
from collections import defaultdict
from itertools import chain
from typing import Dict, List, Mapping, Optional, Tuple


import pandas as pd

from kd_common import excel, logutil, pathutil
from kd_splicing import as_type, blast, database, features, ml, performance, pipeline
from kd_splicing.dataset.models import Dataset
from kd_splicing.dump import dump
from kd_splicing.models import FormattedResults, IsoformTuple, Match, SimpleMatch, Queries
from kd_splicing.models import SearchStatus
from kd_splicing.exception import CustomException
import itertools
from tqdm import tqdm
import json
import uuid
from typing import Optional
from dataclasses import dataclass, field
import re
from kd_splicing.location.models import Location, LocationPart
from kd_splicing.models import FormattedResultsQuery
from kd_splicing import muscle, kalign
from kd_splicing.database import models
from Bio.Seq import Seq
from kd_splicing import paths

_logger = logutil.get_logger(__name__)


def find_in_queries(
    protein_ids_str: str,
    isoforms_to_duplicates: Mapping[uuid.UUID, List[uuid.UUID]],
    db: database.models.DB,
    matches_dict: Mapping[IsoformTuple, List[SimpleMatch]]
) -> Optional[IsoformTuple]:
    tup = str_to_isoform_tuple(db, protein_ids_str)
    for a in isoforms_to_duplicates[tup.a]:
        for b in isoforms_to_duplicates[tup.b]:
            dup = IsoformTuple(a,b)
            if dup in matches_dict:
                return dup
    return None

#############
# Common
#############
@dataclass 
class FakeGene:
    seq: str
    aligned: Optional[str] = None
    guid: uuid.UUID = field(default_factory=uuid.uuid4)
    location: Optional[Location] = None
@dataclass 
class FakeIso:
    seq: str
    aligned: Optional[str] = None
    guid: uuid.UUID = field(default_factory=uuid.uuid4)
    location: Optional[Location] = None

def get_location_from_alignment(seq: str):
        start = None
        loc = Location()
        for i in range(len(seq)):
            if start is None:
                if seq[i] != "-":
                    start = i
            else:
                if seq[i] == "-":
                    loc.parts.append(LocationPart(start, i, 1))
                    start = None
        return loc
def normalize_seq(s: str):
    return re.sub(r'[^ATGC]', '', s.upper())
def str_to_isoform_tuple(db: database.models.DB, protein_ids_str: str) -> IsoformTuple:
    protein_ids = [protein_id.strip()
                   for protein_id in protein_ids_str.split(",")]
    assert len(protein_ids) == 2
    return IsoformTuple(
        db.protein_id_to_isoform[protein_ids[0]], db.protein_id_to_isoform[protein_ids[1]])
def isoform_tuple_to_protein_ids(db: database.models.DB, iso_tuple: IsoformTuple) -> str:
    return f"{db.isoforms[iso_tuple.a].protein_id},{db.isoforms[iso_tuple.b].protein_id}"
def tuples_to_queries(tuples: List[IsoformTuple], num_groups: int = 20) -> Queries:
    isoforms = sorted(list(set(chain.from_iterable(
        (query_isoforms.a, query_isoforms.b)
        for query_isoforms in tuples
    ))))
    group_count = itertools.cycle(range(0, num_groups))
    isoform_to_group = {}
    isoform_to_idx = {}
    group_size: Dict[int, int] = defaultdict(int)
    for iso in isoforms:
        group = next(group_count)
        isoform_to_group[iso] = group
        isoform_to_idx[iso] = group_size[group]
        group_size[group] += 1
    return Queries(
        tuples=tuples,
        isoforms=isoforms,
        isoform_to_idx=isoform_to_idx,
        isoform_to_group=isoform_to_group,
    )
def best_match_per_organism(matches: List[Match]) -> List[Match]:
    query_organism_to_match: Dict[Tuple[IsoformTuple, str], Match] = {}
    for m in matches:
        key = (m.query_isoforms, m.hit_organism)
        best_match = query_organism_to_match.get(key)
        if not best_match  or best_match.predicted_positive_probability < m.predicted_positive_probability:
            query_organism_to_match[key] = m
    return list(query_organism_to_match.values())

#############
# Stats
#############

def count_isoforms_per_organism(db: database.models.DB) -> None:
    organism_to_isoform_count: Dict[str, int] = defaultdict(int)
    for isoform in db.isoforms.values():
        gene = db.genes[isoform.gene_uuid]
        record = db.records[gene.record_uuid]
        organism_to_isoform_count[record.organism] += 1
    for key, value in sorted(organism_to_isoform_count.items(), key=lambda p: p[1]):
        print(key, ",", value)
def calc_performance(matches: List[Match]) -> None:
    predicted = [m.predicted_positive for m in matches]
    correct = [m.positive for m in matches]
    _logger.info(
        f"Performance:\n{pd.Series(performance.binary_y_performance(correct, predicted))}")
def db_organisms_stats(db: database.models.DB, db_folder: str) -> None:
    df = database.utils.to_df(db)

    d1 = df["organism"].value_counts().reset_index()
    excel.write(d1, os.path.join(pathutil.create_folder(
        db_folder, "stats"), os.path.basename(db_folder) + "_db_organisms.xlsx"))

    d2 = df[df["db_name"] == "refseq"]["organism"].value_counts().reset_index()
    excel.write(d2, os.path.join(pathutil.create_folder(
        db_folder, "stats"), os.path.basename(db_folder) + "_db_organisms_refseq.xlsx"))

    d3 = df[df["db_name"] == "genbank"]["organism"].value_counts().reset_index()
    excel.write(d3, os.path.join(pathutil.create_folder(
        db_folder, "stats"), os.path.basename(db_folder) + "_db_organisms_genbank.xlsx"))
    
    d4 = df[df["db_name_src"] == "refseq"]["organism"].value_counts().reset_index()
    excel.write(d4, os.path.join(pathutil.create_folder(
        db_folder, "stats"), os.path.basename(db_folder) + "_db_organisms_refseq_src.xlsx"))

    d5 = df[df["db_name_src"] == "genbank"]["organism"].value_counts().reset_index()
    excel.write(d5, os.path.join(pathutil.create_folder(
        db_folder, "stats"), os.path.basename(db_folder) + "_db_organisms_genbank_src.xlsx"))
def db_missed_files(p: pipeline.Pipeline) -> None:
    def prepare(s: str) -> str:
        s = os.path.basename(s)
        s = ".".join(s.split(".")[:-1])
        return s

    files = pathutil.file_list(p.folder_archive, p.archive_extension)
    extracted = pathutil.file_list(p.folder_extracted)
    files.sort()
    extracted = [prepare(f) for f in extracted]
    files = [prepare(f) for f in files]
    print(sorted(list(set(files) - set(extracted))))

#############
# Dumps
#############


def single_cross_validation_and_dump(db: database.models.DB, launch_folder: str, ds: List[Match], test_protein_ids: str) -> None:
    protein_ids = test_protein_ids.split(",")
    assert len(protein_ids) == 2
    protein_id_to_isoform = {
        i.protein_id: i.uuid for i in db.isoforms.values()}
    test_query_isoforms = IsoformTuple(
        protein_id_to_isoform[protein_ids[0]], protein_id_to_isoform[protein_ids[1]])
    train_ds = [m for m in ds if m.query_isoforms != test_query_isoforms]
    test_ds = [m for m in ds if m.query_isoforms == test_query_isoforms]
    d = ml.Detector()
    d.fit(train_ds)
    d.transform(test_ds)
    calc_performance(test_ds)
    folder = pathutil.create_folder(launch_folder, "cross_validation")
    dump(db, folder, test_ds)
def dump_single_query_simple_matches(
        db: database.models.DB,
        launch_folder: str,
        matches_dict: Mapping[IsoformTuple, List[SimpleMatch]],
        protein_ids_str: str,
        isoforms_to_duplicates: Mapping[uuid.UUID, List[uuid.UUID]],
) -> None:
    query_isoforms  = find_in_queries(protein_ids_str, isoforms_to_duplicates, db, matches_dict)
    if not query_isoforms:
        print("No such query in precalculated queries")
        return

    simple_matches = matches_dict[query_isoforms]
    matches = features.convert_matches({query_isoforms: simple_matches})
    dump(db, pathutil.create_folder(launch_folder,
                                    "matches_simple_single", protein_ids_str), matches)
def calc_features_and_dump_single(
        db: database.models.DB,
        launch_folder: str,
        queries: Queries,
        detector: ml.Detector,
        protein_ids_str: str,
        isoforms_to_duplicates: Mapping[uuid.UUID, List[uuid.UUID]],
        matches_dict: Mapping[IsoformTuple, List[SimpleMatch]],
) -> List[Match]:
    query_isoforms  = find_in_queries(protein_ids_str, isoforms_to_duplicates, db, matches_dict)
    if not query_isoforms:
        print("No such query in precalculated queries")
        return

    matches = features.calc(db, launch_folder, queries, [query_isoforms])
    detector.transform(matches)
    dump(db, pathutil.create_folder(launch_folder,
                                    "matches_single", protein_ids_str), matches)
    return matches


#############
# Search
#############

def _align_multi(gene: FakeGene, iso1: FakeIso, iso2: FakeIso):
    file_for_alignment = os.path.join(paths.FOLDER_DATA, "test.fa")
    items = [gene, iso1, iso2]
    id_to_item = {str(item.guid): item for item in items}
    with open(file_for_alignment, "w") as f:
        for item in [gene, iso1, iso2]:
            f.write(">" + str(item.guid) + "\n")
            f.write(item.seq + "\n")
    alignment_file = muscle.run_single(file_for_alignment)
    result = FormattedResultsQuery.from_file(alignment_file)
    for item in result.items:
        id_to_item[item.name].aligned = item.sequence
        
    for iso in items:
        iso.location = get_location_from_alignment(iso.aligned) 
def _align_pair(gene: FakeGene, iso: FakeIso):
    file_for_alignment = os.path.join(paths.FOLDER_DATA, "test.fa")
    items = [gene, iso]
    id_to_item = {str(item.guid): item for item in items}
    with open(file_for_alignment, "w") as f:
        for item in [gene, iso]:
            f.write(">" + str(item.guid) + "\n")
            f.write(item.seq + "\n")
    alignment_file = muscle.run_single(file_for_alignment)
    result = FormattedResultsQuery.from_file(alignment_file)
    for item in result.items:
        id_to_item[item.name].aligned = item.sequence
        
    for i in items:
        i.location = get_location_from_alignment(i.aligned) 

def search_custom(
    file_db: database.models.DB,
    p: pipeline.Pipeline,
    detector: ml.Detector,
    gene_seq: str, 
    iso1_seq: str, 
    iso2_seq: str,
    blast_db_path: str,
    status: SearchStatus = SearchStatus.construct(progress = 0, description = ""),
    isoforms_to_duplicates: Optional[Mapping[uuid.UUID, List[uuid.UUID]]] = None,
):
    print("blastdb", blast_db_path)
    gene = FakeGene(seq = normalize_seq(gene_seq))
    iso1 = FakeIso(seq = normalize_seq(iso1_seq))
    iso2 = FakeIso(seq = normalize_seq(iso2_seq))

    # _align_multi(gene, iso1, iso2)
    _align_pair(gene, iso1)
    _align_pair(gene, iso2)
    items = [gene, iso1, iso2]
        
    file = models.DBFile(
        uuid = uuid.uuid4(), 
        src_gb_file = "", 
        db_name = "",
    )
    record = models.Record(
        uuid = uuid.uuid4(), 
        file_uuid = file.uuid, 
        sequence_id = "", 
        organism = "DefaultOrganism", 
        taxonomy = ["DefaultTaxonomy"], 
    )
    gene = models.Gene(
        uuid = gene.guid, 
        record_uuid = record.uuid, 
        locus_tag = "DefaultLocusTag",
        gene_id = "", 
        db_xref = "", 
        location = gene.location, 
    )
    isoforms = [
        models.Isoform(
            uuid = iso.guid, 
            gene_uuid = gene.uuid, 
            protein_id = str(iso.guid), 
            product = "DefaultProduct", 
            location = iso.location, 
            translation = str(Seq(iso.seq).translate()), 
            src_gene_uuid = None, 
            rna_uuid = None, 
            
        ) for iso in items[1:]
    ]
    file_db.add_mem_isoforms(
        file = file, 
        record = record, 
        gene = gene, 
        isoforms = isoforms,
    )

    search(file_db, p, detector, [",".join(str(i.uuid) for i in isoforms)], blast_db_path, status = status, isoforms_to_duplicates = isoforms_to_duplicates)

def search(
    db: database.models.DB,
    p: pipeline.Pipeline,
    detector: ml.Detector,
    query_protein_ids_str: List[str],
    blast_db_path: str,
    status: SearchStatus = SearchStatus.construct(progress = 0, description = ""),
    isoforms_to_duplicates: Optional[Mapping[uuid.UUID, List[uuid.UUID]]] = None,
) -> str:
    status.set(0, "Preparing queries")
    tuples = [str_to_isoform_tuple(db, query_proteins) for query_proteins in query_protein_ids_str]
    queries = tuples_to_queries(tuples, num_groups=1)
    name = ";".join(query_protein_ids_str)
    return search_queries(db, p, detector, queries, name, blast_db_path, status, isoforms_to_duplicates)
def search_queries(
    db: database.models.DB,
    p: pipeline.Pipeline,
    detector: ml.Detector,
    queries: Queries,
    name: str,
    blast_db_path: str,
    status: SearchStatus,
    isoforms_to_duplicates: Optional[Mapping[uuid.UUID, List[uuid.UUID]]] = None,
) -> str:
    status.set(10, "BLAST running")
    blast.create_queires(db, queries, p.launch_folder)
    blast.run(p.launch_folder, blast_db_path, parallel = False)
    status.set(20, "Reading BLAST results")
    queries.isoform_to_file = get_isoforms_to_file(p.launch_folder)

    status.set(30, "Calculating features")
    matches = features.calc(db, p.launch_folder, queries)
    status.set(40, "Running ml model")
    detector.transform(matches)

    result_folder = pathutil.create_folder(p.launch_folder, "search_single", name)
    status.set(50, "Preparing results")
    dump(db, result_folder, matches, isoforms_to_duplicates)
    return result_folder
def matches_to_df(
    db: database.models.DB,
    isoforms_to_duplicates: Mapping[uuid.UUID, List[uuid.UUID]],
    matches: List[Match],
) -> pd.DataFrame:
    data = []
    for m in tqdm(matches):
        q_iso_a = db.isoforms[m.query_isoforms.a]
        q_iso_b = db.isoforms[m.query_isoforms.b]
        q_gene = db.genes[q_iso_a.gene_uuid]
        q_record = db.records[q_gene.record_uuid]
        q_file = db.files[q_record.file_uuid]

        h_iso_a = db.isoforms[m.hit_isoforms.a]
        h_iso_b = db.isoforms[m.hit_isoforms.b]
        h_gene = db.genes[h_iso_a.gene_uuid]
        h_record = db.records[h_gene.record_uuid]
        h_file = db.files[h_record.file_uuid]
        hit_as_types = as_type.get_isoforms_as_types(db, isoforms_to_duplicates, h_iso_a.uuid, h_iso_b.uuid)
        query_as_types = as_type.get_isoforms_as_types(db, isoforms_to_duplicates, q_iso_a.uuid, q_iso_b.uuid)
        intersection_as_types = hit_as_types & query_as_types
        row = {
            "query_isoforms": m.query_isoforms,
            "hit_isoforms": m.hit_isoforms,

            "hit_organism": m.hit_organism,
            "hit_db_name": m.hit_db_name,
            "hit_gene_uuid": h_iso_a.gene_uuid,
            "hit_protein_ids": f"{h_iso_a.protein_id}, {h_iso_b.protein_id}",
            "hit_locus_tag": h_gene.locus_tag,
            "hit_gene_id": h_gene.gene_id,
            "hit_db_xref": h_gene.db_xref,
            "hit_as_types": hit_as_types,
            "hit_as_types_max": max([len(as_type) for as_type in hit_as_types], default=0),

            "positive": m.positive,
            "predicted_positive": m.predicted_positive,
            "predicted_positive_probability": m.predicted_positive_probability,

            "isoform_blast_score": m.isoform_blast_score,
            "splicing_difference": m.splicing_difference,
            "splicing_similarity": m.splicing_similarity,
            "splicing_dissimilarity": m.splicing_dissimilarity,

            "query_gene_uuid": q_iso_a.gene_uuid,
            "query_protein_ids": f"{q_iso_a.protein_id}, {q_iso_b.protein_id}",
            "query_locus_tag": q_gene.locus_tag,
            "query_gene_id": q_gene.gene_id,
            "query_db_xref": q_gene.db_xref,
            "query_as_types": query_as_types,
            "query_as_types_max": max([len(as_type) for as_type in query_as_types], default=0),

            "intersection_as_types": intersection_as_types,
            "intersection_as_types_len": len(intersection_as_types),

            "conservative": int(m.predicted_positive),
            "conservative_probability": m.predicted_positive_probability,
            "db_name": q_file.db_name,
        }
        data.append(row)
    df = pd.DataFrame(data)
    return df
def get_isoforms_to_file(launch_folder: str) -> Mapping[uuid.UUID, str]:
    results_folder = pathutil.create_folder(launch_folder, "blast_results")
    isoforms_to_file: Dict[uuid.UUID, str] = {}
    for group_folder in tqdm(pathutil.get_sub_directories(results_folder)):
        for result_file in pathutil.file_list(group_folder, ".json"):
            with open(result_file, "r") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    _logger.exception("exception in file result file")
                    continue
                query_iso_str = data["BlastOutput2"]["report"]["results"]["search"]["query_title"]
                isoforms_to_file[uuid.UUID(query_iso_str)] = result_file
    return isoforms_to_file