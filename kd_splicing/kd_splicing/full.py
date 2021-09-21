import itertools
import os
import uuid
from collections import defaultdict
from dataclasses import dataclass
from statistics import mean, median
from typing import Any, Dict, List, Mapping, Optional, Union, Set
from kd_common import pdutil

import numpy as np
import pandas as pd
from tqdm import tqdm

from kd_common import excel, google, logutil, pathutil
from kd_splicing import as_type, blast, database, features, pipeline
from kd_splicing.models import IsoformTuple, Queries, SimpleMatch
from kd_splicing.location.utils import symmetric_difference
import pickle
import json

_logger = logutil.get_logger(__name__)


##############
# Queries
##############

def _find_duplicates(db: database.models.DB, isoforms: List[uuid.UUID]) -> Set[uuid.UUID]:
    duplicated: Set[uuid.UUID] = set()
    for i in range(len(isoforms)):
        if isoforms[i] in duplicated:
            continue
        for j in range(i + 1, len(isoforms)):
            if isoforms[j] in duplicated:
                continue
            splicing = symmetric_difference(
                db.isoforms[isoforms[i]].location, db.isoforms[isoforms[j]].location)
            if splicing.length() == 0:
                duplicated.add(isoforms[j])
    return duplicated


def get_query_isoforms(db: database.models.DB, num_groups: int = 20, organism: Optional[str] = "Arabidopsis thaliana", db_name: Optional[str] = "refseq") -> Queries:
    gene_to_isoforms: Dict[uuid.UUID, List[uuid.UUID]] = defaultdict(list)
    isoforms_count: int = 0
    for iso in db.isoforms.values():
        gene = db.genes[iso.gene_uuid]
        record = db.records[gene.record_uuid]
        f = db.files[record.file_uuid]
        if organism is None or record.organism == organism  and f.db_name == db_name:
            gene_to_isoforms[iso.gene_uuid].append(iso.uuid)
            isoforms_count += 1

    tuples = []
    isoform_to_idx = {}
    group_count = itertools.cycle(range(0, num_groups))
    isoform_to_group = {}
    group_size: Dict[int, int] = defaultdict(int)
    duplicated_isoforms_count: int = 0
    all_pairs_count: int = 0

    for gene_isoforms in tqdm(list(gene_to_isoforms.values()), desc="full.get_query_isoforms"):
        gene_isoforms = sorted(gene_isoforms, key= lambda i: 0 if db.isoforms[i].src_gene_uuid is None else 1)
        duplicates = _find_duplicates(db, gene_isoforms)
        duplicated_isoforms_count += len(duplicates)
        all_pairs_count += int((len(gene_isoforms) *
                                (len(gene_isoforms) - 1)) / 2)
        for i in range(len(gene_isoforms)):
            iso_uuid = gene_isoforms[i]
            if iso_uuid in duplicates:
                continue
            group = next(group_count)
            isoform_to_group[iso_uuid] = group
            isoform_to_idx[iso_uuid] = group_size[group]
            group_size[group] += 1
            for j in range(i + 1, len(gene_isoforms)):
                if gene_isoforms[j] in duplicates:
                    continue
                tuples.append(IsoformTuple(gene_isoforms[i], gene_isoforms[j]))
    isoforms = list({
        iso
        for iso_tuple in tuples
        for iso in (iso_tuple.a, iso_tuple.b)
    })
    _logger.info(f"Isoforms count: {isoforms_count}")
    _logger.info(
        f"Duplicated isoforms:{duplicated_isoforms_count} {duplicated_isoforms_count / isoforms_count}")
    _logger.info(
        f"Queries isoform pairs: {len(tuples)} {len(tuples) / all_pairs_count}")
    return Queries(
        isoforms=isoforms,
        tuples=tuples,
        isoform_to_idx=isoform_to_idx,
        isoform_to_group=isoform_to_group,
    )


def load_queries(queries_path: str) -> Queries:
    with open(queries_path, "rb") as f:
        return pickle.load(f)



##############
# Stats
##############


