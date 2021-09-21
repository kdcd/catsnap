import itertools
import random
import uuid
from collections import defaultdict
from copy import copy
from itertools import chain
from os.path import join
from typing import Dict, List, Tuple, Mapping, Set

from kd_common import funcutil, google, logutil
from kd_splicing import database, helpers
from kd_splicing.dataset.models import Dataset, DatasetMatch
from kd_splicing.models import IsoformTuple, Match, Queries
import pandas as pd

_GSHEET_TABLE = join("1HTbvSfzFsGE0l2lQbroUGnQAbOlMYH99np95iro9B8A", "dataset")
_logger = logutil.get_logger(__name__)


def read(db: database.models.DB) -> Dataset:
    df = google.sheet.read(_GSHEET_TABLE)
    query_hit_gene_to_records: Dict[Tuple[str, str],
                                    List[Mapping[str, str]]] = defaultdict(list)
    protein_id_to_isoform_uuid = {
        i.protein_id: i.uuid for i in db.isoforms.values()}
    matches = []
    records = df.to_dict('records')
    no_isoform_in_database = []
    excluded_protein_ids = ["NP_566850.3,NP_001326115.1"]
    excluded_queries = {helpers.str_to_isoform_tuple(
        db, i) for i in excluded_protein_ids}
    errors = []
    i = 0
    while i + 1 < len(records):
        r_a = records[i]
        r_b = records[i + 1]
        r_a["conserved"] = str(r_a["conserved"]).strip()
        r_b["conserved"] = str(r_b["conserved"]).strip()
        if r_a["query_locus_tag"] != r_b["query_locus_tag"]:
            errors.append(
                f"Malformed pair, query_locus_tags are not equal. Index: {i + 2}")
            i += 1
            continue
        if r_a["hit_gene"] != r_b["hit_gene"]:
            errors.append(
                f"Malformed pair. hit_genes are not equal. Index: {i + 2}")
            i += 1
            continue
        if r_a["query_protein_id"] == r_b["query_protein_id"]:
            errors.append(
                f"Malformed pair. query_protein_ids are equal. Index: {i + 2}")
            i += 1
            continue
        if r_a["hit_protein_id"] == r_b["hit_protein_id"]:
            errors.append(
                f"Malformed pair. hit_protein_ids are equal. Index: {i + 2}")
            i += 1
            continue
        if r_a["conserved"] not in {"1", "0"}:
            errors.append(
                f"Conserved must be 0 or 1. Got {r_a['conserved']}, Index: {i + 1}")
            i += 2
            continue
        if r_b["conserved"] not in {"1", "0"}:
            errors.append(
                f"Conserved must be 0 or 1. Got {r_b['conserved']}, Index: {i + 2}")
            i += 2
            continue
        if r_a["conserved"] != r_b["conserved"]:
            errors.append(
                f"Malformed pair. conserved are not equal. Index: {i + 2}")
            i += 2
            continue
        query_iso_a = protein_id_to_isoform_uuid.get(r_a["query_protein_id"])
        if not query_iso_a:
            no_isoform_in_database.append(r_a["query_protein_id"])
        query_iso_b = protein_id_to_isoform_uuid.get(r_b["query_protein_id"])
        if not query_iso_b:
            no_isoform_in_database.append(r_b["query_protein_id"])
        hit_iso_a = protein_id_to_isoform_uuid.get(r_a["hit_protein_id"])
        if not hit_iso_a:
            no_isoform_in_database.append(r_a["hit_protein_id"])
        hit_iso_b = protein_id_to_isoform_uuid.get(r_b["hit_protein_id"])
        if not hit_iso_b:
            no_isoform_in_database.append(r_b["hit_protein_id"])
        if query_iso_a and query_iso_b and hit_iso_a and hit_iso_b:
            if query_iso_a > query_iso_b:
                query_iso_a, query_iso_b = query_iso_b, query_iso_a
                hit_iso_a, hit_iso_b = hit_iso_b, hit_iso_a
            query = IsoformTuple(query_iso_a, query_iso_b)
            # if query in excluded_queries:
            #     i += 2
            #     continue
            matches.append(DatasetMatch(
                query=IsoformTuple(query_iso_a, query_iso_b),
                hit=IsoformTuple(hit_iso_a, hit_iso_b),
                positive=r_a["conserved"] == "1",
            ))
        i += 2
    if no_isoform_in_database:
        _logger.warn(
            f"No isoform in database {len(no_isoform_in_database)}:\n{no_isoform_in_database}")
    if errors:
        _logger.warn(f"Dataset read errors {len(errors)}:\n{errors}")
    return Dataset(matches)


def convert_dataset_matches_to_matches(matches: List[DatasetMatch]) -> List[Match]:
    result = []
    for m in matches:
        result.append(Match(
            query_isoforms=m.query,
            hit_isoforms=m.hit,
            positive=m.positive,
        ))
    return result


