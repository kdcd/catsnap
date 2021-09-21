from __future__ import annotations
from kd_splicing.exception import GeneNotFoundException
from kd_splicing.utils import extractutil
from kd_splicing import ct
from kd_common import logutil, pathutil, pdutil
from tqdm import tqdm
import pandas as pd
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
import Bio.SeqIO
import Bio

from uuid import UUID
import multiprocessing
import os
import uuid
import pickle
from collections import Counter, defaultdict
from functools import partial
from os.path import basename
from typing import Optional, Tuple, List, Mapping, Any, Dict
from dataclasses import dataclass, field
import bz2
import gzip

from kd_splicing.database.models import Gene, Isoform, DBPart, DBFile, Record, RNA
from kd_splicing.location.models import Location, LocationPart

_logger = logutil.get_logger(__name__)


def _get_qualifier(db: DBPart, feature: SeqFeature, qualifier_name: str) -> Optional[str]:
    values = feature.qualifiers.get(qualifier_name, None)
    if not values or len(values) == 0:
        return None
    if qualifier_name == ct.DB_XREF:
        values = [value for value in values if value.startswith("GeneID:")]
    if len(values) > 1:
        db.warn(
            f"Multiple values for qualifier {qualifier_name} in feature:\n{feature}")
    if not values:
        return None
    return values[0]


_MAX_PARTS_SIZE = 500


def _convert_location(db: DBPart, loc: FeatureLocation) -> Location:
    if len(loc.parts) > _MAX_PARTS_SIZE:
        db.warn(
            f"Too many parts in location {len(loc.parts)}. Cut to {_MAX_PARTS_SIZE}")
    parts = []
    for i in range(min(len(loc.parts), _MAX_PARTS_SIZE)):
        part = loc.parts[i]
        new_part = LocationPart(
            start=part.start.position + (-1 if part.strand == -1 else 0),
            end=part.end.position - 1 + (1 if part.strand == 1 else 0),
            strand=part.strand
        )
        parts.append(new_part)
    return Location(parts)


def _create_gene(db: DBPart, feature: SeqFeature, record: Record, seq_record: SeqRecord) -> Gene:
    return Gene(
        uuid=uuid.uuid4(),
        record_uuid=record.uuid,
        locus_tag=_get_qualifier(db, feature, ct.LOCUS_TAG),
        gene_id=_get_qualifier(db, feature, ct.GENE),
        db_xref=_get_qualifier(db, feature, ct.DB_XREF),
        location=_convert_location(db, feature.location)
    )


@dataclass
class _RawIsoform:
    uuid: uuid.UUID

    gene_locus_tag: Optional[str]
    gene_id: Optional[str]
    gene_db_xref: Optional[str]

    product: Optional[str]
    protein_id: Optional[str]
    location: Location

    translation: str


def _create_raw_isoform(db: DBPart, feature: SeqFeature, record: SeqRecord) -> Optional[_RawIsoform]:
    translation = _get_qualifier(db, feature, ct.TRANSLATION)
    if not translation:
        return None
    return _RawIsoform(
        uuid=uuid.uuid4(),

        gene_locus_tag=_get_qualifier(db, feature, ct.LOCUS_TAG),
        gene_id=_get_qualifier(db, feature, ct.GENE),
        gene_db_xref=_get_qualifier(db, feature, ct.DB_XREF),

        product=_get_qualifier(db, feature, ct.PRODUCT),
        protein_id=_get_qualifier(db, feature, ct.PROTEIN_ID),
        location=_convert_location(db, feature.location),

        translation=translation,
    )


def _create_rna(db: DBPart, gene: Gene, feature: SeqFeature, record: SeqRecord) -> RNA:
    return RNA(
        uuid=uuid.uuid4(),
        gene_uuid=gene.uuid,
        transcript_id =_get_qualifier(db, feature, "transcript_id"),
        location=_convert_location(db, feature.location),
        src_gene_uuid=None,
    )