def _stats_folder(launch_folder: str) -> str:
    return pathutil.create_folder(launch_folder, "stats")


@dataclass
class Classification:
    organism_class: str
    order: str
    family: str
    group: str


def _get_taxonomy() -> Mapping[str, Classification]:
    df = google.sheet.read(os.path.join(
        "1TynnB55W25xJPtwCVXpQJFF3APqODsUC0CLTNo-hCss", "taxonomy 2021"))
    organism_to_classification = {}
    for organism_class, order, family, organism, group in df[["class", "order", "family", "organism", "groups"]].values:
        organism_to_classification[organism] = Classification(
            organism_class=organism_class,
            order=order,
            family=family,
            group=group,
        )
    return organism_to_classification

def get_taxonomy_df() -> pd.DataFrame:
    def get_group_with_brassicalis(group: str, order: str) -> str:
        if group == "dicots":
            return group + " " + ("Brassicales" if order == "Brassicales" else "NotBrassicales")
        return group
        
    df = google.sheet.read(os.path.join(
        "1TynnB55W25xJPtwCVXpQJFF3APqODsUC0CLTNo-hCss", "taxonomy"))
    df = df.rename(columns={"groups":"group"})
    df["group_with_brassicalis"] = pdutil.apply(df[["group", "order"]], get_group_with_brassicalis)
    return df.set_index("organism")

def get_basic_df(
    db: database.models.DB, 
    query_to_matches: Mapping[IsoformTuple, List[SimpleMatch]],
    isoforms_to_duplicates: Optional[Mapping[uuid.UUID, List[uuid.UUID]]] = None, 
) -> pd.DataFrame:
    data: List[Dict[str, Any]] = []
    organism_to_classification = _get_taxonomy()
    for query, matches in tqdm(query_to_matches.items()):
        q_iso_a = db.isoforms[query.a]
        q_iso_b = db.isoforms[query.b]
        q_gene = db.genes[q_iso_a.gene_uuid]
        query_as_types = None
        if isoforms_to_duplicates is not None:
            query_as_types = as_type.get_isoforms_as_types(db, isoforms_to_duplicates, q_iso_a.uuid, q_iso_b.uuid)
        
        for m in matches:
            m_iso_a = db.isoforms[m.hit_isoforms.a]
            m_iso_b = db.isoforms[m.hit_isoforms.b]
            m_gene = db.genes[m_iso_a.gene_uuid]
            m_record = db.records[m_gene.record_uuid]
            m_file = db.files[m_record.file_uuid]
            row = {
                "organism": m_record.organism,
                "hit_isoforms": m.hit_isoforms,
                "hit_gene_id": m_gene.gene_id,
                "hit_protein_ids": f"{m_iso_a.protein_id}, {m_iso_b.protein_id}",

                "query_isoforms": query,
                "query_gene_uuid": q_iso_a.gene_uuid,
                "query_protein_ids": f"{q_iso_a.protein_id}, {q_iso_b.protein_id}",
                "query_locus_tag": q_gene.locus_tag,
                "query_gene_id": q_gene.gene_id,
                "query_db_xref": q_gene.db_xref,

                "conservative": int(m.predicted_positive),
                "conservative_probability": m.predicted_positive_probability,
                "db_name": m_file.db_name,
            }

            # if m.predicted_positive_probability > 0.5 and query_as_types is not None and isoforms_to_duplicates is not None :
            hit_as_types = as_type.get_isoforms_as_types(db, isoforms_to_duplicates, m_iso_a.uuid, m_iso_b.uuid)
            intersection_as_types = hit_as_types & query_as_types
            row.update({
                "hit_as_types": hit_as_types,
                "hit_as_types_max": max([len(as_type) for as_type in hit_as_types], default=0),
                "query_as_types": query_as_types,
                "query_as_types_max": max([len(as_type) for as_type in query_as_types], default=0),
                "intersection_as_types": intersection_as_types,
                "intersection_as_types_len": len(intersection_as_types),
            })

            classification = organism_to_classification.get(m_record.organism)
            if classification:
                row["group"] = classification.group
                row["order"] = classification.order
                row["family"] = classification.family
                row["group_with_brassicalis"] = classification.group
                if classification.group == "dicots":
                    row["group_with_brassicalis"] += " " + ("Brassicales" if classification.order == "Brassicales" else "NotBrassicales")

            data.append(row)
    df = pd.DataFrame(data)
    df = df.sort_values(["conservative_probability", "conservative", "db_name"],
                        ascending=False).drop_duplicates(["query_isoforms", "organism"])
    return df


