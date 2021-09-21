
import re
from collections import defaultdict
from os.path import join
from typing import List, Optional, Dict, Mapping
import uuid
import shutil

from zipfile import ZipFile
import pandas as pd

from kd_common import excel, pathutil, pdutil
from kd_splicing import as_type, ct, database
from kd_splicing.models import FormattedResults, FormattedResultsItem, FormattedResultsQuery, IsoformTuple, Match


def dump(db: database.models.DB,  launch_folder: str, matches: List[Match], isoforms_to_duplicates: Optional[Mapping[uuid.UUID, List[uuid.UUID]]] = None):
    query_isoforms_to_matches: Dict[IsoformTuple,
                                    List[Match]] = defaultdict(list)
    for m in matches:
        query_isoforms_to_matches[m.query_isoforms].append(m)

    results_folder = pathutil.create_folder(launch_folder, "fasta")
    filtered = []
    for query_isoforms, query_matches in query_isoforms_to_matches.items():
        organism_to_best_match: Dict[str, Match] = {}
        for m in query_matches:
            hit_iso_a = db.isoforms[m.hit_isoforms.a]
            hit_iso_b = db.isoforms[m.hit_isoforms.b]
            hit_gene = db.genes[hit_iso_a.gene_uuid]
            hit_record = db.records[hit_gene.record_uuid]
            best_match = organism_to_best_match.get(hit_record.organism)
            if not best_match or best_match.predicted_positive_probability < m.predicted_positive_probability:
                organism_to_best_match[hit_record.organism] = m
        
        additional = []
        for m in query_matches:
            hit_iso_a = db.isoforms[m.hit_isoforms.a]
            hit_iso_b = db.isoforms[m.hit_isoforms.b]
            # if hit_iso_a.protein_id == "XP_009591645.1" and hit_iso_b.protein_id == "XP_018623801.1":
            #     additional.append(m)
        best_matches = additional + sorted(organism_to_best_match.values(), key=lambda m: (m.predicted_positive, m.predicted_positive_probability), reverse=True)
        filtered.extend(best_matches)
    

    data = []
    for m in filtered:
        hit_iso_a = db.isoforms[m.hit_isoforms.a]
        hit_iso_b = db.isoforms[m.hit_isoforms.b]
        hit_gene = db.genes[hit_iso_a.gene_uuid]
        hit_record = db.records[hit_gene.record_uuid]

        query_iso_a = db.isoforms[m.query_isoforms.a]
        query_iso_b = db.isoforms[m.query_isoforms.b]
        query_gene = db.genes[query_iso_a.gene_uuid]
        query_record = db.records[query_gene.record_uuid]

        row = {
            "query_isoforms": m.query_isoforms,
            "hit_isoforms": m.hit_isoforms,
            "query_protein_ids": f"{query_iso_a.protein_id}, {query_iso_b.protein_id}",
            "query_product": query_iso_a.product,
            "query_gene": query_gene.gene_id,
            "query_db_xref": query_gene.db_xref,
            

            "isoform_blast_score": m.isoform_blast_score,
            "splicing_difference": m.splicing_difference,
            "splicing_similarity": m.splicing_similarity,
            "splicing_dissimilarity": m.splicing_dissimilarity,

            "hit_organism": hit_record.organism,
            "hit_locus_tag": hit_gene.locus_tag,
            "hit_protein_ids": f"{hit_iso_a.protein_id}, {hit_iso_b.protein_id}",
            "hit_gene": hit_gene.gene_id,
            "hit_gene_db_xref": hit_gene.db_xref,
            "hit_product": hit_iso_a.product,
            
            "query_locus_tag": query_gene.locus_tag,
            "positive": m.positive,
            "predicted_positive": m.predicted_positive,
            "predicted_positive_probability": m.predicted_positive_probability,
        }
        if isoforms_to_duplicates:
            row.update({
                "query_as_types": as_type.get_isoforms_as_types(db, isoforms_to_duplicates, query_iso_a.uuid, query_iso_b.uuid),
                "hit_as_types": as_type.get_isoforms_as_types(db, isoforms_to_duplicates, hit_iso_a.uuid, hit_iso_b.uuid),
            })
        data.append(row)
        
    df = pd.DataFrame(data)
    dump_scores(df, launch_folder)
    dump_to_fasta(db, launch_folder, matches, isoforms_to_duplicates)
    shutil.make_archive(join(launch_folder, "results"), 'zip', join(launch_folder, "results"))