def _create_isoform(raw_isoform: _RawIsoform, gene: Gene) -> Isoform:
    return Isoform(
        uuid=raw_isoform.uuid,
        gene_uuid=gene.uuid,
        protein_id=raw_isoform.protein_id,
        product=raw_isoform.product,
        location=raw_isoform.location,
        translation=raw_isoform.translation,
        src_gene_uuid=None,
        rna_uuid = None,
    )


def process_record(db: DBPart, db_file: DBFile, seq_record: SeqRecord) -> Record:
    record = Record(
        uuid=uuid.uuid4(),
        file_uuid=db_file.uuid,
        sequence_id=seq_record.id,
        organism=seq_record.annotations["organism"],
        taxonomy=seq_record.annotations["taxonomy"],
    )
    db.records[record.uuid] = record
    return record


_FEATURE_TYPE_INDEX = {
    "gene": 0,
    "mRNA": 1,
    "CDS": 2,
}


@dataclass
class _RawFeature:
    feature: SeqFeature
    min_pos: int

    def __lt__(self, other: _RawFeature) -> bool:
        if self.min_pos < other.min_pos:
            return True
        if self.min_pos == other.min_pos and _FEATURE_TYPE_INDEX[self.feature.type] < _FEATURE_TYPE_INDEX[other.feature.type]:
            return True
        return False


def _get_raw_features(seq_record: SeqRecord) -> List[_RawFeature]:
    result = []
    for feature in seq_record.features:
        if feature.type not in _FEATURE_TYPE_INDEX.keys():
            continue
        min_pos = min(min(p.start.position, p.end.position)
                      for p in feature.location.parts)
        result.append(_RawFeature(
            feature=feature,
            min_pos=min_pos,
        ))
    return result


def process_features(db: DBPart, db_file: DBFile, record: Record, seq_record: SeqRecord) -> None:
    raw_isoforms: List[_RawIsoform] = []
    isoforms = {}
    genes = {}
    rnas = {}
    locustag2gene = {}
    geneid2gene = {}
    db_xref2gene = {}
    gene_isoforms_count: Dict[uuid.UUID, int] = defaultdict(int)
    gene: Optional[Gene] = None
    raw_features = _get_raw_features(seq_record)
    raw_features.sort()
    for raw_feature in raw_features:
        feature = raw_feature.feature
        try:
            if feature.type == "gene":
                gene = _create_gene(db, feature, record, seq_record)
                genes[gene.uuid] = gene
                if gene.locus_tag:
                    locustag2gene[gene.locus_tag] = gene
                if gene.gene_id:
                    geneid2gene[gene.gene_id] = gene
                if gene.db_xref:
                    db_xref2gene[gene.db_xref] = gene
            elif feature.type == "CDS":
                raw_isoform = _create_raw_isoform(db, feature, seq_record)
                if not raw_isoform:
                    continue

                gene = None
                if raw_isoform.gene_locus_tag:
                    gene = locustag2gene[raw_isoform.gene_locus_tag]
                elif raw_isoform.gene_db_xref:
                    gene = db_xref2gene[raw_isoform.gene_db_xref]
                elif raw_isoform.gene_id:
                    gene = geneid2gene[raw_isoform.gene_id]

                if gene:
                    if raw_isoform.location not in gene.location:
                        db.stats["location_mismatch"] += 1
                        continue
                    gene_isoforms_count[gene.uuid] += 1
                    isoforms[raw_isoform.uuid] = _create_isoform(
                        raw_isoform, gene)
                else:
                    db.stats["absent_genes"] += 1
            elif feature.type == "mRNA":
                gene = None
                locus_tag = _get_qualifier(db, feature, ct.LOCUS_TAG)
                db_xref = _get_qualifier(db, feature, ct.DB_XREF)
                gene_id = _get_qualifier(db, feature, ct.GENE)
                if locus_tag:
                    gene = locustag2gene[locus_tag]
                elif db_xref:
                    gene = db_xref2gene[db_xref]
                elif gene_id:
                    gene = geneid2gene[gene_id]

                if not gene:
                    db.stats["absent_genes"] += 1
                    continue
                rna = _create_rna(db, gene, feature, record)

                if rna.location not in gene.location:
                    db.stats["location_mismatch"] += 1
                    continue
                rnas[rna.uuid] = rna
                    
        except Exception as e:
            db.exception(
                f"Exception happened in file:\n {db_file.src_gb_file}\n During processing feature:\n {feature}")

    db.stats["all_genes"] = len(genes)
    db.stats["all_isoforms"] = len(isoforms)
    db.isoforms.update(isoforms)
    db.genes.update(genes)
    db.rnas.update(rnas)