def group_stats(folder: str, df: pd.DataFrame, db_counts: pd.DataFrame, name_cols: List[str], name: str, normalization: Union[str, int], drop_duplicates_group: Optional[List[str]] = None) -> None:
    if isinstance(normalization, str):
        size = len(df.drop_duplicates(normalization))
    else:
        size = normalization

    if drop_duplicates_group:
        df = df.sort_values("conservative", ascending=False).drop_duplicates(
            drop_duplicates_group)
    df = df.groupby(name_cols).sum()
    df = df[["conservative"]]
    df["conservative_ratio"] = df["conservative"] / size
    # df["size"] = size
    df = df.sort_values("conservative_ratio", ascending=False)

    df = df.join(db_counts, on=name_cols[-1])
    _logger.info(f"{name}:\n{df.to_string()}")
    excel.write(df.reset_index(), os.path.join(folder, name + ".xlsx"))
    return df


def conservative_organisms_count_histogram(df: pd.DataFrame) -> None:
    df = df[df["conservative"] > 0].drop_duplicates(
        ["query_gene_uuid", "organism"])
    df.groupby("query_gene_uuid").size().values_count()

def get_single_order(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["conservative"] > 0].drop_duplicates(["query_isoforms", "order"]).groupby("query_isoforms").filter(lambda g: len(g) == 1)


def gene_conservative_stats(df: pd.DataFrame, dbdf: pd.DataFrame, db: database.models.DB,   all_pairs: Queries, launch_folder: str) -> None:
    _logger.info(f"Start calculate gene conservative stats")

    organism_pair_count = defaultdict(int)
    for iso_tuple in all_pairs.tuples:
        iso_a = db.isoforms[iso_tuple.a]
        gene = db.genes[iso_a.gene_uuid]
        record = db.records[gene.record_uuid]
        organism_pair_count[record.organism] += 1

    organism_deduplicated_isoform_count = defaultdict(int)
    for iso_uuid in all_pairs.isoforms:
        iso = db.isoforms[iso_uuid]
        gene = db.genes[iso.gene_uuid]
        record = db.records[gene.record_uuid]
        organism_deduplicated_isoform_count[record.organism] += 1 

    stats_folder = pathutil.create_folder(launch_folder, "stats", "full")
    as_events_per_gene = df.drop_duplicates(
        "query_isoforms").groupby("query_gene_uuid").size().mean()
    pairs = len(df.drop_duplicates("query_isoforms"))
    genes = len(df.drop_duplicates("query_gene_uuid"))
    conservative_pairs = len(
        df[df["conservative"] > 0].drop_duplicates("query_isoforms"))
    conservative_genes = len(
        df[df["conservative"] > 0].drop_duplicates("query_gene_uuid"))
    single_order = get_single_order(df)
    conservative_brassicales_pairs = len(single_order[single_order["order"] == "Brassicales"])
    conservative_brassicales_genes = len(single_order[single_order["order"] == "Brassicales"].drop_duplicates("query_gene_uuid"))

    db_isoform_counts = pd.concat([
        dbdf.drop_duplicates("gene_uuid").organism.value_counts().rename("gene_count"), 
        dbdf.organism.value_counts().rename("isoform_count"),
        pd.Series(organism_pair_count).rename("pair_count"),
        pd.Series(organism_deduplicated_isoform_count).rename("deduplicated_iso_count"),
    ], axis=1)
    taxonomy = get_taxonomy_df()
    db_group_counts = db_isoform_counts.join(taxonomy[["group"]]).groupby("group").sum()
    db_group_with_brassicalis_counts = db_isoform_counts.join(taxonomy[["group_with_brassicalis"]]).groupby("group_with_brassicalis").sum()

    _logger.info(f"""
    Genes:{genes}
    Genes with conservative alt pairs:{conservative_genes}, {float(conservative_genes)/genes}
    alt pairs:{pairs}
    alt pairs per gene:{as_events_per_gene}
    Conserved alt pairs:{conservative_pairs}, {float(conservative_pairs)/pairs}
    Conserved alt pairs in brassicales: {conservative_brassicales_pairs}, {float(conservative_brassicales_pairs) / pairs}""")

    group_stats(stats_folder, df, db_isoform_counts, ["group", "order", "organism"],
                "conservative_pairs_per_organism", "query_isoforms")
    group_stats(stats_folder, df, db_group_counts, ["group"], "conservative_pairs_per_group",
                "query_isoforms", ["group", "query_isoforms"])
    group_stats(stats_folder, df, db_isoform_counts,  ["group", "order", "organism"], "conservative_genes_per_organism",
                "query_gene_uuid", ["organism", "query_gene_uuid"],)
    group_stats(stats_folder, df, db_group_counts,  ["group"], "conservative_genes_per_group",
                "query_gene_uuid", ["group", "query_gene_uuid"],)
    group_stats(stats_folder, df, db_group_with_brassicalis_counts,  ["group_with_brassicalis"], "conservative_genes_per_group_with_brassicalis",
                "query_gene_uuid", ["group_with_brassicalis", "query_gene_uuid"],)