def fill_from_dataset(dataset: Dataset, matches: List[Match], db: database.models.DB) -> pd.DataFrame:
    query_hit_isoforms_to_match = {
        (m.query_isoforms, m.hit_isoforms): m
        for m in matches
    }
    not_found = []
    not_found_positive = 0
    not_found_negative = 0
    positive_count = 0
    negative_count = 0
    for dataset_m in dataset.matches:
        q_iso_a = db.isoforms[dataset_m.query.a]
        q_iso_b = db.isoforms[dataset_m.query.b]
        q_gene = db.genes[q_iso_a.gene_uuid]

        h_iso_a = db.isoforms[dataset_m.hit.a]
        h_iso_b = db.isoforms[dataset_m.hit.b]
        h_gene = db.genes[h_iso_a.gene_uuid]
        h_record = db.records[h_gene.record_uuid]
        m = query_hit_isoforms_to_match.get((dataset_m.query, dataset_m.hit))
        if dataset_m.positive:
            positive_count += 1
        else:
            negative_count += 1
        if m is None:
            not_found.append({
                    "q_protein_ids": f"{q_iso_a.protein_id}, {q_iso_b.protein_id}",
                    "q_locus_tag": q_gene.locus_tag,
                    "q_gene_id": q_gene.gene_id,
                    "h_protein_ids": f"{h_iso_a.protein_id} , {h_iso_b.protein_id}",
                    "h_locus_tag": h_gene.locus_tag,
                    "h_gene_id": h_gene.gene_id,
                    "h_organism": h_record.organism,
                    "positive": dataset_m.positive,
                })
            if dataset_m.positive:
                not_found_positive += 1
            else:
                not_found_negative += 1
        else:
            m.positive = dataset_m.positive
    _logger.info(f"""Fill from dataset stats. 
    Not found positive: {not_found_positive} {not_found_positive / positive_count}
    Not found negative: {not_found_negative} {not_found_negative / negative_count}""")

    return pd.DataFrame(not_found)


# Build dataset from:
# 1) all positive
# 2) 5% of negative from each organism that has positive
# 3) from organisms which don't have positive take positive_count * n - current_negative_count


def build_dataset_for_training(
    db: database.models.DB,
    matches: List[Match],
    negative_to_positive_ration: float = 5,
    negative_from_positive_organisms_ratio: float = 0.05
) -> List[Match]:
    positive = [copy(m) for m in matches if m.positive is True]
    negative = [copy(m) for m in matches if m.positive is False]
    rest = [copy(m) for m in matches if m.positive is None]
    random.seed(42)

    query_isoform_to_positive_organisms: Dict[IsoformTuple, Set[str]] = defaultdict(
        set)
    for m in positive:
        hit_iso_a = db.isoforms[m.hit_isoforms.a]
        hit_gene = db.genes[hit_iso_a.gene_uuid]
        hit_record = db.records[hit_gene.record_uuid]
        query_isoform_to_positive_organisms[m.query_isoforms].add(
            hit_record.organism)
    positive_organism_to_negative: Dict[str, List[Match]] = defaultdict(list)
    negative_from_negative_organisms: List[Match] = []
    for m in rest:
        hit_iso_a = db.isoforms[m.hit_isoforms.a]
        hit_gene = db.genes[hit_iso_a.gene_uuid]
        hit_record = db.records[hit_gene.record_uuid]
        if hit_record.organism in query_isoform_to_positive_organisms[m.query_isoforms]:
            positive_organism_to_negative[hit_record.organism].append(m)
        else:
            negative_from_negative_organisms.append(m)
    negative_from_positive_organisms_sample = []
    for negative_from_positive_organism in positive_organism_to_negative.values():
        k = negative_from_positive_organisms_ratio * \
            len(negative_from_positive_organism)
        negative_from_positive_organisms_sample.extend(
            random.sample(negative_from_positive_organism, int(k)))

    k = len(positive) * negative_to_positive_ration - len(negative) - \
        len(negative_from_positive_organisms_sample)
    negative_from_negative_organisms_sample = random.sample(
        negative_from_negative_organisms, int(k))
    dataset = positive + negative + negative_from_negative_organisms_sample + \
        negative_from_negative_organisms_sample
    for m in dataset:
        if m.positive is None:
            m.positive = False
    _calc_dataset_stats(dataset)
    return dataset


def _calc_dataset_stats(ds: List[Match]) -> None:
    positive = sum(m.positive for m in ds)
    negative = sum(not m.positive for m in ds)
    _logger.info(f"Dataset stats. Positive: {positive}. Negative: {negative}")


def get_queries(ds: Dataset, num_groups: int = 20) -> Queries:
    tuples = funcutil.unique([m.query for m in ds.matches])
    return helpers.tuples_to_queries(tuples, num_groups=num_groups)

if __name__ == "__main__":
    df = google.sheet.read(_GSHEET_TABLE)