def dump_scores(df: pd.DataFrame, launch_folder: str) -> None:
    queries = df.drop_duplicates("query_isoforms")
    organisms = df.sort_values(["predicted_positive","predicted_positive_probability"], ascending=False)
                  
    excel.write_nested_df([
        queries[[
                "query_locus_tag",
                "query_protein_ids",
                "query_product",
                # "query_as_types",
                "query_gene",
                "query_db_xref",
                "query_isoforms",
                ]],
        organisms[[
            "positive",
            "predicted_positive",
            "predicted_positive_probability",

            "isoform_blast_score",
            "splicing_difference",
            "splicing_similarity",
            "splicing_dissimilarity",

            "hit_protein_ids",
            "hit_locus_tag",
            "hit_organism",
            # "hit_as_types",
            "hit_gene",
            "hit_gene_db_xref",
            "hit_product",
            "query_isoforms",
            "hit_isoforms",
        ]],
    ], [
        "query_isoforms",
    ], join(launch_folder, "scores.xlsx")
    )


def _clean_str(s: Optional[str]) -> str:
    return re.sub(" ", "_", s) if s is not None else ""

def _clean_file_name(s: str) -> str:
    return re.sub("/", "_", s)


def dump_to_fasta(db: database.models.DB, launch_folder: str, matches: List[Match], isoforms_to_duplicates: Optional[Mapping[uuid.UUID, List[uuid.UUID]]] = None) -> None:
    query_isoforms_to_matches: Dict[IsoformTuple,
                                    List[Match]] = defaultdict(list)
    for m in matches:
        query_isoforms_to_matches[m.query_isoforms].append(m)

    results_folder = pathutil.create_folder(launch_folder, "results", "best_ortholog_in_a_species")
    results_full_folder = pathutil.create_folder(launch_folder, "results", "all_orthologs_in_a_species")
    for query_isoforms, query_matches in query_isoforms_to_matches.items():
        organism_to_best_match: Dict[str, Match] = {}
        organism_to_matches: Dict[str, List[Match]] = defaultdict(list)
        for m in query_matches:
            hit_iso_a = db.isoforms[m.hit_isoforms.a]
            hit_iso_b = db.isoforms[m.hit_isoforms.b]
            hit_gene = db.genes[hit_iso_a.gene_uuid]
            hit_record = db.records[hit_gene.record_uuid]
            best_match = organism_to_best_match.get(hit_record.organism)
            organism_to_matches[hit_record.organism].append(m)
            if not best_match or best_match.predicted_positive_probability < m.predicted_positive_probability:
                organism_to_best_match[hit_record.organism] = m
        
        additional = []
        # for m in query_matches:
        #     hit_iso_a = db.isoforms[m.hit_isoforms.a]
        #     hit_iso_b = db.isoforms[m.hit_isoforms.b]
        #     if hit_iso_a.protein_id == "XP_009591645.1" and hit_iso_b.protein_id == "XP_018623801.1":
        #         additional.append(m)
        best_matches :List[Match] = additional + sorted(organism_to_best_match.values(), key=lambda m: (m.predicted_positive, m.predicted_positive_probability), reverse=True)
        for organism, matches in organism_to_matches.items():
            matches = sorted(matches, key=lambda m: (m.predicted_positive, m.predicted_positive_probability), reverse=True)
            filtered_matches = [m for m in matches if m.predicted_positive_probability > 0.0001]
            if len(filtered_matches) < 10:
                organism_to_matches[organism] = filtered_matches
            else:
                organism_to_matches[organism] = filtered_matches

        query_iso_a = db.isoforms[query_isoforms.a]
        query_iso_b = db.isoforms[query_isoforms.b]
        query_gene = db.genes[query_iso_a.gene_uuid]
        query_record = db.records[query_gene.record_uuid]

        filename = query_gene.gene_id
        if filename is None or filename.startswith("GeneID"):
            filename = query_gene.locus_tag
        if filename is None:
            filename = query_gene.db_xref
        if filename is None:
            filename = ""
        filename += f"_{query_iso_a.protein_id}, {query_iso_b.protein_id}"
        filename = _clean_file_name(filename)
        file_path = join(results_folder, filename + ".fasta")

        with open(file_path, "w") as f:
            
            name = f"{query_record.organism}_{query_gene.locus_tag}_{query_iso_a.protein_id}"
            if isoforms_to_duplicates:
                query_as_types = as_type.get_isoforms_as_types(db, isoforms_to_duplicates, query_iso_a.uuid, query_iso_b.uuid)
                print(query_as_types)
                name += "_" + "|".join(";".join(".".join(j) for j in i) for i in query_as_types)
            f.write(f">{name}\n")
            f.write(f"{query_iso_a.translation}\n")

            name = f"{query_record.organism}_{query_gene.locus_tag}_{query_iso_b.protein_id}"
            f.write(f">{name}\n")
            f.write(f"{query_iso_b.translation}\n")

            for m in best_matches:
                if m.hit_organism == query_record.organism: continue

                hit_iso_a = db.isoforms[m.hit_isoforms.a]
                hit_iso_b = db.isoforms[m.hit_isoforms.b]
                hit_gene = db.genes[hit_iso_a.gene_uuid]
                hit_record = db.records[hit_gene.record_uuid]
                locus_tag = hit_gene.locus_tag if hit_gene.locus_tag else hit_gene.gene_id

                m.predicted_positive_probability

                name = f"{hit_record.organism}_{locus_tag}_{hit_iso_a.product}_{hit_iso_a.protein_id}"
                if isoforms_to_duplicates:
                    hit_as_types = as_type.get_isoforms_as_types(db, isoforms_to_duplicates, hit_iso_a.uuid, hit_iso_b.uuid)
                    name += "_" + "|".join(";".join(".".join(j) for j in i) for i in hit_as_types)
                f.write(f">{name}\n")
                f.write(f"{hit_iso_a.translation}\n")

                name = f"{hit_record.organism}_{locus_tag}_{hit_iso_b.product}_{hit_iso_b.protein_id}"
                f.write(f">{name}\n")
                f.write(f"{hit_iso_b.translation}\n")
        
        with open(join(results_full_folder, filename + ".fasta"), "w") as f:
            name = f"{query_record.organism}_{query_gene.locus_tag}_{query_iso_a.protein_id}"
            f.write(f">{name}\n")
            f.write(f"{query_iso_a.translation}\n")

            name = f"{query_record.organism}_{query_gene.locus_tag}_{query_iso_b.protein_id}"
            f.write(f">{name}\n")
            f.write(f"{query_iso_b.translation}\n")

            for best_m  in best_matches:
                for m in organism_to_matches[best_m.hit_organism]:
                    hit_iso_a = db.isoforms[m.hit_isoforms.a]
                    hit_iso_b = db.isoforms[m.hit_isoforms.b]
                    hit_gene = db.genes[hit_iso_a.gene_uuid]
                    hit_record = db.records[hit_gene.record_uuid]
                    locus_tag = hit_gene.locus_tag if hit_gene.locus_tag else hit_gene.gene_id

                    name = f"{m.predicted_positive_probability:.4f}_{hit_record.organism}_{locus_tag}_{hit_iso_a.product}_{hit_iso_a.protein_id}"
                    if isoforms_to_duplicates:
                        hit_as_types = as_type.get_isoforms_as_types(db, isoforms_to_duplicates, hit_iso_a.uuid, hit_iso_b.uuid)
                        name += "_" + "|".join(";".join(".".join(j) for j in i) for i in hit_as_types)
                    f.write(f">{name}\n")
                    f.write(f"{hit_iso_a.translation}\n")

                    name = f"{hit_record.organism}_{locus_tag}_{hit_iso_b.protein_id}"
                    f.write(f">{hit_record.organism}_{locus_tag}_{hit_iso_b.protein_id}\n")
                    f.write(f"{hit_iso_b.translation}\n")