SELECTED_ORGANISMS_CHAMALA = {
    "Amborella trichopoda", "Glycine max", "Medicago truncatula", "Oryza sativa Japonica Group",
    "Phaseolus vulgaris", "Populus trichocarpa", "Solanum lycopersicum", "Vitis vinifera"
}

SELECTED_ORGANISMS_MEI = {
    "Zea mays", "Sorghum bicolor", "Oryza sativa Japonica Group",
    "Brachypodium distachyon", "Setaria italica", "Musa acuminata subsp. malaccensis", "Elaeis guineensis", 
    "Amborella trichopoda"
}


def selected_organisms_stats(df: pd.DataFrame, dbdf: pd.DataFrame, selected_organisms: Set[str], name: str, launch_folder: str) -> None:
    _logger.info(f"Start calculate selected organisms stats")
    stats_folder = pathutil.create_folder(launch_folder, "stats", name)
    as_events_per_gene = df.drop_duplicates(
        "query_isoforms").groupby("query_gene_uuid").size().mean()
    pairs = len(df.drop_duplicates("query_isoforms"))
    genes = len(df.drop_duplicates("query_gene_uuid"))

    df = df[df["organism"].isin(selected_organisms)]

    conservative_pairs = len(
        df[df["conservative"] > 0].drop_duplicates("query_isoforms"))
    conservative_genes = len(
        df[df["conservative"] > 0].drop_duplicates("query_gene_uuid"))

    db_isoform_counts = pd.concat([
        dbdf.drop_duplicates("gene_uuid").organism.value_counts().rename("organism_gene_count"), 
        dbdf.organism.value_counts().rename("organism_isoform_count")
    ], axis=1)

    _logger.info(f"""
    Genes:{genes}
    Genes with conservative alt pairs:{conservative_genes}, {float(conservative_genes)/genes}
    alt pairs:{pairs}
    alt pairs per gene:{as_events_per_gene}
    Conserved alt pairs:{conservative_pairs}, {float(conservative_pairs)/pairs}""")
    group_stats(stats_folder, df, db_isoform_counts, ["group", "order", "organism"],
                "selected_conservative_per_organism_normalized_by_conservative_events", conservative_pairs)
    group_stats(stats_folder, df, db_isoform_counts, ["group", "order", "organism"],
                "selected_conservative_per_organism", "query_isoforms")

    genes_df = df[df["conservative"] > 0].drop_duplicates("query_gene_uuid")

    excel.write(genes_df, os.path.join(stats_folder, "uniq_genes.xlsx"))