def process_file(src_gb_file: str, dst_file: str, db_name: str) -> None:
    db = DBPart()
    try:
        db_file = DBFile(
            uuid=uuid.uuid4(),
            src_gb_file=src_gb_file,
            db_name=db_name,
        )
        db.files[db_file.uuid] = db_file
        for gb_record in Bio.SeqIO.parse(open(src_gb_file, "r"), "genbank"):
            record = process_record(db, db_file, gb_record)
            process_features(db, db_file, record, gb_record)

        
        db.stats["df_isoforms"] = len(db.isoforms)
        db.stats["df_genes"] = len(db.genes)

        if len(db.isoforms) == 0:
            db_file = DBFile(
                uuid=uuid.uuid4(),
                src_gb_file=src_gb_file,
                db_name=db_name,
            )

            organisms = {r.organism for r in db.records.values()}
            _logger.warn(
                f"No isoforms, File:{src_gb_file}\norganisms: {organisms}\nstats:\n{pd.DataFrame(db.stats.items()).to_string()}")
            # return

        with gzip.GzipFile(dst_file + ".pgz", "w") as f: 
            pickle.dump(db, f, protocol=pickle.HIGHEST_PROTOCOL) # type: ignore
    except Exception as e:
        db.exception(
            f"Exception happened during processing {src_gb_file}")


def read(src_file: str, dst_folder: Optional[str], db_name: str, check_existence: bool = True, remove_extracted_file: bool = True) -> None:
    try:
        if src_file[-3:] != ".gz":
            _logger.warn(f"Wrong file extension: {src_file}")
            return

        tmp_file = src_file[:-3]
        dst_file = os.path.join(dst_folder, basename(
            tmp_file)) if dst_folder is not None else None

        _logger.info(f"Extract file{tmp_file}")
        extractutil.extract_file(src_file, tmp_file)

        if dst_file:
            process_file(tmp_file, dst_file, db_name)

        if remove_extracted_file:
            os.remove(tmp_file)
    except Exception as e:
        os.remove(src_file)
        _logger.exception(f"Read exception {src_file}")


def read_folder(src_folder: str, dst_folder: Optional[str], db_name: str, extension: str, check_existence: bool = True, parallel: bool = True,
                remove_extracted_file: bool = True, reset_folder: bool = False) -> None:
    files = pathutil.file_list(src_folder, extension)
    read_files(
        files=files,
        dst_folder=dst_folder,
        db_name=db_name,
        extension=extension,
        check_existence=check_existence,
        parallel=parallel,
        remove_extracted_file=remove_extracted_file,
    )

def read_files(files: List[str], dst_folder: Optional[str], db_name: str, extension: str, check_existence: bool = True, parallel: bool = True,
                remove_extracted_file: bool = True, reset_folder: bool = False) -> None:
    if not len(files):
        _logger.warn(f"Empty files")
        return
    if reset_folder and dst_folder:
        pathutil.reset_folder(dst_folder)
    if check_existence:        
        filtered = []
        for f in files:
            dst_file = os.path.join(dst_folder, basename(f[:-3])) + ".pgz"
            if not os.path.exists(dst_file):
                filtered.append(f)
        _logger.info(f"Filtered files {len(filtered)}")

    else:
        filtered = files
        
    if parallel:
        with multiprocessing.Pool() as p:
            list(tqdm(
                p.imap_unordered(partial(read, dst_folder=dst_folder, db_name=db_name, check_existence=check_existence,
                                         remove_extracted_file=remove_extracted_file), filtered),
                total=len(filtered)))
    else:
        for file in tqdm(filtered):
            read(file, dst_folder, db_name=db_name, check_existence=check_existence,
                 remove_extracted_file=remove_extracted_file)
